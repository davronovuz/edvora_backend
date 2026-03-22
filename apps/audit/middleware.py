"""
Edvora - Audit Middleware
Barcha yozish (POST/PUT/PATCH/DELETE) operatsiyalarini avtomatik log qilish
"""

import json
import logging
from .models import AuditLog

logger = logging.getLogger(__name__)

# Log qilmaydigan URL patternlar
EXCLUDED_PATHS = [
    '/api/v1/auth/login/',
    '/api/v1/auth/refresh/',
    '/api/docs/',
    '/api/schema/',
    '/admin/',
]

METHOD_ACTION_MAP = {
    'POST': 'create',
    'PUT': 'update',
    'PATCH': 'update',
    'DELETE': 'delete',
}


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class AuditMiddleware:
    """
    Barcha mutatsion API so'rovlarini audit log qilish.
    Faqat muvaffaqiyatli (2xx) so'rovlar log qilinadi.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if not self._should_log(request, response):
            return response

        try:
            self._create_log(request, response)
        except Exception as e:
            logger.warning(f"Audit log xatosi: {e}")

        return response

    def _should_log(self, request, response):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return False

        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return False

        if not (200 <= response.status_code < 300):
            return False

        path = request.path
        for excluded in EXCLUDED_PATHS:
            if path.startswith(excluded):
                return False

        return True

    def _create_log(self, request, response):
        action = METHOD_ACTION_MAP.get(request.method, 'update')
        path = request.path

        # Model nomini URL'dan aniqlash
        model_name = self._extract_model_name(path)

        # Ob'ekt ID'sini URL'dan olish
        object_id = self._extract_object_id(path)

        # Response'dan ma'lumot olish
        extra_data = {}
        try:
            if hasattr(response, 'data') and isinstance(response.data, dict):
                data = response.data.get('data', response.data)
                if isinstance(data, dict):
                    object_id = object_id or str(data.get('id', ''))
                    extra_data['response_summary'] = {
                        k: str(v)[:100] for k, v in data.items()
                        if k in ('id', 'name', 'title', 'email', 'status')
                    }
        except Exception:
            pass

        AuditLog.log(
            user=request.user,
            action=action,
            model_name=model_name,
            object_id=object_id,
            object_repr=f"{request.method} {path}",
            extra_data=extra_data,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )

    def _extract_model_name(self, path):
        parts = [p for p in path.split('/') if p and p != 'api' and p != 'v1']
        if parts:
            name = parts[0].replace('-', '_').title().replace('_', '')
            return name
        return 'Unknown'

    def _extract_object_id(self, path):
        parts = [p for p in path.split('/') if p]
        for part in parts:
            if len(part) == 36 and '-' in part:
                return part
        return None
