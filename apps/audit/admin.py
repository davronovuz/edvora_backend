from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'model_name', 'object_repr', 'ip_address', 'created_at']
    list_filter = ['action', 'model_name']
    search_fields = ['object_repr', 'model_name']
    readonly_fields = [
        'user', 'action', 'model_name', 'object_id', 'object_repr',
        'changes', 'extra_data', 'ip_address', 'user_agent', 'created_at',
    ]
