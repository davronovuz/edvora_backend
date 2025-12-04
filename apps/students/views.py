"""
Edvora - Students Views
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from core.permissions import RoleBasedPermission
from .models import Student
from .serializers import (
    StudentListSerializer,
    StudentSerializer,
    StudentCreateSerializer
)


class StudentViewSet(viewsets.ModelViewSet):
    """
    O'quvchilar CRUD
    """
    queryset = Student.objects.all()
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'gender', 'source']
    search_fields = ['first_name', 'last_name', 'phone', 'parent_phone']
    ordering_fields = ['first_name', 'last_name', 'created_at', 'balance']
    ordering = ['-created_at']

    role_permissions = {
        'list': ['owner', 'admin', 'teacher', 'accountant', 'registrar'],
        'retrieve': ['owner', 'admin', 'teacher', 'accountant', 'registrar'],
        'create': ['owner', 'admin', 'registrar'],
        'update': ['owner', 'admin'],
        'partial_update': ['owner', 'admin'],
        'destroy': ['owner'],
    }

    def get_serializer_class(self):
        if self.action == 'list':
            return StudentListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return StudentCreateSerializer
        return StudentSerializer

    def get_queryset(self):
        queryset = Student.objects.all()

        # Qarzdorlar filtri
        has_debt = self.request.query_params.get('has_debt')
        if has_debt is not None:
            if has_debt.lower() == 'true':
                queryset = queryset.filter(balance__lt=0)
            else:
                queryset = queryset.filter(balance__gte=0)

        return queryset

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """O'quvchilar statistikasi"""
        total = Student.objects.count()
        active = Student.objects.filter(status='active').count()
        with_debt = Student.objects.filter(balance__lt=0).count()

        return Response({
            'success': True,
            'data': {
                'total': total,
                'active': active,
                'inactive': total - active,
                'with_debt': with_debt,
            }
        })

    @action(detail=True, methods=['get'])
    def groups(self, request, pk=None):
        """O'quvchining guruhlari"""
        student = self.get_object()
        groups = student.groups.select_related('group__course', 'group__teacher').filter(is_active=True)

        data = []
        for gs in groups:
            data.append({
                'id': str(gs.group.id),
                'name': gs.group.name,
                'course': gs.group.course.name,
                'teacher': gs.group.teacher.full_name if gs.group.teacher else None,
                'days': gs.group.get_days_display(),
                'time': f"{gs.group.start_time.strftime('%H:%M')} - {gs.group.end_time.strftime('%H:%M')}",
                'monthly_price': gs.monthly_price,
                'joined_date': gs.joined_date,
            })

        return Response({
            'success': True,
            'data': data
        })