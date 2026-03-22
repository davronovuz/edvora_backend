"""
Edvora - Teachers Tests
"""

import pytest
from rest_framework import status
from decimal import Decimal


pytestmark = pytest.mark.django_db


class TestTeacherCRUD:
    """O'qituvchi CRUD testlari"""

    def test_create_teacher(self, authenticated_client):
        data = {
            'first_name': 'Olimjon',
            'last_name': 'Karimov',
            'phone': '+998901234567',
            'status': 'active',
            'salary_type': 'fixed',
            'salary_amount': '5000000.00',
        }
        response = authenticated_client.post('/api/v1/teachers/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['first_name'] == 'Olimjon'

    def test_list_teachers(self, authenticated_client, create_teacher):
        create_teacher()
        response = authenticated_client.get('/api/v1/teachers/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['meta']['total'] == 1

    def test_retrieve_teacher(self, authenticated_client, create_teacher):
        teacher = create_teacher()
        response = authenticated_client.get(f'/api/v1/teachers/{teacher.id}/')
        assert response.status_code == status.HTTP_200_OK

    def test_update_teacher(self, authenticated_client, create_teacher):
        teacher = create_teacher()
        data = {
            'first_name': 'Yangilangan',
            'last_name': teacher.last_name,
            'phone': teacher.phone,
            'salary_type': 'fixed',
            'salary_amount': '6000000.00',
        }
        response = authenticated_client.put(
            f'/api/v1/teachers/{teacher.id}/', data, format='json'
        )
        assert response.status_code == status.HTTP_200_OK

    def test_delete_teacher(self, authenticated_client, create_teacher):
        teacher = create_teacher()
        response = authenticated_client.delete(f'/api/v1/teachers/{teacher.id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT


class TestTeacherModel:
    """Teacher model testlari"""

    def test_full_name(self, create_teacher):
        teacher = create_teacher()
        assert teacher.full_name == 'Test Teacher'

    def test_is_active(self, create_teacher):
        teacher = create_teacher(status='active')
        assert teacher.is_active is True

        teacher.status = 'inactive'
        assert teacher.is_active is False
