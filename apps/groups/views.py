"""
Edvora - Groups Views
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.shortcuts import get_object_or_404
from core.permissions import RoleBasedPermission
from apps.students.models import Student
from .models import Group, GroupStudent
from .serializers import (
    GroupListSerializer,
    GroupSerializer,
    GroupCreateSerializer,
    GroupStudentSerializer,
    AddStudentToGroupSerializer
)


class GroupViewSet(viewsets.ModelViewSet):
    """
    Guruhlar CRUD
    """
    queryset = Group.objects.select_related('course', 'teacher').all()
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['course', 'teacher', 'status']
    search_fields = ['name']
    ordering_fields = ['name', 'start_date', 'created_at']
    ordering = ['-start_date']

    role_permissions = {
        'list': ['owner', 'admin', 'teacher', 'registrar'],
        'retrieve': ['owner', 'admin', 'teacher', 'registrar'],
        'create': ['owner', 'admin'],
        'update': ['owner', 'admin'],
        'partial_update': ['owner', 'admin'],
        'destroy': ['owner'],
        'students': ['owner', 'admin', 'teacher'],
        'add_student': ['owner', 'admin', 'registrar'],
        'remove_student': ['owner', 'admin'],
    }

    def get_serializer_class(self):
        if self.action == 'list':
            return GroupListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return GroupCreateSerializer
        return GroupSerializer

    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        """Guruhdagi o'quvchilar"""
        group = self.get_object()
        students = group.students.select_related('student').all()
        serializer = GroupStudentSerializer(students, many=True)

        return Response({
            'success': True,
            'data': serializer.data
        })

    @action(detail=True, methods=['post'])
    def add_student(self, request, pk=None):
        """Guruhga o'quvchi qo'shish"""
        group = self.get_object()
        serializer = AddStudentToGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        student = get_object_or_404(Student, id=serializer.validated_data['student_id'])

        # Tekshirish
        if group.is_full:
            return Response({
                'success': False,
                'error': {'code': 'GROUP_FULL', 'message': 'Guruh to\'lgan'}
            }, status=status.HTTP_400_BAD_REQUEST)

        if GroupStudent.objects.filter(group=group, student=student, is_active=True).exists():
            return Response({
                'success': False,
                'error': {'code': 'ALREADY_EXISTS', 'message': 'O\'quvchi allaqachon guruhda'}
            }, status=status.HTTP_400_BAD_REQUEST)

        # Qo'shish
        gs = GroupStudent.objects.create(
            group=group,
            student=student,
            custom_price=serializer.validated_data.get('custom_price'),
            discount_percent=serializer.validated_data.get('discount_percent', 0)
        )

        return Response({
            'success': True,
            'message': f"{student.full_name} guruhga qo'shildi",
            'data': GroupStudentSerializer(gs).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='remove-student/(?P<student_id>[^/.]+)')
    def remove_student(self, request, pk=None, student_id=None):
        """Guruhdan o'quvchini chiqarish"""
        group = self.get_object()

        gs = get_object_or_404(GroupStudent, group=group, student_id=student_id, is_active=True)
        gs.is_active = False
        gs.status = 'dropped'
        gs.save()

        return Response({
            'success': True,
            'message': "O'quvchi guruhdan chiqarildi"
        })