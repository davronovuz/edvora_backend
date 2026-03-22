"""
Holidays Tests
"""

import pytest
from datetime import date, timedelta
from rest_framework import status


@pytest.mark.django_db
class TestHolidayModel:

    def test_create_holiday(self, db):
        from apps.attendance.models import Holiday

        holiday = Holiday.objects.create(
            name='Mustaqillik kuni',
            date=date(2026, 9, 1),
            holiday_type='national',
        )
        assert 'Mustaqillik kuni' in str(holiday)

    def test_is_holiday_single_day(self, db):
        from apps.attendance.models import Holiday

        Holiday.objects.create(
            name='Test',
            date=date(2026, 3, 21),
            holiday_type='national',
            is_active=True,
        )
        assert Holiday.is_holiday(date(2026, 3, 21)) is True
        assert Holiday.is_holiday(date(2026, 3, 22)) is False

    def test_is_holiday_multi_day(self, db):
        from apps.attendance.models import Holiday

        Holiday.objects.create(
            name='Ramazon hayit',
            date=date(2026, 3, 25),
            end_date=date(2026, 3, 27),
            holiday_type='religious',
            is_active=True,
        )
        assert Holiday.is_holiday(date(2026, 3, 25)) is True
        assert Holiday.is_holiday(date(2026, 3, 26)) is True
        assert Holiday.is_holiday(date(2026, 3, 27)) is True
        assert Holiday.is_holiday(date(2026, 3, 28)) is False

    def test_is_holiday_inactive(self, db):
        from apps.attendance.models import Holiday

        Holiday.objects.create(
            name='Bekor qilingan',
            date=date(2026, 4, 1),
            is_active=False,
        )
        assert Holiday.is_holiday(date(2026, 4, 1)) is False


@pytest.mark.django_db
class TestHolidayAPI:

    def test_list_holidays(self, authenticated_client):
        url = '/api/v1/holidays/'
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_create_holiday(self, authenticated_client):
        url = '/api/v1/holidays/'
        data = {
            'name': 'Navro\'z',
            'date': '2026-03-21',
            'holiday_type': 'national',
            'is_active': True,
        }
        response = authenticated_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == "Navro'z"

    def test_create_multi_day_holiday(self, authenticated_client):
        url = '/api/v1/holidays/'
        data = {
            'name': 'Qurbon hayit',
            'date': '2026-06-15',
            'end_date': '2026-06-17',
            'holiday_type': 'religious',
        }
        response = authenticated_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_check_date_holiday(self, authenticated_client, db):
        from apps.attendance.models import Holiday
        Holiday.objects.create(name='Test', date=date(2026, 5, 1), is_active=True)

        url = '/api/v1/holidays/check-date/?date=2026-05-01'
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['is_holiday'] is True
        assert response.data['data']['holiday_name'] == 'Test'

    def test_check_date_not_holiday(self, authenticated_client):
        url = '/api/v1/holidays/check-date/?date=2026-05-02'
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['is_holiday'] is False

    def test_upcoming_holidays(self, authenticated_client, db):
        from apps.attendance.models import Holiday

        Holiday.objects.create(name='Kelajak', date=date.today() + timedelta(days=10), is_active=True)
        Holiday.objects.create(name='O\'tgan', date=date.today() - timedelta(days=10), is_active=True)

        url = '/api/v1/holidays/upcoming/'
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        names = [h['name'] for h in response.data['data']]
        assert 'Kelajak' in names
        assert "O'tgan" not in names
