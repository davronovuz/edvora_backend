"""
Authentication Tests
"""

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestAuthentication:
    """Auth endpoint tests"""

    def test_login_success(self, api_client, owner_user):
        """Login muvaffaqiyatli"""
        url = '/api/v1/auth/login/'
        data = {
            'email': 'owner@test.com',
            'password': 'testpass123'
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_login_wrong_password(self, api_client, owner_user):
        """Noto'g'ri parol"""
        url = '/api/v1/auth/login/'
        data = {
            'email': 'owner@test.com',
            'password': 'wrongpassword'
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_authenticated(self, authenticated_client, owner_user):
        """Me endpoint - autentifikatsiya qilingan"""
        url = '/api/v1/auth/me/'

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == owner_user.email

    def test_me_unauthenticated(self, api_client):
        """Me endpoint - autentifikatsiya qilinmagan"""
        url = '/api/v1/auth/me/'

        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED