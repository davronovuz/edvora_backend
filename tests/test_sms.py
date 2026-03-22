"""
SMS Service & Endpoint Tests
"""

import pytest
from unittest.mock import patch, MagicMock
from rest_framework import status


class TestEskizSMSService:
    """EskizSMSService unit tests"""

    def test_clean_phone_with_plus(self):
        from core.utils.sms import EskizSMSService
        assert EskizSMSService._clean_phone('+998901234567') == '998901234567'

    def test_clean_phone_without_plus(self):
        from core.utils.sms import EskizSMSService
        assert EskizSMSService._clean_phone('998901234567') == '998901234567'

    def test_clean_phone_short(self):
        from core.utils.sms import EskizSMSService
        assert EskizSMSService._clean_phone('901234567') == '998901234567'

    def test_clean_phone_with_spaces(self):
        from core.utils.sms import EskizSMSService
        assert EskizSMSService._clean_phone('+998 90 123 45 67') == '998901234567'

    def test_clean_phone_with_dashes(self):
        from core.utils.sms import EskizSMSService
        assert EskizSMSService._clean_phone('+998-90-123-45-67') == '998901234567'

    @patch('core.utils.sms.requests.post')
    @patch('core.utils.sms.cache')
    def test_send_sms_success(self, mock_cache, mock_post):
        from core.utils.sms import EskizSMSService

        mock_cache.get.return_value = 'test_token'

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': '12345', 'data': {'id': '12345'}}
        mock_post.return_value = mock_response

        service = EskizSMSService()
        result = service.send_sms('998901234567', 'Test xabar')

        assert result['success'] is True
        assert result['message_id'] == '12345'

    @patch('core.utils.sms.requests.post')
    @patch('core.utils.sms.cache')
    def test_send_sms_failure(self, mock_cache, mock_post):
        from core.utils.sms import EskizSMSService

        mock_cache.get.return_value = 'test_token'

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = 'Bad Request'
        mock_post.return_value = mock_response

        service = EskizSMSService()
        result = service.send_sms('998901234567', 'Test')

        assert result['success'] is False
        assert result['error'] is not None

    @patch('core.utils.sms.cache')
    def test_send_sms_no_credentials(self, mock_cache):
        from core.utils.sms import EskizSMSService

        mock_cache.get.return_value = None

        service = EskizSMSService()
        service._email = ''
        service._password = ''
        result = service.send_sms('998901234567', 'Test')

        assert result['success'] is False
        assert 'Token' in result['error']


@pytest.mark.django_db
class TestSMSEndpoint:
    """SMS endpoint tests"""

    @patch('core.utils.sms.sms_service')
    def test_send_sms_endpoint(self, mock_sms, authenticated_client, create_student):
        """SMS yuborish endpoint"""
        mock_sms.send_sms.return_value = {'success': True, 'message_id': '123', 'error': None}

        student = create_student(phone='+998901234567')

        url = '/api/v1/notifications/send-sms/'
        data = {
            'student_id': str(student.id),
            'message': 'Test xabar',
        }
        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True

    def test_send_sms_without_params(self, authenticated_client):
        """Parametrlarsiz SMS - xato"""
        url = '/api/v1/notifications/send-sms/'
        response = authenticated_client.post(url, {}, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_send_sms_student_not_found(self, authenticated_client):
        """Mavjud bo'lmagan student"""
        import uuid
        url = '/api/v1/notifications/send-sms/'
        data = {
            'student_id': str(uuid.uuid4()),
            'message': 'Test',
        }
        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_404_NOT_FOUND
