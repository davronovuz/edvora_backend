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
from .models import Notification, NotificationTemplate, NotificationLog, AutoSMS, Reminder
from .serializers import (
    NotificationSerializer,
    NotificationCreateSerializer,
    NotificationTemplateSerializer,
    NotificationLogSerializer,
    BulkNotificationSerializer,
    AutoSMSSerializer,
    ReminderSerializer,
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
        'send_sms': ['owner', 'admin'],
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
        sms_count = 0
        for student in students:
            for channel in data['channels']:
                notification = Notification.objects.create(
                    student=student,
                    title=data['title'],
                    message=data['message'],
                    notification_type=data['notification_type'],
                    channel=channel,
                    priority='normal'
                )
                created_count += 1

                # SMS kanalida bo'lsa, SMS yuborish
                if channel == 'sms' and student.phone:
                    from core.utils.sms import sms_service
                    result = sms_service.send_sms(student.phone, data['message'])

                    NotificationLog.objects.create(
                        notification=notification,
                        channel='sms',
                        status='sent' if result['success'] else 'failed',
                        external_id=result.get('message_id'),
                        error_message=result.get('error'),
                    )

                    if result['success']:
                        notification.is_sent = True
                        notification.sent_at = timezone.now()
                        notification.save(update_fields=['is_sent', 'sent_at'])
                        sms_count += 1

        return Response({
            'success': True,
            'message': f"{created_count} ta xabarnoma yaratildi, {sms_count} ta SMS yuborildi",
            'data': {
                'students_count': students.count(),
                'notifications_count': created_count,
                'sms_sent': sms_count,
            }
        })

    @action(detail=False, methods=['post'], url_path='send-sms')
    def send_sms(self, request):
        """
        Bir o'quvchiga SMS yuborish

        POST /api/v1/notifications/send-sms/
        {
            "student_id": "uuid",
            "message": "Xabar matni"
        }
        """
        student_id = request.data.get('student_id')
        message = request.data.get('message')

        if not student_id or not message:
            return Response({
                'success': False,
                'error': {'code': 'MISSING_PARAMS', 'message': "student_id va message kerak"}
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'NOT_FOUND', 'message': "O'quvchi topilmadi"}
            }, status=status.HTTP_404_NOT_FOUND)

        if not student.phone:
            return Response({
                'success': False,
                'error': {'code': 'NO_PHONE', 'message': "O'quvchining telefon raqami yo'q"}
            }, status=status.HTTP_400_BAD_REQUEST)

        # Notification yaratish
        notification = Notification.objects.create(
            student=student,
            title='SMS xabar',
            message=message,
            notification_type='system',
            channel='sms',
        )

        # SMS yuborish
        from core.utils.sms import sms_service
        result = sms_service.send_sms(student.phone, message)

        NotificationLog.objects.create(
            notification=notification,
            channel='sms',
            status='sent' if result['success'] else 'failed',
            external_id=result.get('message_id'),
            error_message=result.get('error'),
        )

        if result['success']:
            notification.is_sent = True
            notification.sent_at = timezone.now()
            notification.save(update_fields=['is_sent', 'sent_at'])

        return Response({
            'success': result['success'],
            'message': 'SMS yuborildi' if result['success'] else f"SMS yuborilmadi: {result.get('error')}",
            'data': {
                'message_id': result.get('message_id'),
                'phone': student.phone,
            }
        }, status=status.HTTP_200_OK if result['success'] else status.HTTP_502_BAD_GATEWAY)


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


class AutoSMSViewSet(viewsets.ModelViewSet):
    """
    Avtomatik SMS sozlamalari CRUD
    """
    queryset = AutoSMS.objects.all()
    serializer_class = AutoSMSSerializer
    permission_classes = [IsAuthenticated, RoleBasedPermission]

    role_permissions = {
        'list': ['owner', 'admin'],
        'retrieve': ['owner', 'admin'],
        'create': ['owner'],
        'update': ['owner', 'admin'],
        'partial_update': ['owner', 'admin'],
        'destroy': ['owner'],
    }


class ReminderViewSet(viewsets.ModelViewSet):
    """
    Eslatmalar CRUD
    Har bir foydalanuvchi o'z eslatmalarini ko'radi
    """
    queryset = Reminder.objects.select_related(
        'created_by', 'related_student', 'related_group'
    ).all()
    serializer_class = ReminderSerializer
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['is_completed', 'priority']
    ordering = ['remind_at']

    role_permissions = {
        'list': ['owner', 'admin', 'teacher', 'accountant', 'registrar'],
        'retrieve': ['owner', 'admin', 'teacher', 'accountant', 'registrar'],
        'create': ['owner', 'admin', 'teacher', 'accountant', 'registrar'],
        'update': ['owner', 'admin', 'teacher', 'accountant', 'registrar'],
        'partial_update': ['owner', 'admin', 'teacher', 'accountant', 'registrar'],
        'destroy': ['owner', 'admin', 'teacher', 'accountant', 'registrar'],
        'complete': ['owner', 'admin', 'teacher', 'accountant', 'registrar'],
        'upcoming': ['owner', 'admin', 'teacher', 'accountant', 'registrar'],
    }

    def get_queryset(self):
        qs = super().get_queryset()
        # Har bir foydalanuvchi faqat o'z eslatmalarini ko'radi
        # Owner/admin hammani ko'radi
        user = self.request.user
        if user.role not in ['owner', 'admin']:
            qs = qs.filter(created_by=user)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Eslatmani bajarildi deb belgilash"""
        reminder = self.get_object()
        reminder.complete()

        return Response({
            'success': True,
            'message': 'Eslatma bajarildi deb belgilandi',
            'data': ReminderSerializer(reminder).data,
        })

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Kelayotgan eslatmalar (bugundan 7 kun ichida)"""
        from datetime import timedelta

        now = timezone.now()
        week_later = now + timedelta(days=7)

        reminders = self.get_queryset().filter(
            is_completed=False,
            remind_at__gte=now,
            remind_at__lte=week_later,
        )

        serializer = ReminderSerializer(reminders, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
        })