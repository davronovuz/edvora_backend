"""
Edvora - Users Admin
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'full_name', 'role', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'is_staff', 'created_at']
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    ordering = ['-created_at']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Shaxsiy', {'fields': ('first_name', 'last_name', 'phone', 'avatar')}),
        ('Rol', {'fields': ('role', 'custom_permissions')}),
        ('Status', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Vaqt', {'fields': ('last_login', 'last_login_ip', 'created_at', 'updated_at')}),
    )

    readonly_fields = ['created_at', 'updated_at', 'last_login', 'last_login_ip']

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
    )