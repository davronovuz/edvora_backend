"""
Edvora - Custom Validators
"""

import re
from django.core.exceptions import ValidationError


def validate_phone_number(value):
    """
    O'zbekiston telefon raqami validatsiyasi
    Format: +998 XX XXX XX XX
    """
    pattern = r'^\+998[0-9]{9}$'
    cleaned = re.sub(r'[\s\-\(\)]', '', value)

    if not re.match(pattern, cleaned):
        raise ValidationError(
            "Telefon raqami noto'g'ri formatda. To'g'ri format: +998901234567"
        )
    return cleaned


def validate_percentage(value):
    """
    Foiz validatsiyasi (0-100)
    """
    if value < 0 or value > 100:
        raise ValidationError("Foiz 0 dan 100 gacha bo'lishi kerak")
    return value


def validate_positive_decimal(value):
    """
    Musbat son validatsiyasi
    """
    if value < 0:
        raise ValidationError("Qiymat musbat bo'lishi kerak")
    return value