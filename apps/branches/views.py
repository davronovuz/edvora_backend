"""
Edvora - Branch Views
"""

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from core.permissions import RoleBasedPermission
from .models import Branch
from .serializers import BranchListSerializer, BranchSerializer, BranchCreateSerializer


class BranchViewSet(viewsets.ModelViewSet):
    """Filiallar CRUD + statistika"""
    queryset = Branch.objects.all()
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'city', 'is_main']
    search_fields = ['name', 'address', 'city', 'district']
    ordering_fields = ['name', 'created_at']
    ordering = ['-is_main', 'name']

    role_permissions = {
        'list': ['owner', 'admin', 'teacher', 'accountant', 'registrar'],
        'retrieve': ['owner', 'admin', 'teacher', 'accountant', 'registrar'],
        'create': ['owner', 'admin'],
        'update': ['owner', 'admin'],
        'partial_update': ['owner', 'admin'],
        'destroy': ['owner'],
        'statistics': ['owner', 'admin', 'accountant'],
    }

    def get_serializer_class(self):
        if self.action == 'list':
            return BranchListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return BranchCreateSerializer
        return BranchSerializer

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Filial statistikasi"""
        branch = self.get_object()

        from apps.groups.models import Group, GroupStudent
        from apps.students.models import Student

        groups = Group.objects.filter(branch=branch)
        active_groups = groups.filter(status='active').count()
        total_groups = groups.count()

        students = Student.objects.filter(branch=branch)
        active_students = students.filter(status='active').count()
        total_students = students.count()
        debtors = students.filter(status='active', balance__lt=0).count()

        return Response({
            'success': True,
            'data': {
                'branch': BranchListSerializer(branch).data,
                'groups': {
                    'total': total_groups,
                    'active': active_groups,
                },
                'students': {
                    'total': total_students,
                    'active': active_students,
                    'debtors': debtors,
                },
                'rooms': branch.rooms_count,
                'teachers': branch.teachers_count,
            }
        })
