"""
Reports (Hisobotlar) Tests
"""

import pytest
from datetime import date
from rest_framework import status


@pytest.mark.django_db
class TestReportsAPI:

    def test_lead_conversion_report(self, authenticated_client):
        url = '/api/v1/analytics/reports/lead_conversion/?start_date=2026-01-01&end_date=2026-12-31'
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert 'summary' in response.data['data']
        assert 'conversion_rate' in response.data['data']['summary']

    def test_lead_conversion_missing_params(self, authenticated_client):
        url = '/api/v1/analytics/reports/lead_conversion/'
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_teacher_performance_report(self, authenticated_client):
        url = '/api/v1/analytics/reports/teacher_performance/?start_date=2026-01-01&end_date=2026-12-31'
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert 'teachers' in response.data['data']

    def test_teacher_performance_with_data(self, authenticated_client, create_group, create_student):
        from apps.groups.models import GroupStudent

        group = create_group()
        student = create_student()
        GroupStudent.objects.create(group=group, student=student, joined_date=date.today())

        url = '/api/v1/analytics/reports/teacher_performance/?start_date=2026-01-01&end_date=2026-12-31'
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['teachers']) > 0
        teacher_data = response.data['data']['teachers'][0]
        assert 'attendance_rate' in teacher_data
        assert 'retention_rate' in teacher_data

    def test_write_off_report(self, authenticated_client):
        url = '/api/v1/analytics/reports/write_off_report/?year=2026&month=3'
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert 'summary' in response.data['data']

    def test_dashboard_summary(self, authenticated_client):
        url = '/api/v1/analytics/dashboard/summary/'
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert 'students' in response.data['data']
        assert 'finance' in response.data['data']
        assert 'leads' in response.data['data']
