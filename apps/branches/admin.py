"""
Edvora - Branch Admin
"""

from django.contrib import admin
from .models import Branch


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'phone', 'status', 'is_main', 'created_at']
    list_filter = ['status', 'city', 'is_main']
    search_fields = ['name', 'address', 'city']
