"""
Edvora - Billing Models
Pluggable billing system: BillingProfile, Invoice, InvoiceLine, StudentLeave, Discount

Asosiy g'oya:
    BillingProfile (konfiguratsiya) -> BillingStrategy (mantiq) -> Invoice (natija)

Har bir o'quv markaz o'ziga mos billing modelni tanlaydi:
    monthly_flat, monthly_prorated_days, per_lesson, per_attendance,
    package, hourly, subscription_freeze, monthly_prorated_lessons
"""

from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

from core.models import BaseModel


# =============================================================================
# BILLING PROFILE
# =============================================================================

class BillingProfile(BaseModel):
    """
    Billing konfiguratsiyasi.

    Har bir markaz/filial/kurs/guruh o'z billing profilini tanlaydi.
    Profil tanlangan strategy klassini va uning sozlamalarini saqlaydi.
    """

    class Mode(models.TextChoices):
        MONTHLY_FLAT = 'monthly_flat', "Oylik (qat'iy)"
        MONTHLY_PRORATED_DAYS = 'monthly_prorated_days', "Oylik (kun bo'yicha pro-rate)"
        MONTHLY_PRORATED_LESSONS = 'monthly_prorated_lessons', "Oylik (dars bo'yicha pro-rate)"
        PER_LESSON = 'per_lesson', "Har dars uchun"
        PER_ATTENDANCE = 'per_attendance', "Qatnashgan dars uchun"
        PACKAGE = 'package', "Paket (butun kurs)"
        HOURLY = 'hourly', "Soat hisobida"
        SUBSCRIPTION_FREEZE = 'subscription_freeze', "Obuna (muzlatish bilan)"

    class LeavePolicy(models.TextChoices):
        NONE = 'none', "Ta'til yo'q"
        PRORATE_DAYS = 'prorate_days', "Kun bo'yicha chegirish"
        PRORATE_LESSONS = 'prorate_lessons', "Dars bo'yicha chegirish"
        PUSH_TO_NEXT_MONTH = 'push_to_next_month', "Keyingi oyga surish"

    class LateFeeType(models.TextChoices):
        PERCENT = 'percent', "Foiz"
        FIXED = 'fixed', "Belgilangan summa"

    class LateFeeFrequency(models.TextChoices):
        ONCE = 'once', "Bir marta"
        DAILY = 'daily', "Har kuni"
        WEEKLY = 'weekly', "Har hafta"

    # === Identification ===
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.CASCADE,
        related_name='billing_profiles',
        null=True, blank=True,
        verbose_name="Filial",
        help_text="null bo'lsa global shablon"
    )
    name = models.CharField(max_length=150, verbose_name="Profil nomi")
    description = models.TextField(blank=True, null=True, verbose_name="Tavsif")
    mode = models.CharField(
        max_length=40, choices=Mode.choices,
        default=Mode.MONTHLY_FLAT,
        verbose_name="Billing turi"
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name="Filial uchun default"
    )
    is_active = models.BooleanField(default=True, verbose_name="Faol")

    # === Billing cycle ===
    billing_day = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Hisob-faktura kuni",
        help_text="Oyning qaysi kunida invoice generatsiya qilinadi (1-28)"
    )
    due_days = models.PositiveSmallIntegerField(
        default=10,
        verbose_name="To'lov muddati (kun)",
        help_text="Invoice yaratilgandan necha kun ichida to'lash kerak"
    )
    grace_period_days = models.PositiveSmallIntegerField(
        default=3,
        verbose_name="Toqatlik muddati (kun)",
        help_text="Due date'dan keyin overdue bo'lishidan oldin kutilgan kun"
    )

    # === Leave / ta'til ===
    leave_policy = models.CharField(
        max_length=30, choices=LeavePolicy.choices,
        default=LeavePolicy.PRORATE_DAYS,
        verbose_name="Ta'til siyosati"
    )
    min_leave_days = models.PositiveSmallIntegerField(
        default=3,
        verbose_name="Minimal ta'til kuni",
        help_text="Shundan kam ta'til hisoblanmaydi"
    )
    max_leave_days_per_month = models.PositiveSmallIntegerField(
        default=15,
        verbose_name="Oyiga maksimal ta'til kuni"
    )

    # === Late fee / penya ===
    late_fee_enabled = models.BooleanField(default=False, verbose_name="Penya yoqilgan")
    late_fee_type = models.CharField(
        max_length=20, choices=LateFeeType.choices,
        default=LateFeeType.PERCENT,
        verbose_name="Penya turi"
    )
    late_fee_value = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0'),
        verbose_name="Penya qiymati"
    )
    late_fee_frequency = models.CharField(
        max_length=20, choices=LateFeeFrequency.choices,
        default=LateFeeFrequency.ONCE,
        verbose_name="Penya chastotasi"
    )

    # === Payment rules ===
    allow_partial_payment = models.BooleanField(
        default=True,
        verbose_name="Qisman to'lovga ruxsat"
    )
    allow_prepayment = models.BooleanField(
        default=True,
        verbose_name="Oldindan to'lovga ruxsat"
    )
    auto_allocate_fifo = models.BooleanField(
        default=True,
        verbose_name="To'lovni avtomatik FIFO taqsimlash"
    )

    # === Registration fee ===
    has_registration_fee = models.BooleanField(
        default=False,
        verbose_name="Ro'yxatga olish to'lovi bormi"
    )
    registration_fee_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0'),
        verbose_name="Ro'yxatga olish summasi"
    )

    # === Free trial ===
    first_month_free_days = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Birinchi oy bepul kun"
    )

    # === Mode-specific (per_lesson, per_attendance, hourly) ===
    price_per_lesson = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        verbose_name="1 dars narxi (per_lesson/per_attendance uchun)"
    )
    price_per_hour = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        verbose_name="1 soat narxi (hourly uchun)"
    )

    # === Custom / future ===
    extra_settings = models.JSONField(
        default=dict, blank=True,
        verbose_name="Qo'shimcha sozlamalar"
    )

    class Meta:
        verbose_name = "Billing profili"
        verbose_name_plural = "Billing profillari"
        ordering = ['branch', '-is_default', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['branch', 'name'],
                name='unique_billing_profile_per_branch'
            ),
        ]

    def __str__(self):
        scope = self.branch.name if self.branch else "Global"
        return f"{self.name} ({self.get_mode_display()}) — {scope}"

    def clean(self):
        if self.billing_day < 1 or self.billing_day > 28:
            raise ValidationError({'billing_day': "1 va 28 oralig'ida bo'lishi kerak"})
        if self.late_fee_enabled and self.late_fee_value <= 0:
            raise ValidationError({'late_fee_value': "Penya yoqilgan bo'lsa qiymat 0 dan katta bo'lsin"})


