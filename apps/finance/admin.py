"""
Edvora - Finance Admin
"""

from django.contrib import admin
from .models import ExpenseCategory, Expense, Transaction, Salary


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'amount', 'expense_date', 'status', 'created_by']
    list_filter = ['category', 'status', 'expense_date']
    search_fields = ['title', 'description']
    date_hierarchy = 'expense_date'


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_type', 'amount', 'transaction_date', 'description']
    list_filter = ['transaction_type', 'transaction_date']
    date_hierarchy = 'transaction_date'


@admin.register(Salary)
class SalaryAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'period_month', 'period_year', 'total', 'status']
    list_filter = ['status', 'period_year', 'period_month']
    search_fields = ['teacher__first_name', 'teacher__last_name']