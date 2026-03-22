"""
Groups API Tests
"""

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestGroupsAPI:
    """Groups endpoint tests"""

    def test_list_groups(self, authenticated_client, create_group):
        """Guruhlar ro'yxati"""
        create_group(name='Group 1')
        create_group(name='Group 2')

        url = '/api/v1/groups/'
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_create_group(self, authenticated_client, create_course, create_teacher):
        """Yangi guruh yaratish"""
        course = create_course()
        teacher = create_teacher()

        url = '/api/v1/groups/'
        data = {
            'name': 'Yangi Guruh',
            'course': str(course.id),
            'teacher': str(teacher.id),
            'start_date': '2024-01-15',
            'days': [0, 2, 4],
            'start_time': '09:00',
            'end_time': '11:00',
            'max_students': 15,
            'status': 'active'
        }

        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Yangi Guruh'

    def test_add_student_to_group(self, authenticated_client, create_group, create_student):
        """Guruhga o'quvchi qo'shish"""
        group = create_group()
        student = create_student()

        url = f'/api/v1/groups/{group.id}/add_student/'
        data = {'student_id': str(student.id)}

        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED

    def test_group_students_list(self, authenticated_client, create_group, create_student):
        """Guruhdagi o'quvchilar"""
        from apps.groups.models import GroupStudent

        group = create_group()
        student1 = create_student(phone='+998901111111')
        student2 = create_student(phone='+998902222222')

        GroupStudent.objects.create(group=group, student=student1)
        GroupStudent.objects.create(group=group, student=student2)

        url = f'/api/v1/groups/{group.id}/students/'
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']) == 2