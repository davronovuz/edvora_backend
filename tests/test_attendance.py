"""
Edvora - Attendance Tests
Davomat CRUD, bulk create, statistika
"""

import pytest
from django.utils import timezone
from rest_framework import status
from apps.attendance.models import Attendance, AttendanceSession
from apps.groups.models import GroupStudent


pytestmark = pytest.mark.django_db


class TestAttendanceCRUD:
    """Davomat CRUD testlari"""

    def test_create_attendance(self, authenticated_client, create_group, create_student):
        group = create_group()
        student = create_student()
        GroupStudent.objects.create(group=group, student=student, joined_date=timezone.now().date())

        data = {
            'group': str(group.id),
            'student': str(student.id),
            'date': timezone.now().date().isoformat(),
            'status': 'present',
        }
        response = authenticated_client.post('/api/v1/attendance/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_list_attendance(self, authenticated_client, create_group, create_student):
        group = create_group()
        student = create_student()
        Attendance.objects.create(
            group=group, student=student,
            date=timezone.now().date(), status='present'
        )

        response = authenticated_client.get('/api/v1/attendance/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['meta']['total'] == 1


class TestBulkAttendance:
    """Bulk davomat testlari"""

    def test_bulk_create(self, authenticated_client, create_group, create_student):
        group = create_group()
        s1 = create_student(phone='+998901111111')
        s2 = create_student(phone='+998902222222', first_name='Ali')
        GroupStudent.objects.create(group=group, student=s1, joined_date=timezone.now().date())
        GroupStudent.objects.create(group=group, student=s2, joined_date=timezone.now().date())

        data = {
            'group_id': str(group.id),
            'date': timezone.now().date().isoformat(),
            'attendances': [
                {'student_id': str(s1.id), 'status': 'present'},
                {'student_id': str(s2.id), 'status': 'absent', 'note': 'Kasal'},
            ]
        }
        response = authenticated_client.post(
            '/api/v1/attendance/bulk_create/', data, format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['created'] == 2

        # Session yaratilganmi
        session = AttendanceSession.objects.filter(group=group).first()
        assert session is not None

    def test_bulk_update(self, authenticated_client, create_group, create_student):
        """Mavjud davomatni bulk yangilash"""
        group = create_group()
        student = create_student()
        Attendance.objects.create(
            group=group, student=student,
            date=timezone.now().date(), status='absent'
        )

        data = {
            'group_id': str(group.id),
            'date': timezone.now().date().isoformat(),
            'attendances': [
                {'student_id': str(student.id), 'status': 'present'},
            ]
        }
        response = authenticated_client.post(
            '/api/v1/attendance/bulk_create/', data, format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['updated'] == 1

        # Status yangilangan bo'lishi kerak
        att = Attendance.objects.get(group=group, student=student)
        assert att.status == 'present'


class TestAttendanceByGroup:
    """Guruh bo'yicha davomat"""

    def test_by_group(self, authenticated_client, create_group, create_student):
        group = create_group()
        student = create_student()
        GroupStudent.objects.create(group=group, student=student, joined_date=timezone.now().date())

        response = authenticated_client.get(
            f'/api/v1/attendance/by_group/?group_id={group.id}'
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['students']) == 1

    def test_by_group_missing_param(self, authenticated_client):
        response = authenticated_client.get('/api/v1/attendance/by_group/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestAttendanceByStudent:
    """O'quvchi bo'yicha davomat"""

    def test_by_student(self, authenticated_client, create_group, create_student):
        group = create_group()
        student = create_student()

        for i in range(5):
            Attendance.objects.create(
                group=group, student=student,
                date=timezone.now().date() - timezone.timedelta(days=i),
                status='present' if i < 3 else 'absent',
            )

        response = authenticated_client.get(
            f'/api/v1/attendance/by_student/?student_id={student.id}'
        )
        assert response.status_code == status.HTTP_200_OK
        stats = response.data['data']['statistics']
        assert stats['total'] == 5
        assert stats['present'] == 3
        assert stats['absent'] == 2


class TestAttendanceReport:
    """Davomat hisoboti"""

    def test_report(self, authenticated_client, create_group, create_student):
        group = create_group()
        student = create_student()
        GroupStudent.objects.create(group=group, student=student, joined_date=timezone.now().date())

        today = timezone.now().date()
        Attendance.objects.create(
            group=group, student=student, date=today, status='present'
        )

        response = authenticated_client.get(
            f'/api/v1/attendance/report/?group_id={group.id}'
            f'&start_date={today.isoformat()}&end_date={today.isoformat()}'
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['report']) == 1
        assert response.data['data']['report'][0]['present_days'] == 1

    def test_report_missing_params(self, authenticated_client):
        response = authenticated_client.get('/api/v1/attendance/report/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
