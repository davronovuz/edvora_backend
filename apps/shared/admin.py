"""
Edvora - Shared Admin
"""

from django.contrib import admin
from django_tenants.admin import TenantAdminMixin
from .models import Tenant, Domain, Plan, BillingInvoice, BillingPayment


@admin.register(Tenant)
class TenantAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ['name', 'slug', 'owner_name', 'status', 'plan', 'created_at']
    list_filter = ['status', 'plan', 'created_at']
    search_fields = ['name', 'slug', 'owner_name', 'owner_email']
    readonly_fields = ['schema_name', 'created_at', 'updated_at']

    fieldsets = (
        ('Asosiy', {
            'fields': ('name', 'slug', 'schema_name')
        }),
        ('Egasi', {
            'fields': ('owner_name', 'owner_email', 'owner_phone')
        }),
        ('Manzil', {
            'fields': ('address', 'city')
        }),
        ('Obuna', {
            'fields': ('plan', 'status', 'trial_ends_at', 'subscription_ends_at')
        }),
        ('Sozlamalar', {
            'fields': ('timezone', 'language', 'currency', 'settings'),
            'classes': ('collapse',)
        }),
        ('Vaqt', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ['domain', 'tenant', 'is_primary']
    list_filter = ['is_primary']
    search_fields = ['domain', 'tenant__name']


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'plan_type', 'price_monthly', 'max_students', 'is_active', 'is_popular',
                    'sort_order']  # sort_order qo'shildi
    list_filter = ['plan_type', 'is_active', 'is_popular']
    search_fields = ['name', 'slug']
    list_editable = ['is_active', 'is_popular', 'sort_order']

    fieldsets = (
        ('Asosiy', {
            'fields': ('name', 'slug', 'plan_type', 'description')
        }),
        ('Narxlar', {
            'fields': ('price_monthly', 'price_yearly')
        }),
        ('Limitlar', {
            'fields': ('max_students', 'max_groups', 'max_teachers', 'max_admins')
        }),
        ('Features', {
            'fields': ('features',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'is_popular', 'sort_order')
        }),
    )


@admin.register(BillingInvoice)
class BillingInvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'tenant', 'total', 'status', 'due_date', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['invoice_number', 'tenant__name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(BillingPayment)
class BillingPaymentAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'amount', 'payment_method', 'status', 'created_at']
    list_filter = ['payment_method', 'status', 'created_at']
    search_fields = ['invoice__invoice_number', 'external_id']
    readonly_fields = ['created_at', 'updated_at']