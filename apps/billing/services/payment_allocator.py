"""
Edvora - Payment Allocator

To'lov kelganda qaysi invoice(lar)ga taqsimlash kerakligini aniqlaydi.

Strategiya: FIFO (eng eski unpaid/partial invoice'ga avval).

Oqim:
    1. Payment qabul qilindi (apps.payments.Payment)
    2. allocate(payment) chaqiriladi
    3. Eng eski UNPAID/PARTIAL invoice'larni topadi
    4. Har biriga to'lov taqsimlaydi
    5. Invoice statuslarini yangilaydi
    6. Ortiqcha bo'lsa — prepaid yoki balansga yozish
"""

from decimal import Decimal

from django.db import transaction
from django.db.models import Q

from apps.billing.models import Invoice


class AllocationResult:
    """allocate() natijasi."""

    __slots__ = ('allocated', 'remaining', 'paid_invoices', 'partial_invoices')

    def __init__(self):
        self.allocated: list[tuple[Invoice, Decimal]] = []  # [(invoice, amount), ...]
        self.remaining: Decimal = Decimal("0")  # taqsimlanmagan qoldiq
        self.paid_invoices: list[Invoice] = []
        self.partial_invoices: list[Invoice] = []


class PaymentAllocator:
    """
    Payment → Invoice FIFO taqsimlash.
    """

    def allocate(self, payment, group_student=None) -> AllocationResult:
        """
        Payment summasini eng eski unpaid/partial invoice'larga taqsimlaydi.

        Args:
            payment: apps.payments.Payment instance
            group_student: ixtiyoriy, faqat shu gs uchun invoice larga taqsimlash.
                           None bo'lsa, student'ning barcha unpaid invoice'lari.

        Returns: AllocationResult
        """
        result = AllocationResult()
        remaining = Decimal(payment.amount)

        if remaining <= 0:
            return result

        invoices = self._get_unpaid_invoices(payment.student, group_student)

        with transaction.atomic():
            for invoice in invoices:
                if remaining <= 0:
                    break

                to_pay = min(remaining, invoice.remaining)
                if to_pay <= 0:
                    continue

                invoice.paid_amount += to_pay
                invoice.payments.add(payment)
                invoice.save(update_fields=['paid_amount', 'updated_at'])
                invoice.recompute_status()

                result.allocated.append((invoice, to_pay))
                remaining -= to_pay

                if invoice.is_paid:
                    result.paid_invoices.append(invoice)
                else:
                    result.partial_invoices.append(invoice)

            result.remaining = remaining

        return result

    def allocate_to_invoice(self, payment, invoice) -> Decimal:
        """
        Bitta konkret invoice'ga to'lov taqsimlash.
        Qaytaradi: haqiqatda taqsimlangan summa.
        """
        remaining = Decimal(payment.amount)
        to_pay = min(remaining, invoice.remaining)
        if to_pay <= 0:
            return Decimal("0")

        with transaction.atomic():
            invoice.paid_amount += to_pay
            invoice.payments.add(payment)
            invoice.save(update_fields=['paid_amount', 'updated_at'])
            invoice.recompute_status()

        return to_pay

    @staticmethod
    def _get_unpaid_invoices(student, group_student=None):
        """
        FIFO tartibda unpaid/partial invoice'larni oladi.
        Eng eski (overdue) birinchi, keyin oddiy.
        """
        q = Q(student=student)
        q &= Q(status__in=[Invoice.Status.UNPAID, Invoice.Status.PARTIAL, Invoice.Status.OVERDUE])

        if group_student:
            q &= Q(group_student=group_student)

        return (
            Invoice.objects
            .filter(q)
            .order_by('period_year', 'period_month', 'created_at')
        )
