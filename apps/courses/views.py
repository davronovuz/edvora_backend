"""
Edvora - Courses Views
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from core.permissions import RoleBasedPermission
from .models import Subject, Course
from .serializers import (
    SubjectSerializer, SubjectCreateSerializer,
    CourseSerializer, CourseCreateSerializer
)


class SubjectViewSet(viewsets.ModelViewSet):
    """
    Fanlar CRUD
    """
    queryset = Subject.objects.all()
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    role_permissions = {
        'list': ['owner', 'admin', 'teacher', 'registrar'],
        'retrieve': ['owner', 'admin', 'teacher', 'registrar'],
        'create': ['owner', 'admin'],
        'update': ['owner', 'admin'],
        'partial_update': ['owner', 'admin'],
        'destroy': ['owner'],
    }

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return SubjectCreateSerializer
        return SubjectSerializer

    def get_queryset(self):
        queryset = Subject.objects.all()
        if self.action == 'list':
            is_active = self.request.query_params.get('is_active')
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active.lower() == 'true')
        return queryset


class CourseViewSet(viewsets.ModelViewSet):
    """
    Kurslar CRUD
    """
    queryset = Course.objects.select_related('subject').all()
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['subject', 'level', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'price', 'created_at']
    ordering = ['name']

    role_permissions = {
        'list': ['owner', 'admin', 'teacher', 'registrar'],
        'retrieve': ['owner', 'admin', 'teacher', 'registrar'],
        'create': ['owner', 'admin'],
        'update': ['owner', 'admin'],
        'partial_update': ['owner', 'admin'],
        'destroy': ['owner'],
    }

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CourseCreateSerializer
        return CourseSerializer