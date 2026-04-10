"""
Edvora - Transfer Tests
Talaba guruhlar o'rtasida o'tkazish va jadval konflikti
"""

import pytest
from django.utils import timezone
from rest_framework import status
from apps.groups.models import Group, GroupStudent


pytestmark = pytest.mark.django_db


class TestStudentTransfer:
    """Talaba transfer testlari"""

    def test_transfer_student(self, authenticated_client, create_group, create_student):
        group1 = create_group(name='Group A')
        group2 = create_group(name='Group B')
        student = create_student()

        # Guruhga qo'shish
        GroupStudent.objects.create(group=group1, student=student, joined_date=timezone.now().date())

        data = {
            'student_id': str(student.id),
            'target_group_id': str(group2.id),
            'reason': 'Vaqt mos kelmadi',
        }
        response = authenticated_client.post(
            f'/api/v1/groups/{group1.id}/transfer_student/', data, format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        assert 'Group B' in response.data['message']

        # Eski guruhdan chiqarilganmi
        old_gs = GroupStudent.objects.get(group=group1, student=student)
        assert old_gs.is_active is False
        assert old_gs.status == 'transferred'

        # Yangi guruhga qo'shilganmi
        new_gs = GroupStudent.objects.get(group=group2, student=student)
        assert new_gs.is_active is True

    def test_transfer_to_full_group(self, authenticated_client, create_group, create_student):
        group1 = create_group(name='Group A')
        group2 = create_group(name='Group B', max_students=0)  # To'lgan
        student = create_student()

        GroupStudent.objects.create(group=group1, student=student, joined_date=timezone.now().date())

        data = {
            'student_id': str(student.id),
            'target_group_id': str(group2.id),
        }
        response = authenticated_client.post(
            f'/api/v1/groups/{group1.id}/transfer_student/', data, format='json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['error']['code'] == 'TARGET_FULL'

    def test_transfer_student_not_in_group(self, authenticated_client, create_group, create_student):
        group1 = create_group(name='Group A')
        group2 = create_group(name='Group B')
        student = create_student()

        data = {
            'student_id': str(student.id),
            'target_group_id': str(group2.id),
        }
        response = authenticated_client.post(
            f'/api/v1/groups/{group1.id}/transfer_student/', data, format='json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['error']['code'] == 'NOT_IN_GROUP'

    def test_transfer_with_custom_price(self, authenticated_client, create_group, create_student):
        group1 = create_group(name='Group A')
        group2 = create_group(name='Group B')
        student = create_student()

        GroupStudent.objects.create(group=group1, student=student, joined_date=timezone.now().date())

        data = {
            'student_id': str(student.id),
            'target_group_id': str(group2.id),
            'custom_price': '400000.00',
            'discount_percent': '10.00',
        }
        response = authenticated_client.post(
            f'/api/v1/groups/{group1.id}/transfer_student/', data, format='json'
        )
        assert response.status_code == status.HTTP_200_OK


class TestScheduleConflicts:
    """Jadval konflikti testlari"""

    def test_no_conflicts(self, authenticated_client, create_group, create_teacher, create_course):
        course = create_course()
        teacher1 = create_teacher(phone='+998901111111')
        teacher2 = create_teacher(phone='+998902222222', first_name='Ali')

        create_group(
            name='Morning', teacher=teacher1, course=course,
            days=[0, 2, 4], start_time='09:00', end_time='11:00'
        )
        create_group(
            name='Afternoon', teacher=teacher2, course=course,
            days=[0, 2, 4], start_time='14:00', end_time='16:00'
        )

        response = authenticated_client.get('/api/v1/groups/schedule_conflicts/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['total_conflicts'] == 0

    def test_teacher_conflict(self, authenticated_client, create_group, create_teacher, create_course):
        course = create_course()
        teacher = create_teacher()

        create_group(
            name='Group A', teacher=teacher, course=course,
            days=[0, 2, 4], start_time='09:00', end_time='11:00'
        )
        create_group(
            name='Group B', teacher=teacher, course=course,
            days=[0, 2, 4], start_time='10:00', end_time='12:00'
        )

        response = authenticated_client.get('/api/v1/groups/schedule_conflicts/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['total_conflicts'] >= 1

        # Kamida bitta teacher konflikti bo'lishi kerak
        teacher_conflicts = [
            c for c in response.data['data']['conflicts']
            if c['type'] == 'teacher'
        ]
        assert len(teacher_conflicts) >= 1
