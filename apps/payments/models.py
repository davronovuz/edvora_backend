"""
Edvora - Payments Model
To'lovlar va invoicelar
"""

from django.db import models
from core.models import BaseModel
from decimal import Decimal


class Payment(BaseModel):
    """
    To'lov
    O'quvchidan qabul qilingan to'lov
    """

    class PaymentMethod(models.TextChoices):
        CASH = 'cash', 'Naqd'
        CARD = 'card', 'Karta'
        TRANSFER = 'transfer', "O'tkazma"
        PAYME = 'payme', 'Payme'
        CLICK = 'click', 'Click'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Kutilmoqda'
        COMPLETED = 'completed', 'Qabul qilindi'
        CANCELLED = 'cancelled', 'Bekor qilindi'
        REFUNDED = 'refunded', 'Qaytarildi'

    class PaymentType(models.TextChoices):
        TUITION = 'tuition', "O'qish to'lovi"
        REGISTRATION = 'registration', "Ro'yxatga olish"
        MATERIAL = 'material', 'Material'
        OTHER = 'other', 'Boshqa'

    # O'quvchi
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name="O'quvchi"
    )

    # Guruh (ixtiyoriy - umumiy to'lov bo'lishi mumkin)
    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
        verbose_name="Guruh"
    )

    # To'lov ma'lumotlari
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Summa"
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
        verbose_name="To'lov usuli"
    )
    payment_type = models.CharField(
        max_length=20,
        choices=PaymentType.choices,
        default=PaymentType.TUITION,
        verbose_name="To'lov turi"
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.COMPLETED,
        verbose_name="Status"
    )

    # Qaysi oy uchun
    period_month = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Oy (1-12)"
    )
    period_year = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Yil"
    )

    # Kvitansiya
    receipt_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Kvitansiya raqami"
    )

    # Kim qabul qildi
    received_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='received_payments',
        verbose_name="Kim qabul qildi"
    )

    # Tashqi tizim uchun
    external_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Tashqi ID (Payme/Click)"
    )

    # Izoh
    note = models.TextField(
        blank=True,
        null=True,
        verbose_name="Izoh"
    )

    class Meta:
        verbose_name = "To'lov"
        verbose_name_plural = "To'lovlar"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.full_name} - {self.amount:,.0f} so'm"

    def save(self, *args, **kwargs):
        # Kvitansiya raqamini generatsiya qilish
        if not self.receipt_number:
            from core.utils.helpers import generate_invoice_number
            self.receipt_number = generate_invoice_number('PAY')

        # Yangi to'lov bo'lsa, balansni yangilash
        is_new = self.pk is None
        old_status = None

        if not is_new:
            old_payment = Payment.objects.get(pk=self.pk)
            old_status = old_payment.status

        super().save(*args, **kwargs)

        # Balansni yangilash
        if is_new and self.status == self.Status.COMPLETED:
            self.student.balance += self.amount
            self.student.save(update_fields=['balance'])
        elif old_status and old_status != self.status:
            if self.status == self.Status.REFUNDED and old_status == self.Status.COMPLETED:
                self.student.balance -= self.amount
                self.student.save(update_fields=['balance'])


