"""
Edvora - Courses Tests
"""

import pytest
from rest_framework import status


pytestmark = pytest.mark.django_db


class TestSubjectCRUD:
    """Fan CRUD testlari"""

    def test_create_subject(self, authenticated_client):
        data = {
            'name': 'Ingliz tili',
            'slug': 'ingliz-tili',
        }
        response = authenticated_client.post('/api/v1/subjects/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_list_subjects(self, authenticated_client, create_subject):
        create_subject()
        response = authenticated_client.get('/api/v1/subjects/')
        assert response.status_code == status.HTTP_200_OK


class TestCourseCRUD:
    """Kurs CRUD testlari"""

    def test_create_course(self, authenticated_client, create_subject):
        subject = create_subject()
        data = {
            'name': 'Beginner English',
            'subject': str(subject.id),
            'level': 'beginner',
            'duration_months': 3,
            'total_lessons': 36,
            'price': '500000.00',
        }
        response = authenticated_client.post('/api/v1/courses/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_list_courses(self, authenticated_client, create_course):
        create_course()
        response = authenticated_client.get('/api/v1/courses/')
        assert response.status_code == status.HTTP_200_OK
