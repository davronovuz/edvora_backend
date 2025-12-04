"""
Edvora - Notifications Admin
"""

from django.contrib import admin
from .models import Notification, NotificationTemplate, NotificationLog


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'notification_type', 'channel', 'is_read', 'is_sent', 'created_at']
    list_filter = ['notification_type', 'channel', 'is_read', 'is_sent', 'created_at']
    search_fields = ['title', 'message']
    date_hierarchy = 'created_at'


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'notification_type', 'is_active']
    list_filter = ['notification_type', 'is_active']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ['notification', 'channel', 'status', 'created_at']
    list_filter = ['channel', 'status', 'created_at']