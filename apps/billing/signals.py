"""
Billing signals.

Payment completed → avtomatik invoice'larga FIFO taqsimlash.
Payment refunded → invoice'lardan yechib olish.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='payments.Payment')
def allocate_payment_to_invoices(sender, instance, created, **kwargs):
    """
    To'lov qabul qilinganda yoki status o'zgarganda
    billing invoice'larga avtomatik taqsimlash.
    """
    payment = instance

    # Faqat completed to'lovlar uchun
    if payment.status != 'completed':
        return

    # Faqat yangi to'lov yoki status o'zgarishi uchun
    # (update_fields bilan chaqirilganda ham ishlaydi)
    from apps.billing.models import Invoice

    # Bu payment allaqachon invoice'larga taqsimlangan-mi?
    already_allocated = Invoice.objects.filter(payments=payment).exists()
    if already_allocated:
        return

    # Student'ning unpaid invoice'lari bormi?
    unpaid = Invoice.objects.filter(
        student=payment.student,
        status__in=[
            Invoice.Status.UNPAID,
            Invoice.Status.PARTIAL,
            Invoice.Status.OVERDUE,
        ],
    ).exists()

    if not unpaid:
        return

    try:
        from apps.billing.services.payment_allocator import PaymentAllocator
        from apps.groups.models import GroupStudent

        # Agar payment.group bor bo'lsa, shu guruhdagi group_student'ni topamiz
        group_student = None
        if payment.group_id:
            group_student = GroupStudent.objects.filter(
                student=payment.student,
                group=payment.group,
                status='active',
            ).first()

        allocator = PaymentAllocator()
        result = allocator.allocate(payment, group_student=group_student)

        if result.allocated:
            inv_ids = [inv.id for inv, _ in result.allocated]
            logger.info(
                f"Payment {payment.id} → {len(result.allocated)} invoice(s) allocated, "
                f"remaining={result.remaining}"
            )
    except Exception as e:
        logger.error(f"Payment allocation error: {e}", exc_info=True)
