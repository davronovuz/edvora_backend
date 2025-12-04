"""
Edvora - Attendance Admin
"""

from django.contrib import admin
from .models import Attendance, AttendanceSession


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['student', 'group', 'date', 'status', 'marked_by', 'created_at']
    list_filter = ['status', 'date', 'group']
    search_fields = ['student__first_name', 'student__last_name']
    date_hierarchy = 'date'


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ['group', 'date', 'total_students', 'present_count', 'absent_count']
    list_filter = ['date', 'group']
    date_hierarchy = 'date'