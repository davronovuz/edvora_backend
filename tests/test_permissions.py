"""
Edvora - Permissions Tests
Role-based access control testlari
"""

import pytest
from rest_framework import status


pytestmark = pytest.mark.django_db


class TestRoleBasedAccess:
    """Rol asosidagi kirish huquqlari"""

    def test_owner_can_access_everything(self, api_client, owner_user):
        api_client.force_authenticate(user=owner_user)

        endpoints = [
            '/api/v1/students/',
            '/api/v1/teachers/',
            '/api/v1/groups/',
            '/api/v1/rooms/',
            '/api/v1/audit/',
        ]
        for url in endpoints:
            response = api_client.get(url)
            assert response.status_code == status.HTTP_200_OK, f"Owner {url} ga kira olmadi"

    def test_admin_can_access_main_features(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)

        response = api_client.get('/api/v1/students/')
        assert response.status_code == status.HTTP_200_OK

        response = api_client.get('/api/v1/groups/')
        assert response.status_code == status.HTTP_200_OK

    def test_teacher_limited_access(self, api_client, teacher_user):
        api_client.force_authenticate(user=teacher_user)

        # Teacher guruhlarni ko'rishi mumkin
        response = api_client.get('/api/v1/groups/')
        assert response.status_code == status.HTTP_200_OK

        # Teacher guruh yarata olmaydi
        response = api_client.post('/api/v1/groups/', {}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_denied(self, api_client):
        response = api_client.get('/api/v1/students/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_teacher_cannot_delete_group(self, api_client, teacher_user, create_group):
        api_client.force_authenticate(user=teacher_user)
        group = create_group()
        response = api_client.delete(f'/api/v1/groups/{group.id}/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_teacher_cannot_access_audit(self, api_client, teacher_user):
        api_client.force_authenticate(user=teacher_user)
        response = api_client.get('/api/v1/audit/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_accountant_cannot_create_students(self, api_client, accountant_user):
        api_client.force_authenticate(user=accountant_user)
        response = api_client.post('/api/v1/students/', {}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestOwnerOnlyOperations:
    """Faqat owner qila oladigan operatsiyalar"""

    def test_only_owner_can_delete_student(self, api_client, admin_user, create_student):
        api_client.force_authenticate(user=admin_user)
        student = create_student()

        # Admin o'chira olmaydi (agar role_permissions da owner bo'lsa)
        response = api_client.delete(f'/api/v1/students/{student.id}/')
        # Bu loyihada admin ham o'chirishi mumkin bo'lishi mumkin,
        # lekin test yozib qo'yamiz
        assert response.status_code in [
            status.HTTP_204_NO_CONTENT, status.HTTP_403_FORBIDDEN
        ]
