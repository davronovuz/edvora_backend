"""
Edvora - Finance Signals
Xarajat to'langanda va maosh to'langanda Transaction yaratish
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Expense, Salary, Transaction


@receiver(post_save, sender=Expense)
def create_transaction_on_expense(sender, instance, created, **kwargs):
    """Xarajat to'langanda Transaction yaratish"""
    if instance.status == Expense.Status.PAID:
        if not Transaction.objects.filter(
            expense=instance, transaction_type=Transaction.TransactionType.EXPENSE
        ).exists():
            Transaction.objects.create(
                transaction_type=Transaction.TransactionType.EXPENSE,
                amount=instance.amount,
                transaction_date=instance.expense_date,
                description=f"Xarajat: {instance.title}",
                expense=instance,
                created_by=instance.created_by,
            )


@receiver(post_save, sender=Salary)
def create_transaction_on_salary_paid(sender, instance, created, **kwargs):
    """Maosh to'langanda Transaction yaratish"""
    if instance.status == Salary.Status.PAID:
        if not Transaction.objects.filter(
            salary=instance, transaction_type=Transaction.TransactionType.SALARY
        ).exists():
            Transaction.objects.create(
                transaction_type=Transaction.TransactionType.SALARY,
                amount=instance.total,
                transaction_date=timezone.now().date(),
                description=f"Ish haqi: {instance.teacher.full_name} - {instance.period_month}/{instance.period_year}",
                salary=instance,
                created_by=instance.paid_by,
            )
