"""
Edvora - Helper Functions
"""

from datetime import datetime, date
from decimal import Decimal
import random
import string


def generate_random_code(length=6, digits_only=True):
    """
    Tasodifiy kod generatsiya qilish
    """
    if digits_only:
        return ''.join(random.choices(string.digits, k=length))
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def generate_invoice_number(prefix='INV'):
    """
    Invoice raqam generatsiya qilish
    Format: INV-2024-000001
    """
    year = datetime.now().year
    random_part = generate_random_code(6)
    return f"{prefix}-{year}-{random_part}"


def format_currency(amount, currency='UZS'):
    """
    Pul summasini formatlash
    """
    if amount is None:
        return f"0 {currency}"

    # Format with thousand separators
    formatted = "{:,.0f}".format(amount).replace(',', ' ')
    return f"{formatted} {currency}"


def calculate_percentage(part, total):
    """
    Foizni hisoblash
    """
    if total == 0:
        return Decimal('0')
    return (Decimal(str(part)) / Decimal(str(total))) * 100


def get_current_month_range():
    """
    Joriy oyning boshi va oxirini qaytarish
    """
    today = date.today()
    start = today.replace(day=1)

    # Next month's first day - 1 day = current month's last day
    if today.month == 12:
        end = today.replace(year=today.year + 1, month=1, day=1)
    else:
        end = today.replace(month=today.month + 1, day=1)

    from datetime import timedelta
    end = end - timedelta(days=1)

    return start, end


def mask_phone_number(phone):
    """
    Telefon raqamini maskalash
    +998901234567 -> +998 90 *** ** 67
    """
    if not phone or len(phone) < 9:
        return phone

    return f"{phone[:7]} *** ** {phone[-2:]}"