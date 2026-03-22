"""
Edvora - Finance Tests
Xarajatlar, tranzaksiyalar, maoshlar
"""

import pytest
from django.utils import timezone
from rest_framework import status
from decimal import Decimal
from apps.finance.models import ExpenseCategory, Expense, Transaction, Salary


pytestmark = pytest.mark.django_db


class TestExpenseCategory:
    """Xarajat kategoriyasi testlari"""

    def test_create_category(self, authenticated_client):
        data = {
            'name': 'Ijara',
            'slug': 'ijara',
            'color': '#FF5733',
        }
        response = authenticated_client.post(
            '/api/v1/finance/expense-categories/', data, format='json'
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_list_categories(self, authenticated_client):
        ExpenseCategory.objects.create(name='Ijara', slug='ijara')
        ExpenseCategory.objects.create(name='Kommunal', slug='kommunal')

        response = authenticated_client.get('/api/v1/finance/expense-categories/')
        assert response.status_code == status.HTTP_200_OK


class TestExpense:
    """Xarajat testlari"""

    def test_create_expense(self, authenticated_client):
        category = ExpenseCategory.objects.create(name='Ijara', slug='ijara')

        data = {
            'category': str(category.id),
            'title': 'Fevral ijara',
            'amount': '5000000.00',
            'expense_date': timezone.now().date().isoformat(),
            'status': 'paid',
        }
        response = authenticated_client.post(
            '/api/v1/finance/expenses/', data, format='json'
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_list_expenses(self, authenticated_client, owner_user):
        category = ExpenseCategory.objects.create(name='Ijara', slug='ijara')
        Expense.objects.create(
            category=category, title='Test',
            amount=1000000, expense_date=timezone.now().date(),
            status='paid', created_by=owner_user,
        )

        response = authenticated_client.get('/api/v1/finance/expenses/')
        assert response.status_code == status.HTTP_200_OK


class TestTransaction:
    """Tranzaksiya testlari"""

    def test_list_transactions(self, authenticated_client, owner_user):
        Transaction.objects.create(
            transaction_type='income',
            amount=Decimal('500000'),
            transaction_date=timezone.now().date(),
            description="Test to'lov",
            created_by=owner_user,
        )

        response = authenticated_client.get('/api/v1/finance/transactions/')
        assert response.status_code == status.HTTP_200_OK


class TestSalary:
    """Maosh testlari"""

    def test_create_salary(self, authenticated_client, create_teacher):
        teacher = create_teacher()

        data = {
            'teacher': str(teacher.id),
            'period_month': 3,
            'period_year': 2024,
            'base_salary': '5000000.00',
            'bonus': '500000.00',
            'deduction': '0.00',
            'total': '5500000.00',
        }
        response = authenticated_client.post(
            '/api/v1/finance/salaries/', data, format='json'
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_salary_auto_total(self, create_teacher):
        """Total avtomatik hisoblanishi"""
        teacher = create_teacher()
        salary = Salary.objects.create(
            teacher=teacher,
            period_month=3, period_year=2024,
            base_salary=Decimal('5000000'),
            bonus=Decimal('500000'),
            deduction=Decimal('200000'),
            total=0,
        )
        salary.refresh_from_db()
        assert salary.total == Decimal('5300000')


class TestFinanceDashboard:
    """Moliya dashboard testi"""

    def test_dashboard(self, authenticated_client):
        response = authenticated_client.get('/api/v1/finance/dashboard/')
        assert response.status_code == status.HTTP_200_OK
