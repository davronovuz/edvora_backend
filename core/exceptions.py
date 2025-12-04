"""
Edvora - Custom Exceptions & Exception Handler
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError


def custom_exception_handler(exc, context):
    """
    Custom exception handler

    Response format:
    {
        "success": false,
        "error": {
            "code": "ERROR_CODE",
            "message": "Error message",
            "details": [...] (optional)
        }
    }
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        custom_response = {
            'success': False,
            'error': {
                'code': get_error_code(exc),
                'message': get_error_message(exc, response),
            }
        }

        # Add details for validation errors
        if isinstance(exc, (DRFValidationError, DjangoValidationError)):
            custom_response['error']['details'] = get_error_details(response.data)

        response.data = custom_response

    return response


def get_error_code(exc):
    """Exception type'dan error code olish"""
    error_codes = {
        'ValidationError': 'VALIDATION_ERROR',
        'AuthenticationFailed': 'AUTHENTICATION_FAILED',
        'NotAuthenticated': 'NOT_AUTHENTICATED',
        'PermissionDenied': 'PERMISSION_DENIED',
        'NotFound': 'NOT_FOUND',
        'MethodNotAllowed': 'METHOD_NOT_ALLOWED',
        'Throttled': 'THROTTLED',
    }
    return error_codes.get(exc.__class__.__name__, 'ERROR')


def get_error_message(exc, response):
    """Error message olish"""
    if hasattr(exc, 'detail'):
        if isinstance(exc.detail, str):
            return exc.detail
        elif isinstance(exc.detail, dict):
            # First error message
            for key, value in exc.detail.items():
                if isinstance(value, list):
                    return str(value[0])
                return str(value)
    return "Xatolik yuz berdi"


def get_error_details(data):
    """Validation error details"""
    if isinstance(data, dict):
        details = []
        for field, errors in data.items():
            if isinstance(errors, list):
                for error in errors:
                    details.append({
                        'field': field,
                        'message': str(error)
                    })
            else:
                details.append({
                    'field': field,
                    'message': str(errors)
                })
        return details
    return []


# Custom Exception Classes
class BusinessLogicError(Exception):
    """Business logic xatoliklari uchun"""

    def __init__(self, message, code='BUSINESS_ERROR'):
        self.message = message
        self.code = code
        super().__init__(message)


class TenantNotFoundError(Exception):
    """Tenant topilmadi"""

    def __init__(self, message="Markaz topilmadi"):
        self.message = message
        super().__init__(message)


class InsufficientBalanceError(Exception):
    """Balans yetarli emas"""

    def __init__(self, message="Balans yetarli emas"):
        self.message = message
        super().__init__(message)