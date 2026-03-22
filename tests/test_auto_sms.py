"""
Auto-SMS Tests
"""

import pytest
from unittest.mock import patch
from decimal import Decimal
from datetime import date
from rest_framework import status


@pytest.mark.django_db
class TestAutoSMSModel:
    """AutoSMS model tests"""

    def test_create_auto_sms(self, db):
        from apps.notifications.models import AutoSMS

        auto = AutoSMS.objects.create(
            name='Qarz eslatmasi',
            trigger='debt_reminder',
            message_template='Hurmatli {student_name}, {amount} so\'m qarzingiz bor.',
            is_active=True,
        )
        assert str(auto) == 'Qarz eslatmasi (Qarz eslatmasi)'

    def test_render_message(self, db):
        from apps.notifications.models import AutoSMS

        auto = AutoSMS.objects.create(
            name='Test',
            trigger='birthday',
            message_template='Hurmatli {student_name}, tug\'ilgan kuningiz bilan!',
        )
        result = auto.render_message({'student_name': 'Alisher'})
        assert 'Alisher' in result

    def test_render_message_missing_key(self, db):
        from apps.notifications.models import AutoSMS

        auto = AutoSMS.objects.create(
            name='Test',
            trigger='payment_received',
            message_template='Hurmatli {student_name}, {amount} qabul qilindi',
        )
        # Missing key bo'lsa template qaytaradi
        result = auto.render_message({'student_name': 'Test'})
        assert result == 'Hurmatli {student_name}, {amount} qabul qilindi'


@pytest.mark.django_db
class TestAutoSMSTask:
    """Auto-SMS Celery task tests"""

    @patch('core.utils.sms.sms_service')
    def test_debt_reminder_sms(self, mock_sms, create_student):
        from apps.notifications.models import AutoSMS
        from apps.notifications.tasks import send_debt_reminder_sms

        AutoSMS.objects.create(
            name='Qarz eslatmasi',
            trigger='debt_reminder',
            message_template='Hurmatli {student_name}, {amount} so\'m qarzingiz bor.',
            is_active=True,
        )

        create_student(
            phone='+998901234567',
            balance=Decimal('-100000'),
            status='active',
        )

        mock_sms.send_sms.return_value = {'success': True, 'message_id': '123', 'error': None}

        result = send_debt_reminder_sms()
        assert result['sent'] == 1
        mock_sms.send_sms.assert_called_once()

    def test_debt_reminder_no_trigger(self, create_student):
        """Trigger mavjud bo'lmasa o'tkazib yuborish"""
        from apps.notifications.tasks import send_debt_reminder_sms

        create_student(balance=Decimal('-100000'))
        result = send_debt_reminder_sms()
        assert result['sent'] == 0

    @patch('core.utils.sms.sms_service')
    def test_birthday_sms(self, mock_sms, create_student):
        from apps.notifications.models import AutoSMS
        from apps.notifications.tasks import send_birthday_sms

        AutoSMS.objects.create(
            name='Tug\'ilgan kun',
            trigger='birthday',
            message_template='Hurmatli {student_name}, tug\'ilgan kuningiz bilan!',
            is_active=True,
        )

        today = date.today()
        create_student(
            phone='+998901234567',
            birth_date=today.replace(year=2000),
            status='active',
        )

        mock_sms.send_sms.return_value = {'success': True, 'message_id': '456', 'error': None}

        result = send_birthday_sms()
        assert result['sent'] == 1

    @patch('core.utils.sms.sms_service')
    def test_event_sms_helper(self, mock_sms, create_student):
        from apps.notifications.models import AutoSMS
        from apps.notifications.tasks import send_event_sms

        AutoSMS.objects.create(
            name='Guruhga qo\'shildi',
            trigger='group_joined',
            message_template='{student_name}, siz {group_name} guruhiga qo\'shildingiz.',
            is_active=True,
        )

        student = create_student(phone='+998901234567')
        mock_sms.send_sms.return_value = {'success': True, 'message_id': '789', 'error': None}

        result = send_event_sms('group_joined', student, {
            'student_name': student.full_name,
            'group_name': 'Python A1',
        })

        assert result['success'] is True

    def test_event_sms_inactive_trigger(self, create_student):
        from apps.notifications.tasks import send_event_sms

        student = create_student(phone='+998901234567')
        result = send_event_sms('group_joined', student, {})
        assert result is None


@pytest.mark.django_db
class TestAutoSMSAPI:
    """AutoSMS CRUD API tests"""

    def test_list_auto_sms(self, authenticated_client):
        url = '/api/v1/auto-sms/'
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_create_auto_sms(self, authenticated_client):
        url = '/api/v1/auto-sms/'
        data = {
            'name': 'Test trigger',
            'trigger': 'debt_reminder',
            'message_template': 'Test {student_name}',
            'is_active': True,
        }
        response = authenticated_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_update_auto_sms(self, authenticated_client, db):
        from apps.notifications.models import AutoSMS
        auto = AutoSMS.objects.create(
            name='Old',
            trigger='birthday',
            message_template='Old template',
        )

        url = f'/api/v1/auto-sms/{auto.id}/'
        data = {'name': 'New', 'message_template': 'New template'}
        response = authenticated_client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'New'