class Invoice(BaseModel):
    """
    Invoice (Hisob-faktura)
    Oylik to'lov uchun
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Qoralama'
        SENT = 'sent', 'Yuborilgan'
        PAID = 'paid', "To'langan"
        PARTIAL = 'partial', "Qisman to'langan"
        OVERDUE = 'overdue', "Muddati o'tgan"
        CANCELLED = 'cancelled', 'Bekor qilindi'

    # O'quvchi va guruh
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.PROTECT,
        related_name='invoices',
        verbose_name="O'quvchi"
    )
    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.SET_NULL,
        null=True,
        related_name='invoices',
        verbose_name="Guruh"
    )

    # Invoice ma'lumotlari
    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Invoice raqami"
    )

    # Davr
    period_month = models.PositiveIntegerField(
        verbose_name="Oy (1-12)"
    )
    period_year = models.PositiveIntegerField(
        verbose_name="Yil"
    )

    # Summa
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Summa"
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
        verbose_name="Jami"
    )
    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="To'langan summa"
    )

    # Status va muddatlar
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
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

    # Bog'langan to'lovlar
    payments = models.ManyToManyField(
        Payment,
        blank=True,
        related_name='invoices_paid',
        verbose_name="To'lovlar"
    )

    class Meta:
        verbose_name = "Invoice"
        verbose_name_plural = "Invoicelar"
        unique_together = ['student', 'group', 'period_month', 'period_year']
        ordering = ['-period_year', '-period_month']

    def __str__(self):
        return f"{self.invoice_number} - {self.student.full_name}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            from core.utils.helpers import generate_invoice_number
            self.invoice_number = generate_invoice_number('INV')

        # Jami hisoblash
        self.total = self.amount - self.discount

        super().save(*args, **kwargs)

    @property
    def remaining(self):
        """Qolgan summa"""
        return self.total - self.paid_amount

    @property
    def is_paid(self):
        return self.status == self.Status.PAID

    @property
    def is_overdue(self):
        from django.utils import timezone
        return (
                self.status not in [self.Status.PAID, self.Status.CANCELLED] and
                self.due_date < timezone.now().date()
        )


class Discount(BaseModel):
    """
    Chegirma
    """

    class DiscountType(models.TextChoices):
        PERCENT = 'percent', 'Foiz'
        FIXED = 'fixed', 'Belgilangan summa'

    # O'quvchi
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='discounts',
        verbose_name="O'quvchi"
    )

    # Guruh (ixtiyoriy)
    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='discounts',
        verbose_name="Guruh"
    )

    # Chegirma
    name = models.CharField(
        max_length=255,
        verbose_name="Nomi"
    )
    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
        default=DiscountType.PERCENT,
        verbose_name="Turi"
    )
    value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Qiymat"
    )

    # Muddat
    start_date = models.DateField(
        verbose_name="Boshlanish"
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Tugash"
    )

    # Status
    is_active = models.BooleanField(
        default=True,
        verbose_name="Faol"
    )

    # Izoh
    reason = models.TextField(
        blank=True,
        null=True,
        verbose_name="Sabab"
    )

    class Meta:
        verbose_name = "Chegirma"
        verbose_name_plural = "Chegirmalar"
        ordering = ['-created_at']

    def __str__(self):
        if self.discount_type == self.DiscountType.PERCENT:
            return f"{self.student.full_name} - {self.value}%"
        return f"{self.student.full_name} - {self.value:,.0f} so'm"

    def calculate_discount(self, amount):
        """Chegirma summasini hisoblash"""
        if self.discount_type == self.DiscountType.PERCENT:
            return amount * (self.value / 100)
        return min(self.value, amount)


class WriteOff(BaseModel):
    """
    Oylik yechib olish logi
    Har oy avtomatik GroupStudent.balance dan yechib olinadi
    """

    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='write_offs',
        verbose_name="O'quvchi"
    )
    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.CASCADE,
        related_name='write_offs',
        verbose_name="Guruh"
    )
    group_student = models.ForeignKey(
        'groups.GroupStudent',
        on_delete=models.CASCADE,
        related_name='write_offs',
        verbose_name="Guruh-O'quvchi"
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Yechib olingan summa"
    )

    # Qaysi oy uchun
    period_month = models.PositiveIntegerField(
        verbose_name="Oy (1-12)"
    )
    period_year = models.PositiveIntegerField(
        verbose_name="Yil"
    )

    # Balans holati
    balance_before = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Oldingi balans"
    )
    balance_after = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Keyingi balans"
    )

    class Meta:
        verbose_name = "Yechib olish"
        verbose_name_plural = "Yechib olishlar"
        ordering = ['-created_at']
        unique_together = ['group_student', 'period_month', 'period_year']

    def __str__(self):
        return f"{self.student.full_name} - {self.group.name} - {self.amount:,.0f} ({self.period_month}/{self.period_year})"