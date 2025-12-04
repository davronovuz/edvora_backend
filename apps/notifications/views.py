"""
Edvora - Notifications Views
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from django.db.models import Count, Q
from django.utils import timezone
from core.permissions import RoleBasedPermission
from apps.students.models import Student
from apps.groups.models import GroupStudent
from .models import Notification, NotificationTemplate, NotificationLog
from .serializers import (
    NotificationSerializer,
    NotificationCreateSerializer,
    NotificationTemplateSerializer,
    NotificationLogSerializer,
    BulkNotificationSerializer
)


class NotificationViewSet(viewsets.ModelViewSet):
    """
    Xabarnomalar CRUD
    """
    queryset = Notification.objects.all()
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['notification_type', 'channel', 'is_read', 'is_sent']
    ordering = ['-created_at']

    role_permissions = {
        'list': ['owner', 'admin', 'teacher', 'accountant', 'registrar'],
        'retrieve': ['owner', 'admin', 'teacher', 'accountant', 'registrar'],
        'create': ['owner', 'admin'],
        'update': ['owner', 'admin'],
        'partial_update': ['owner', 'admin'],
        'destroy': ['owner'],
        'my_notifications': ['owner', 'admin', 'teacher', 'accountant', 'registrar'],
        'mark_read': ['owner', 'admin', 'teacher', 'accountant', 'registrar'],
        'mark_all_read': ['owner', 'admin', 'teacher', 'accountant', 'registrar'],
        'send_bulk': ['owner', 'admin'],
        'unread_count': ['owner', 'admin', 'teacher', 'accountant', 'registrar'],
    }

    def get_serializer_class(self):
        if self.action == 'create':
            return NotificationCreateSerializer
        if self.action == 'send_bulk':
            return BulkNotificationSerializer
        return NotificationSerializer

    @action(detail=False, methods=['get'])
    def my_notifications(self, request):
        """
        Joriy foydalanuvchining xabarnomalar

        GET /api/v1/notifications/my_notifications/
        """
        notifications = Notification.objects.filter(
            user=request.user
        ).order_by('-created_at')[:50]

        serializer = NotificationSerializer(notifications, many=True)

        return Response({
            'success': True,
            'data': serializer.data
        })

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """
        O'qilmagan xabarnomalar soni

        GET /api/v1/notifications/unread_count/
        """
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()

        return Response({
            'success': True,
            'data': {'count': count}
        })

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """
        O'qilgan deb belgilash

        POST /api/v1/notifications/{id}/mark_read/
        """
        notification = self.get_object()
        notification.mark_as_read()

        return Response({
            'success': True,
            'message': "O'qilgan deb belgilandi"
        })

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """
        Barchasini o'qilgan deb belgilash

        POST /api/v1/notifications/mark_all_read/
        """
        updated = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())

        return Response({
            'success': True,
            'message': f"{updated} ta xabarnoma o'qilgan deb belgilandi"
        })

    @action(detail=False, methods=['post'])
    def send_bulk(self, request):
        """
        Ommaviy xabarnoma yuborish

        POST /api/v1/notifications/send_bulk/
        {
            "title": "Eslatma",
            "message": "To'lovni amalga oshiring",
            "notification_type": "payment_reminder",
            "channels": ["telegram", "in_app"],
            "target_type": "debtors"
        }
        """
        serializer = BulkNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        target_type = data['target_type']

        # Maqsadli o'quvchilarni aniqlash
        if target_type == 'all_students':
            students = Student.objects.filter(status='active')
        elif target_type == 'group':
            group_id = data.get('group_id')
            if not group_id:
                return Response({
                    'success': False,
                    'error': {'code': 'MISSING_PARAM', 'message': 'group_id kerak'}
                }, status=status.HTTP_400_BAD_REQUEST)

            student_ids = GroupStudent.objects.filter(
                group_id=group_id,
                is_active=True
            ).values_list('student_id', flat=True)
            students = Student.objects.filter(id__in=student_ids)
        elif target_type == 'debtors':
            students = Student.objects.filter(balance__lt=0, status='active')
        elif target_type == 'selected':
            student_ids = data.get('student_ids', [])
            students = Student.objects.filter(id__in=student_ids)
        else:
            students = Student.objects.none()

        # Xabarnomalarni yaratish
        created_count = 0
        for student in students:
            for channel in data['channels']:
                Notification.objects.create(
                    student=student,
                    title=data['title'],
                    message=data['message'],
                    notification_type=data['notification_type'],
                    channel=channel,
                    priority='normal'
                )
                created_count += 1

        return Response({
            'success': True,
            'message': f"{created_count} ta xabarnoma yaratildi",
            'data': {
                'students_count': students.count(),
                'notifications_count': created_count
            }
        })


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    """
    Xabarnoma shablonlari CRUD
    """
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['notification_type', 'is_active']

    role_permissions = {
        'list': ['owner', 'admin'],
        'retrieve': ['owner', 'admin'],
        'create': ['owner'],
        'update': ['owner'],
        'partial_update': ['owner'],
        'destroy': ['owner'],
    }


class NotificationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Xabarnoma loglari (faqat o'qish)
    """
    queryset = NotificationLog.objects.select_related('notification').all()
    serializer_class = NotificationLogSerializer
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['channel', 'status']
    ordering = ['-created_at']

    role_permissions = {
        'list': ['owner', 'admin'],
        'retrieve': ['owner', 'admin'],
    }