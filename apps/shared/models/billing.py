"""
Edvora - Billing Models
SaaS to'lovlari (Edvora uchun)
"""

from django.db import models
from core.models import BaseModel


class BillingInvoice(BaseModel):
    """
    Edvora SaaS uchun invoice
    Markazlarning oylik obuna to'lovlari
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Qoralama'
        PENDING = 'pending', 'Kutilmoqda'
        PAID = 'paid', "To'langan"
        OVERDUE = 'overdue', 'Muddati o\'tgan'
        CANCELLED = 'cancelled', 'Bekor qilingan'

    # Tenant
    tenant = models.ForeignKey(
        'shared.Tenant',
        on_delete=models.CASCADE,
        related_name='billing_invoices',
        verbose_name="Markaz"
    )

    # Invoice details
    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Invoice raqami"
    )

    # Period
    period_start = models.DateField(
        verbose_name="Davr boshi"
    )
    period_end = models.DateField(
        verbose_name="Davr oxiri"
    )

    # Amount
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Jami summa"
    )
    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Chegirma"
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Umumiy summa"
    )
    currency = models.CharField(
        max_length=3,
        default='UZS',
        verbose_name="Valyuta"
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Status"
    )
    due_date = models.DateField(
        verbose_name="To'lov muddati"
    )
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="To'langan vaqt"
    )

    # Notes
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Izoh"
    )

    class Meta:
        verbose_name = "Billing Invoice"
        verbose_name_plural = "Billing Invoices"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.invoice_number} - {self.tenant.name}"

    @property
    def is_paid(self):
        return self.status == self.Status.PAID

    @property
    def is_overdue(self):
        from django.utils import timezone
        return (
                self.status == self.Status.PENDING and
                self.due_date < timezone.now().date()
        )


class BillingPayment(BaseModel):
    """
    Billing to'lovlari
    """

    class PaymentMethod(models.TextChoices):
        CARD = 'card', 'Karta'
        PAYME = 'payme', 'Payme'
        CLICK = 'click', 'Click'
        TRANSFER = 'transfer', "Bank o'tkazmasi"

    class Status(models.TextChoices):
        PENDING = 'pending', 'Kutilmoqda'
        COMPLETED = 'completed', 'Bajarildi'
        FAILED = 'failed', 'Xato'
        REFUNDED = 'refunded', 'Qaytarildi'

    # Invoice
    invoice = models.ForeignKey(
        BillingInvoice,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name="Invoice"
    )

    # Amount
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Summa"
    )
    currency = models.CharField(
        max_length=3,
        default='UZS',
        verbose_name="Valyuta"
    )

    # Payment details
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        verbose_name="To'lov usuli"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Status"
    )

    # External reference
    external_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Tashqi ID"
    )

    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Metadata"
    )

    class Meta:
        verbose_name = "Billing Payment"
        verbose_name_plural = "Billing Payments"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.amount}"