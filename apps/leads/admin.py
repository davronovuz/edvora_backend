"""
Edvora - Leads Admin
"""

from django.contrib import admin
from .models import Lead, LeadActivity, DemoRequest


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'phone', 'status', 'source', 'priority', 'assigned_to', 'created_at']
    list_filter = ['status', 'source', 'priority', 'created_at']
    search_fields = ['first_name', 'last_name', 'phone', 'email']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Shaxsiy', {
            'fields': ('first_name', 'last_name', 'phone', 'phone_secondary', 'email')
        }),
        ('Qiziqish', {
            'fields': ('interested_course', 'interested_subject')
        }),
        ('Status', {
            'fields': ('status', 'source', 'priority', 'assigned_to', 'next_contact_date')
        }),
        ('Konversiya', {
            'fields': ('converted_student', 'converted_at', 'lost_reason'),
            'classes': ('collapse',)
        }),
        ('Marketing', {
            'fields': ('utm_source', 'utm_medium', 'utm_campaign'),
            'classes': ('collapse',)
        }),
        ('Izoh', {
            'fields': ('notes',)
        }),
    )


@admin.register(LeadActivity)
class LeadActivityAdmin(admin.ModelAdmin):
    list_display = ['lead', 'activity_type', 'created_by', 'created_at']
    list_filter = ['activity_type', 'created_at']
    search_fields = ['lead__first_name', 'lead__last_name', 'description']


@admin.register(DemoRequest)
class DemoRequestAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'center_name', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'phone', 'center_name']
    date_hierarchy = 'created_at'