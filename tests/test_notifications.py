"""
Edvora - Notifications Tests
Xabarnomalar CRUD, template rendering
"""

import pytest
from rest_framework import status
from apps.notifications.models import Notification, NotificationTemplate


pytestmark = pytest.mark.django_db


class TestNotificationCRUD:
    """Xabarnoma testlari"""

    def test_create_notification(self, authenticated_client, create_student):
        student = create_student()
        data = {
            'student': str(student.id),
            'title': "To'lov eslatmasi",
            'message': 'Iltimos to\'lovni amalga oshiring',
            'notification_type': 'payment_reminder',
            'channel': 'in_app',
        }
        response = authenticated_client.post(
            '/api/v1/notifications/', data, format='json'
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_list_notifications(self, authenticated_client, owner_user):
        Notification.objects.create(
            user=owner_user,
            title='Test', message='Test message',
        )
        response = authenticated_client.get('/api/v1/notifications/')
        assert response.status_code == status.HTTP_200_OK


class TestNotificationModel:
    """Notification model testlari"""

    def test_mark_as_read(self, owner_user):
        notification = Notification.objects.create(
            user=owner_user,
            title='Test', message='Test message',
        )
        assert notification.is_read is False

        notification.mark_as_read()
        notification.refresh_from_db()

        assert notification.is_read is True
        assert notification.read_at is not None


class TestNotificationTemplate:
    """Shablon testlari"""

    def test_template_render(self):
        template = NotificationTemplate(
            name='Payment Reminder',
            slug='payment-reminder',
            notification_type='payment_reminder',
            title_template="To'lov eslatmasi",
            message_template="Hurmatli {student_name}, {amount} so'm qarzingiz bor.",
            channels=['in_app', 'telegram'],
        )
        title, message = template.render({
            'student_name': 'Ali Karimov',
            'amount': '500,000',
        })
        assert title == "To'lov eslatmasi"
        assert 'Ali Karimov' in message
        assert '500,000' in message
