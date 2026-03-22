"""
Edvora - Eskiz.uz SMS Service
O'zbekiston uchun SMS yuborish xizmati
"""

import logging
import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

ESKIZ_BASE_URL = 'https://notify.eskiz.uz/api'
ESKIZ_TOKEN_CACHE_KEY = 'eskiz_auth_token'


class EskizSMSService:
    """
    Eskiz.uz SMS API bilan ishlash
    https://documenter.getpostman.com/view/663428/RzfmES4z
    """

    def __init__(self):
        self._email = None
        self._password = None
        self._from_name = None

    @property
    def email(self):
        if self._email is None:
            self._email = getattr(settings, 'ESKIZ_EMAIL', '')
        return self._email

    @property
    def password(self):
        if self._password is None:
            self._password = getattr(settings, 'ESKIZ_PASSWORD', '')
        return self._password

    @property
    def from_name(self):
        if self._from_name is None:
            self._from_name = getattr(settings, 'ESKIZ_FROM', '4546')
        return self._from_name

    def _get_token(self):
        """Token olish (cache bilan)"""
        token = cache.get(ESKIZ_TOKEN_CACHE_KEY)
        if token:
            return token

        if not self.email or not self.password:
            logger.error("Eskiz credentials sozlanmagan")
            return None

        try:
            response = requests.post(
                f'{ESKIZ_BASE_URL}/auth/login',
                data={
                    'email': self.email,
                    'password': self.password,
                },
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                token = data.get('data', {}).get('token')
                if token:
                    # Token 29 kunga cache qilinadi
                    cache.set(ESKIZ_TOKEN_CACHE_KEY, token, 29 * 24 * 60 * 60)
                    return token
            else:
                logger.error(f"Eskiz login xato: {response.status_code} - {response.text}")
        except requests.RequestException as e:
            logger.error(f"Eskiz login xato: {e}")

        return None

    def send_sms(self, phone_number, message):
        """
        SMS yuborish

        Args:
            phone_number: Telefon raqami (998XXXXXXXXX formatida)
            message: Xabar matni

        Returns:
            dict: {'success': bool, 'message_id': str|None, 'error': str|None}
        """
        token = self._get_token()
        if not token:
            return {'success': False, 'message_id': None, 'error': 'Token olinmadi'}

        # Telefon raqamini tozalash
        clean_phone = self._clean_phone(phone_number)

        try:
            response = requests.post(
                f'{ESKIZ_BASE_URL}/message/sms/send',
                headers={'Authorization': f'Bearer {token}'},
                data={
                    'mobile_phone': clean_phone,
                    'message': message,
                    'from': self.from_name,
                },
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                message_id = data.get('id') or data.get('data', {}).get('id')
                return {
                    'success': True,
                    'message_id': str(message_id) if message_id else None,
                    'error': None,
                }
            else:
                error = response.text
                logger.error(f"SMS yuborish xato: {response.status_code} - {error}")

                # Token muddati tugagan bo'lishi mumkin
                if response.status_code == 401:
                    cache.delete(ESKIZ_TOKEN_CACHE_KEY)

                return {'success': False, 'message_id': None, 'error': error}

        except requests.RequestException as e:
            logger.error(f"SMS yuborish xato: {e}")
            return {'success': False, 'message_id': None, 'error': str(e)}

    def send_bulk_sms(self, messages):
        """
        Ko'plab SMS yuborish

        Args:
            messages: list of {'phone': str, 'text': str}

        Returns:
            list of results
        """
        results = []
        for msg in messages:
            result = self.send_sms(msg['phone'], msg['text'])
            result['phone'] = msg['phone']
            results.append(result)
        return results

    def check_status(self, message_id):
        """SMS holatini tekshirish"""
        token = self._get_token()
        if not token:
            return None

        try:
            response = requests.get(
                f'{ESKIZ_BASE_URL}/message/sms/status/{message_id}',
                headers={'Authorization': f'Bearer {token}'},
                timeout=10,
            )
            if response.status_code == 200:
                return response.json()
        except requests.RequestException as e:
            logger.error(f"SMS status tekshirish xato: {e}")

        return None

    @staticmethod
    def _clean_phone(phone):
        """Telefon raqamini tozalash: +998901234567 -> 998901234567"""
        phone = str(phone).strip()
        phone = phone.replace('+', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        if phone.startswith('998') and len(phone) == 12:
            return phone
        if len(phone) == 9:
            return f'998{phone}'
        return phone


# Singleton
sms_service = EskizSMSService()
