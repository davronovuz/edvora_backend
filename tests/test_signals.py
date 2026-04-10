"""
Edvora - Signal Tests
Payment -> Transaction, GroupStudent -> Notification, Expense -> Transaction
"""

import pytest
from django.utils import timezone
from datetime import date
from decimal import Decimal
from apps.payments.models import Payment
from apps.finance.models import Transaction, Expense, ExpenseCategory, Salary
from apps.groups.models import GroupStudent
from apps.notifications.models import Notification


pytestmark = pytest.mark.django_db


class TestPaymentSignals:
    """To'lov signallari testlari"""

    def test_transaction_created_on_payment(self, owner_user, create_student):
        """To'lov qilinganda avtomatik Transaction yaratilishi"""
        student = create_student()
        payment = Payment.objects.create(
            student=student,
            amount=Decimal('500000'),
            payment_method='cash',
            payment_type='tuition',
            status='completed',
            received_by=owner_user,
        )

        transaction = Transaction.objects.filter(payment=payment).first()
        assert transaction is not None
        assert transaction.transaction_type == 'income'
        assert transaction.amount == Decimal('500000')

    def test_refund_transaction_created(self, owner_user, create_student):
        """Qaytarish qilinganda refund Transaction yaratilishi"""
        student = create_student()
        payment = Payment.objects.create(
            student=student,
            amount=Decimal('500000'),
            payment_method='cash',
            status='completed',
            received_by=owner_user,
        )

        # Qaytarish
        payment.status = 'refunded'
        payment.save()

        refund_tx = Transaction.objects.filter(
            payment=payment, transaction_type='refund'
        ).first()
        assert refund_tx is not None
        assert refund_tx.amount == Decimal('500000')

    def test_no_duplicate_transactions(self, owner_user, create_student):
        """Bir xil transaction ikki marta yaratilmasligi"""
        student = create_student()
        payment = Payment.objects.create(
            student=student,
            amount=Decimal('500000'),
            payment_method='cash',
            status='completed',
            received_by=owner_user,
        )

        # Income transaction 1 ta bo'lishi kerak
        assert Transaction.objects.filter(
            payment=payment, transaction_type='income'
        ).count() == 1


class TestGroupStudentSignals:
    """GroupStudent signallari testlari"""

    def test_notification_on_student_join(self, create_group, create_student):
        """Guruhga qo'shilganda notification yaratilishi"""
        group = create_group()
        student = create_student()

        GroupStudent.objects.create(group=group, student=student, joined_date=date.today())

        notification = Notification.objects.filter(
            student=student, notification_type='group'
        ).first()
        assert notification is not None
        assert "qo'shildingiz" in notification.title

    def test_notification_on_student_drop(self, create_group, create_student):
        """Guruhdan chiqarilganda notification yaratilishi"""
        group = create_group()
        student = create_student()
        gs = GroupStudent.objects.create(group=group, student=student, joined_date=date.today())

        # Chiqarish
        gs.status = 'dropped'
        gs.is_active = False
        gs.save()

        notifications = Notification.objects.filter(
            student=student, notification_type='group'
        )
        # Birinchisi qo'shilish, ikkinchisi chiqarilish
        assert notifications.count() == 2


class TestExpenseSignals:
    """Xarajat signallari testlari"""

    def test_transaction_on_expense_paid(self, owner_user):
        """Xarajat to'langanda Transaction yaratilishi"""
        category = ExpenseCategory.objects.create(
            name='Ijara', slug='ijara'
        )
        expense = Expense.objects.create(
            category=category,
            title='Yanvar ijara',
            amount=Decimal('5000000'),
            expense_date=timezone.now().date(),
            status='paid',
            created_by=owner_user,
        )

        transaction = Transaction.objects.filter(expense=expense).first()
        assert transaction is not None
        assert transaction.transaction_type == 'expense'
        assert transaction.amount == Decimal('5000000')
