"""
Edvora - Payment Signals
To'lov qilinganda avtomatik Transaction yaratish
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Payment


@receiver(post_save, sender=Payment)
def create_transaction_on_payment(sender, instance, created, **kwargs):
    """To'lov saqlanganda avtomatik Transaction yaratish"""
    from apps.finance.models import Transaction

    if created and instance.status == Payment.Status.COMPLETED:
        Transaction.objects.create(
            transaction_type=Transaction.TransactionType.INCOME,
            amount=instance.amount,
            transaction_date=timezone.now().date(),
            description=f"To'lov: {instance.student.full_name} - {instance.get_payment_type_display()}",
            payment=instance,
            created_by=instance.received_by,
        )
    elif not created and instance.status == Payment.Status.REFUNDED:
        # Qaytarish uchun Transaction
        if not Transaction.objects.filter(
            payment=instance, transaction_type=Transaction.TransactionType.REFUND
        ).exists():
            Transaction.objects.create(
                transaction_type=Transaction.TransactionType.REFUND,
                amount=instance.amount,
                transaction_date=timezone.now().date(),
                description=f"Qaytarish: {instance.student.full_name}",
                payment=instance,
                created_by=instance.received_by,
            )
