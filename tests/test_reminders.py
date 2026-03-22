"""
Reminders Tests
"""

import pytest
from datetime import timedelta
from django.utils import timezone
from rest_framework import status


@pytest.mark.django_db
class TestReminderModel:

    def test_create_reminder(self, owner_user):
        from apps.notifications.models import Reminder

        reminder = Reminder.objects.create(
            created_by=owner_user,
            title='Test eslatma',
            remind_at=timezone.now() + timedelta(hours=1),
        )
        assert 'Test eslatma' in str(reminder)

    def test_complete_reminder(self, owner_user):
        from apps.notifications.models import Reminder

        reminder = Reminder.objects.create(
            created_by=owner_user,
            title='Complete test',
            remind_at=timezone.now(),
        )
        reminder.complete()
        reminder.refresh_from_db()

        assert reminder.is_completed is True
        assert reminder.completed_at is not None


@pytest.mark.django_db
class TestReminderTask:

    def test_process_reminders(self, owner_user):
        from apps.notifications.models import Reminder, Notification
        from apps.notifications.tasks import process_reminders

        # Vaqti kelgan eslatma
        Reminder.objects.create(
            created_by=owner_user,
            title='Eslatma 1',
            remind_at=timezone.now() - timedelta(minutes=5),
        )
        # Kelajakdagi eslatma (ishlanmasligi kerak)
        Reminder.objects.create(
            created_by=owner_user,
            title='Eslatma 2',
            remind_at=timezone.now() + timedelta(hours=2),
        )

        result = process_reminders()
        assert result['notified'] == 1

        # Notification yaratilganmi?
        notif = Notification.objects.filter(user=owner_user, title__contains='Eslatma 1')
        assert notif.exists()

    def test_process_reminders_already_notified(self, owner_user):
        from apps.notifications.models import Reminder
        from apps.notifications.tasks import process_reminders

        Reminder.objects.create(
            created_by=owner_user,
            title='Already notified',
            remind_at=timezone.now() - timedelta(hours=1),
            is_notified=True,
        )

        result = process_reminders()
        assert result['notified'] == 0


@pytest.mark.django_db
class TestReminderAPI:

    def test_list_reminders(self, authenticated_client):
        url = '/api/v1/reminders/'
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_create_reminder(self, authenticated_client):
        url = '/api/v1/reminders/'
        data = {
            'title': 'Student bilan gaplash',
            'description': 'To\'lov haqida',
            'remind_at': (timezone.now() + timedelta(hours=2)).isoformat(),
            'priority': 'high',
        }
        response = authenticated_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == 'Student bilan gaplash'

    def test_complete_reminder_endpoint(self, authenticated_client, owner_user):
        from apps.notifications.models import Reminder

        reminder = Reminder.objects.create(
            created_by=owner_user,
            title='Complete me',
            remind_at=timezone.now() + timedelta(hours=1),
        )

        url = f'/api/v1/reminders/{reminder.id}/complete/'
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['is_completed'] is True

    def test_upcoming_reminders(self, authenticated_client, owner_user):
        from apps.notifications.models import Reminder

        # Kelayotgan eslatma (3 kun ichida)
        Reminder.objects.create(
            created_by=owner_user,
            title='Soon',
            remind_at=timezone.now() + timedelta(days=2),
        )
        # Uzoq kelajakdagi (ko'rinmasligi kerak)
        Reminder.objects.create(
            created_by=owner_user,
            title='Far away',
            remind_at=timezone.now() + timedelta(days=30),
        )

        url = '/api/v1/reminders/upcoming/'
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']) == 1
        assert response.data['data'][0]['title'] == 'Soon'

    def test_reminder_with_student(self, authenticated_client, create_student):
        student = create_student()

        url = '/api/v1/reminders/'
        data = {
            'title': 'Call student',
            'remind_at': (timezone.now() + timedelta(hours=1)).isoformat(),
            'related_student': str(student.id),
        }
        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['student_name'] == student.full_name