# =============================================================================
# STUDENT LEAVE (Ta'til)
# =============================================================================

class StudentLeave(BaseModel):
    """
    O'quvchining ta'tili / dam olish davri.
    Invoice hisoblashda bu davr leave_policy bo'yicha chegirib tashlanadi.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', "Kutilmoqda"
        APPROVED = 'approved', "Tasdiqlangan"
        REJECTED = 'rejected', "Rad etilgan"
        CANCELLED = 'cancelled', "Bekor qilingan"

    group_student = models.ForeignKey(
        'groups.GroupStudent',
        on_delete=models.CASCADE,
        related_name='leaves',
        verbose_name="Guruh-O'quvchi"
    )
    start_date = models.DateField(verbose_name="Boshlanish sanasi")
    end_date = models.DateField(verbose_name="Tugash sanasi")
    reason = models.TextField(verbose_name="Sabab")
    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Status"
    )
    requested_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='requested_leaves',
        verbose_name="Kim so'radi"
    )
    approved_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='approved_leaves',
        verbose_name="Kim tasdiqladi"
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="Tasdiqlangan vaqt")

    class Meta:
        verbose_name = "Ta'til"
        verbose_name_plural = "Ta'tillar"
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['group_student', 'status']),
            models.Index(fields=['start_date', 'end_date']),
        ]

    def __str__(self):
        return f"{self.group_student} — {self.start_date} → {self.end_date}"

    def clean(self):
        if self.end_date < self.start_date:
            raise ValidationError({'end_date': "Tugash sanasi boshlanishdan oldin bo'lmasligi kerak"})

    @property
    def days_count(self) -> int:
        return (self.end_date - self.start_date).days + 1


# =============================================================================
# DISCOUNT
# =============================================================================

class Discount(BaseModel):
    """
    Chegirma — pluggable.
    Har xil turdagi chegirmalarni qo'llab-quvvatlaydi:
    individual, sibling, multi-course, loyalty, early payment, promo code, ...
    """

    class Kind(models.TextChoices):
        STUDENT_PERCENT = 'student_percent', "O'quvchi (foiz)"
        STUDENT_FIXED = 'student_fixed', "O'quvchi (summa)"
        SIBLING = 'sibling', "Aka-uka chegirmasi"
        MULTI_COURSE = 'multi_course', "Ko'p kurs chegirmasi"
        LOYALTY = 'loyalty', "Sodiqlik chegirmasi"
        EARLY_PAYMENT = 'early_payment', "Erta to'lov chegirmasi"
        REFERRAL = 'referral', "Tavsiya chegirmasi"
        PROMO_CODE = 'promo_code', "Promo kod"
        SCHOLARSHIP = 'scholarship', "Stipendiya"
        GROUP_PROMO = 'group_promo', "Guruh aksiyasi"
        FIRST_MONTH = 'first_month', "Birinchi oy chegirmasi"

    class ValueType(models.TextChoices):
        PERCENT = 'percent', "Foiz"
        FIXED = 'fixed', "Summa"

    kind = models.CharField(max_length=30, choices=Kind.choices, verbose_name="Chegirma turi")
    name = models.CharField(max_length=200, verbose_name="Nomi")
    code = models.CharField(
        max_length=50, unique=True, null=True, blank=True,
        verbose_name="Promo kod"
    )

    # Targets — qaysi obyektga qo'llanadi
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='billing_discounts',
        verbose_name="O'quvchi"
    )
    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='billing_discounts',
        verbose_name="Guruh"
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='billing_discounts',
        verbose_name="Kurs"
    )
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='billing_discounts',
        verbose_name="Filial"
    )

    # Qiymat
    value_type = models.CharField(
        max_length=20, choices=ValueType.choices,
        default=ValueType.PERCENT,
        verbose_name="Qiymat turi"
    )
    value = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name="Qiymat"
    )
    max_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name="Maksimal chegirma summasi"
    )

    # Muddat
    start_date = models.DateField(verbose_name="Boshlanish sanasi")
    end_date = models.DateField(null=True, blank=True, verbose_name="Tugash sanasi")

    # Promo limit
    max_uses = models.PositiveIntegerField(null=True, blank=True, verbose_name="Maksimal foydalanish")
    uses_count = models.PositiveIntegerField(default=0, verbose_name="Foydalanilgan soni")

    # Qoidalar
    stackable = models.BooleanField(
        default=False,
        verbose_name="Boshqa chegirmalar bilan birga ishlatilsinmi"
    )
    priority = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Ustuvorlik (yuqori = ustun)"
    )
    applies_to_first_month_only = models.BooleanField(
        default=False,
        verbose_name="Faqat birinchi oy"
    )
    min_months = models.PositiveSmallIntegerField(
        null=True, blank=True,
        verbose_name="Minimal oylar (loyalty uchun)"
    )

    # Boshqaruv
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    reason = models.TextField(blank=True, null=True, verbose_name="Izoh")
    approved_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='approved_billing_discounts',
        verbose_name="Tasdiqlagan"
    )

    extra_conditions = models.JSONField(
        default=dict, blank=True,
        verbose_name="Qo'shimcha shartlar"
    )

    class Meta:
        verbose_name = "Chegirma"
        verbose_name_plural = "Chegirmalar"
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['kind', 'is_active']),
            models.Index(fields=['code']),
            models.Index(fields=['student']),
            models.Index(fields=['group']),
        ]

    def __str__(self):
        if self.value_type == self.ValueType.PERCENT:
            val = f"{self.value}%"
        else:
            val = f"{self.value:,.0f} so'm"
        return f"{self.name} ({val})"

    def clean(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError({'end_date': "Tugash sanasi boshlanishdan oldin bo'lmasligi kerak"})
        if self.value_type == self.ValueType.PERCENT and self.value > 100:
            raise ValidationError({'value': "Foiz 100 dan katta bo'lmasligi kerak"})
        if self.value < 0:
            raise ValidationError({'value': "Qiymat manfiy bo'lmasligi kerak"})

    @property
    def is_expired(self) -> bool:
        if not self.end_date:
            return False
        return self.end_date < timezone.now().date()

    @property
    def is_exhausted(self) -> bool:
        if self.max_uses is None:
            return False
        return self.uses_count >= self.max_uses

    @property
    def is_usable(self) -> bool:
        return self.is_active and not self.is_expired and not self.is_exhausted

    def calculate(self, base_amount: Decimal) -> Decimal:
        """Berilgan summadan chegirma summasini hisoblash."""
        base_amount = Decimal(base_amount)
        if self.value_type == self.ValueType.PERCENT:
            discount = base_amount * (self.value / Decimal('100'))
        else:
            discount = min(self.value, base_amount)
        if self.max_amount is not None:
            discount = min(discount, self.max_amount)
        return discount.quantize(Decimal('0.01'))


# =============================================================================
# INVOICE
# =============================================================================

class Invoice(BaseModel):
    """
    Hisob-faktura — billing tizimining haqiqat manbasi.
    Har bir o'quvchi-guruh-davr uchun bitta invoice yaratiladi.
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', "Qoralama"
        UNPAID = 'unpaid', "To'lanmagan"
        PARTIAL = 'partial', "Qisman to'langan"
        PAID = 'paid', "To'langan"
        OVERDUE = 'overdue', "Muddati o'tgan"
        CANCELLED = 'cancelled', "Bekor qilingan"

    # === Subject ===
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.PROTECT,
        related_name='billing_invoices',
        verbose_name="O'quvchi"
    )
    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.PROTECT,
        related_name='billing_invoices',
        verbose_name="Guruh"
    )
    group_student = models.ForeignKey(
        'groups.GroupStudent',
        on_delete=models.PROTECT,
        related_name='billing_invoices',
        verbose_name="Guruh-O'quvchi"
    )
    billing_profile = models.ForeignKey(
        BillingProfile,
        on_delete=models.PROTECT,
        related_name='invoices',
        verbose_name="Billing profili"
    )

    # === Identification ===
    number = models.CharField(
        max_length=50, unique=True,
        verbose_name="Invoice raqami"
    )

    # === Period ===
    period_month = models.PositiveSmallIntegerField(verbose_name="Oy (1-12)")
    period_year = models.PositiveSmallIntegerField(verbose_name="Yil")
    period_start = models.DateField(verbose_name="Davr boshi")
    period_end = models.DateField(verbose_name="Davr oxiri")

    # === Calculation snapshot (audit uchun) ===
    base_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0'),
        verbose_name="Asosiy summa"
    )
    discount_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0'),
        verbose_name="Chegirma summasi"
    )
    leave_credit_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0'),
        verbose_name="Ta'til uchun qaytarim"
    )
    late_fee_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0'),
        verbose_name="Penya summasi"
    )
    extra_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0'),
        verbose_name="Qo'shimcha summa"
    )
    total_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0'),
        verbose_name="Jami to'lash kerak"
    )
    paid_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0'),
        verbose_name="To'langan summa"
    )

    # === Pro-rate ma'lumoti (audit uchun) ===
    billable_days = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="To'lashga tegishli kunlar"
    )
    total_period_days = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Davrdagi jami kunlar"
    )
    billable_lessons = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="To'lashga tegishli darslar"
    )
    total_period_lessons = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Davrdagi jami darslar"
    )

    # === Status / muddatlar ===
    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Status"
    )
    issue_date = models.DateField(default=timezone.now, verbose_name="Berilgan sana")
    due_date = models.DateField(verbose_name="To'lov muddati")
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="To'liq to'langan vaqt")

    # === Payments link ===
    payments = models.ManyToManyField(
        'payments.Payment',
        blank=True,
        related_name='billing_invoices',
        verbose_name="Bog'langan to'lovlar"
    )

    note = models.TextField(blank=True, null=True, verbose_name="Izoh")

    class Meta:
        verbose_name = "Invoice"
        verbose_name_plural = "Invoicelar"
        ordering = ['-period_year', '-period_month', '-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['group_student', 'period_year', 'period_month'],
                name='unique_invoice_per_period'
            ),
        ]
        indexes = [
            models.Index(fields=['student', 'status']),
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['period_year', 'period_month']),
        ]

    def __str__(self):
        return f"{self.number} — {self.student} — {self.period_month}/{self.period_year}"

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = self._generate_number()
        # Total ni snapshotlar asosida hisoblash
        self.total_amount = (
            self.base_amount
            - self.discount_amount
            - self.leave_credit_amount
            + self.late_fee_amount
            + self.extra_amount
        )
        if self.total_amount < 0:
            self.total_amount = Decimal('0')
        super().save(*args, **kwargs)

    def _generate_number(self) -> str:
        from django.db.models import Max
        prefix = f"INV-{self.period_year}{self.period_month:02d}"
        last = (
            Invoice.objects
            .filter(number__startswith=prefix)
            .aggregate(m=Max('number'))['m']
        )
        if last:
            try:
                seq = int(last.split('-')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"{prefix}-{seq:05d}"

    @property
    def remaining(self) -> Decimal:
        return max(self.total_amount - self.paid_amount, Decimal('0'))

    @property
    def is_paid(self) -> bool:
        return self.status == self.Status.PAID

    @property
    def is_overdue(self) -> bool:
        if self.status in (self.Status.PAID, self.Status.CANCELLED):
            return False
        return self.due_date < timezone.now().date()

    def recompute_status(self, save: bool = True):
        """paid_amount asosida statusni qayta hisoblash."""
        if self.status == self.Status.CANCELLED:
            return
        if self.paid_amount >= self.total_amount and self.total_amount > 0:
            self.status = self.Status.PAID
            if not self.paid_at:
                self.paid_at = timezone.now()
        elif self.paid_amount > 0:
            self.status = self.Status.PARTIAL
        else:
            if self.due_date < timezone.now().date():
                self.status = self.Status.OVERDUE
            else:
                self.status = self.Status.UNPAID
        if save:
            self.save(update_fields=['status', 'paid_at', 'updated_at'])


# =============================================================================
# INVOICE LINE
# =============================================================================

class InvoiceLine(BaseModel):
    """
    Invoice qatorlari — har bir tushumning batafsil yozuvi.
    Audit uchun: "Asosiy 500,000 - Sibling 75,000 - Ta'til 80,000 = 345,000"
    """

    class Kind(models.TextChoices):
        BASE = 'base', "Asosiy summa"
        DISCOUNT = 'discount', "Chegirma"
        LEAVE_CREDIT = 'leave_credit', "Ta'til chegirmasi"
        LATE_FEE = 'late_fee', "Penya"
        REGISTRATION = 'registration', "Ro'yxatga olish"
        EXTRA = 'extra', "Qo'shimcha"
        ADJUSTMENT = 'adjustment', "Tuzatish"

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name="Invoice"
    )
    kind = models.CharField(max_length=20, choices=Kind.choices, verbose_name="Tur")
    description = models.CharField(max_length=255, verbose_name="Tavsif")
    amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name="Summa",
        help_text="Chegirma uchun musbat (subtractive), penya uchun ham musbat (additive)"
    )

    # Manba (ixtiyoriy)
    discount = models.ForeignKey(
        Discount,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='invoice_lines',
        verbose_name="Chegirma"
    )
    leave = models.ForeignKey(
        StudentLeave,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='invoice_lines',
        verbose_name="Ta'til"
    )

    meta = models.JSONField(default=dict, blank=True, verbose_name="Qo'shimcha ma'lumot")

    class Meta:
        verbose_name = "Invoice qatori"
        verbose_name_plural = "Invoice qatorlari"
        ordering = ['invoice', 'created_at']

    def __str__(self):
        return f"{self.invoice.number} / {self.get_kind_display()} / {self.amount}"
