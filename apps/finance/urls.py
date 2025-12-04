"""
Edvora - Finance URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ExpenseCategoryViewSet,
    ExpenseViewSet,
    TransactionViewSet,
    SalaryViewSet,
    FinanceDashboardView
)

router = DefaultRouter()
router.register('expense-categories', ExpenseCategoryViewSet, basename='expense-categories')
router.register('expenses', ExpenseViewSet, basename='expenses')
router.register('transactions', TransactionViewSet, basename='transactions')
router.register('salaries', SalaryViewSet, basename='salaries')
router.register('dashboard', FinanceDashboardView, basename='finance-dashboard')

urlpatterns = [
    path('', include(router.urls)),
]