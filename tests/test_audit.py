"""
Edvora - Audit Tests
Audit log yaratish, ko'rish, statistika
"""

import pytest
from rest_framework import status
from apps.audit.models import AuditLog


pytestmark = pytest.mark.django_db


class TestAuditLog:
    """Audit log testlari"""

    def test_create_audit_log(self, owner_user):
        log = AuditLog.log(
            user=owner_user,
            action='create',
            model_name='Student',
            object_id='test-uuid-123',
            object_repr='Test Student',
            changes={'first_name': {'old': '', 'new': 'Ali'}},
            ip_address='127.0.0.1',
        )
        assert log.action == 'create'
        assert log.model_name == 'Student'
        assert log.changes['first_name']['new'] == 'Ali'

    def test_list_audit_logs(self, authenticated_client, owner_user):
        AuditLog.log(user=owner_user, action='create', model_name='Student')
        AuditLog.log(user=owner_user, action='update', model_name='Student')

        response = authenticated_client.get('/api/v1/audit/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['meta']['total'] == 2

    def test_filter_by_action(self, authenticated_client, owner_user):
        AuditLog.log(user=owner_user, action='create', model_name='Student')
        AuditLog.log(user=owner_user, action='delete', model_name='Student')

        response = authenticated_client.get('/api/v1/audit/?action=create')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['meta']['total'] == 1

    def test_filter_by_model(self, authenticated_client, owner_user):
        AuditLog.log(user=owner_user, action='create', model_name='Student')
        AuditLog.log(user=owner_user, action='create', model_name='Payment')

        response = authenticated_client.get('/api/v1/audit/?model_name=Payment')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['meta']['total'] == 1

    def test_audit_summary(self, authenticated_client, owner_user):
        for i in range(5):
            AuditLog.log(user=owner_user, action='create', model_name='Student')
        for i in range(3):
            AuditLog.log(user=owner_user, action='update', model_name='Payment')

        response = authenticated_client.get('/api/v1/audit/summary/?days=7')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['total'] == 8

    def test_object_history(self, authenticated_client, owner_user):
        obj_id = 'test-obj-uuid'
        AuditLog.log(user=owner_user, action='create', model_name='Student', object_id=obj_id)
        AuditLog.log(user=owner_user, action='update', model_name='Student', object_id=obj_id)

        response = authenticated_client.get(
            f'/api/v1/audit/object_history/?model=Student&object_id={obj_id}'
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']) == 2

    def test_audit_readonly(self, authenticated_client):
        """Audit loglarni o'chirish/o'zgartirish mumkin emas"""
        response = authenticated_client.post('/api/v1/audit/', {}, format='json')
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_non_admin_cannot_view_audit(self, api_client, create_user):
        """Faqat owner/admin ko'rishi mumkin"""
        teacher = create_user(email='teacher2@test.com', role='teacher')
        api_client.force_authenticate(user=teacher)

        response = api_client.get('/api/v1/audit/')
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestAuditLogModel:
    """Model test"""

    def test_str_representation(self, owner_user):
        log = AuditLog.log(
            user=owner_user, action='create', model_name='Student'
        )
        assert 'Yaratish' in str(log)
        assert 'Student' in str(log)
