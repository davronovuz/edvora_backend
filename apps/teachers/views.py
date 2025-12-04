"""
Edvora - Teachers Views
"""

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from core.permissions import RoleBasedPermission
from .models import Teacher
from .serializers import (
    TeacherListSerializer,
    TeacherSerializer,
    TeacherCreateSerializer
)


class TeacherViewSet(viewsets.ModelViewSet):
    """
    O'qituvchilar CRUD
    """
    queryset = Teacher.objects.prefetch_related('subjects').all()
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['first_name', 'last_name', 'phone']
    ordering_fields = ['first_name', 'last_name', 'created_at']
    ordering = ['first_name']

    role_permissions = {
        'list': ['owner', 'admin', 'accountant'],
        'retrieve': ['owner', 'admin', 'accountant'],
        'create': ['owner'],
        'update': ['owner'],
        'partial_update': ['owner'],
        'destroy': ['owner'],
    }

    def get_serializer_class(self):
        if self.action == 'list':
            return TeacherListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return TeacherCreateSerializer
        return TeacherSerializer

    @action(detail=True, methods=['get'])
    def groups(self, request, pk=None):
        """O'qituvchining guruhlari"""
        teacher = self.get_object()
        groups = teacher.groups.select_related('course').filter(status='active')

        data = []
        for group in groups:
            data.append({
                'id': str(group.id),
                'name': group.name,
                'course': group.course.name,
                'students_count': group.students_count,
                'days': group.get_days_display(),
                'time': f"{group.start_time.strftime('%H:%M')} - {group.end_time.strftime('%H:%M')}",
            })

        return Response({
            'success': True,
            'data': data
        })