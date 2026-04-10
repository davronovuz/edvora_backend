"""
Edvora - Billing Admin
"""

from django.contrib import admin

from .models import (
    BillingProfile,
    StudentLeave,
    Discount,
    Invoice,
    InvoiceLine,
)


@admin.register(BillingProfile)
class BillingProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'mode', 'branch', 'is_default', 'is_active', 'created_at')
    list_filter = ('mode', 'is_default', 'is_active', 'leave_policy', 'branch')
    search_fields = ('name', 'description')
    fieldsets = (
        ("Asosiy", {
            'fields': ('branch', 'name', 'description', 'mode', 'is_default', 'is_active')
        }),
        ("Billing cycle", {
            'fields': ('billing_day', 'due_days', 'grace_period_days')
        }),
        ("Ta'til siyosati", {
            'fields': ('leave_policy', 'min_leave_days', 'max_leave_days_per_month')
        }),
        ("Penya", {
            'fields': (
                'late_fee_enabled', 'late_fee_type',
                'late_fee_value', 'late_fee_frequency'
            )
        }),
        ("To'lov qoidalari", {
            'fields': ('allow_partial_payment', 'allow_prepayment', 'auto_allocate_fifo')
        }),
        ("Ro'yxatga olish", {
            'fields': ('has_registration_fee', 'registration_fee_amount')
        }),
        ("Qo'shimcha", {
            'fields': (
                'first_month_free_days',
                'price_per_lesson', 'price_per_hour',
                'extra_settings',
            )
        }),
    )


@admin.register(StudentLeave)
class StudentLeaveAdmin(admin.ModelAdmin):
    list_display = ('group_student', 'start_date', 'end_date', 'status', 'days_count', 'created_at')
    list_filter = ('status', 'start_date')
    search_fields = (
        'group_student__student__first_name',
        'group_student__student__last_name',
        'reason',
    )
    raw_id_fields = ('group_student', 'requested_by', 'approved_by')


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'kind', 'value_type', 'value',
        'student', 'group', 'is_active', 'is_usable',
    )
    list_filter = ('kind', 'value_type', 'is_active', 'stackable')
    search_fields = ('name', 'code')
    raw_id_fields = ('student', 'group', 'course', 'branch', 'approved_by')


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0
    fields = ('kind', 'description', 'amount', 'discount', 'leave')
    raw_id_fields = ('discount', 'leave')


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        'number', 'student', 'group', 'period_month', 'period_year',
        'total_amount', 'paid_amount', 'status', 'due_date',
    )
    list_filter = ('status', 'period_year', 'period_month', 'billing_profile')
    search_fields = (
        'number',
        'student__first_name',
        'student__last_name',
        'group__name',
    )
    raw_id_fields = (
        'student', 'group', 'group_student', 'billing_profile', 'payments',
    )
    readonly_fields = ('number', 'total_amount', 'created_at', 'updated_at')
    inlines = [InvoiceLineInline]


@admin.register(InvoiceLine)
class InvoiceLineAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'kind', 'description', 'amount', 'created_at')
    list_filter = ('kind',)
    search_fields = ('invoice__number', 'description')
    raw_id_fields = ('invoice', 'discount', 'leave')
