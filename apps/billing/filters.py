"""
Edvora - Billing filter classes
"""
from django_filters import rest_framework as filters

from .models import Invoice


class CharInFilter(filters.BaseInFilter, filters.CharFilter):
    pass


class InvoiceFilter(filters.FilterSet):
    """
    Invoice filter — `status` bir nechta qiymatni qo'llab-quvvatlaydi
    (vergul bilan ajratilgan yoki `?status=a&status=b`).
    """
    status = CharInFilter(field_name='status', lookup_expr='in')

    class Meta:
        model = Invoice
        fields = ['status', 'student', 'group', 'period_year', 'period_month']
