"""
Edvora - Payments Admin
"""

from django.contrib import admin
from .models import Payment, Invoice, Discount


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'student', 'amount', 'payment_method', 'status', 'created_at']
    list_filter = ['status', 'payment_method', 'payment_type', 'created_at']
    search_fields = ['student__first_name', 'student__last_name', 'receipt_number']
    date_hierarchy = 'created_at'
    readonly_fields = ['receipt_number', 'created_at', 'updated_at']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'student', 'total', 'paid_amount', 'status', 'due_date']
    list_filter = ['status', 'period_year', 'period_month']
    search_fields = ['student__first_name', 'student__last_name', 'invoice_number']
    readonly_fields = ['invoice_number', 'created_at', 'updated_at']


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ['student', 'name', 'discount_type', 'value', 'is_active', 'start_date']
    list_filter = ['discount_type', 'is_active']
    search_fields = ['student__first_name', 'student__last_name', 'name']