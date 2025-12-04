"""
Edvora - Analytics Admin
"""

from django.contrib import admin
from .models import DailyStats, MonthlyStats


@admin.register(DailyStats)
class DailyStatsAdmin(admin.ModelAdmin):
    list_display = ['date', 'total_students', 'active_students', 'total_income', 'attendance_rate']
    list_filter = ['date']
    date_hierarchy = 'date'


@admin.register(MonthlyStats)
class MonthlyStatsAdmin(admin.ModelAdmin):
    list_display = ['year', 'month', 'total_students', 'total_income', 'net_profit']
    list_filter = ['year']