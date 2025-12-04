"""
Edvora - Finance Models
Daromad, xarajat, tranzaksiyalar
"""

from django.db import models
from core.models import BaseModel


class ExpenseCategory(BaseModel):
    """
    Xarajat kategoriyasi
    Masalan: Ijara, Kommunal, Ish haqi, Marketing
    """

    name = models.CharField(
        max_length=100,
        verbose_name="Nomi"
    )
    slug = models.SlugField(
        max_length=50,
        unique=True,
        verbose_name="Slug"
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Icon"
    )
    color = models.CharField(
        max_length=7,
        default='#EF4444',
        verbose_name="Rang"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Faol"
    )

    class Meta:
        verbose_name = "Xarajat kategoriyasi"
        verbose_name_plural = "Xarajat kategoriyalari"
        ordering = ['name']

    def __str__(self):
        return self.name


class Expense(BaseModel):
    """
    Xarajat
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Kutilmoqda'
        APPROVED = 'approved', 'Tasdiqlangan'
        PAID = 'paid', "To'langan"
        CANCELLED = 'cancelled', 'Bekor qilingan'

    # Kategoriya
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name='expenses',
        verbose_name="Kategoriya"
    )

    # Ma'lumotlar
    title = models.CharField(
        max_length=255,
        verbose_name="Sarlavha"
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Tavsif"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Summa"
    )

    # Sana
    expense_date = models.DateField(
        verbose_name="Xarajat sanasi"
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PAID,
        verbose_name="Status"
    )

    # Kim kiritdi
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_expenses',
        verbose_name="Kim kiritdi"
    )
    approved_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_expenses',
        verbose_name="Kim tasdiqladi"
    )

    # Kvitansiya/Chek
    receipt = models.ImageField(
        upload_to='expenses/receipts/',
        blank=True,
        null=True,
        verbose_name="Chek/Kvitansiya"
    )

    # Takroriy xarajat
    is_recurring = models.BooleanField(
        default=False,
        verbose_name="Takroriy"
    )
    recurring_day = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Har oyning qaysi kuni"
    )

    class Meta:
        verbose_name = "Xarajat"
        verbose_name_plural = "Xarajatlar"
        ordering = ['-expense_date', '-created_at']

    def __str__(self):
        return f"{self.title} - {self.amount:,.0f} so'm"


class Transaction(BaseModel):
    """
    Moliyaviy tranzaksiya
    Barcha pul oqimlarini kuzatish
    """

    class TransactionType(models.TextChoices):
        INCOME = 'income', 'Kirim'
        EXPENSE = 'expense', 'Chiqim'
        TRANSFER = 'transfer', "O'tkazma"
        REFUND = 'refund', 'Qaytarish'
        SALARY = 'salary', 'Ish haqi'

    # Tur
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        verbose_name="Turi"
    )

    # Summa
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Summa"
    )

    # Sana
    transaction_date = models.DateField(
        verbose_name="Sana"
    )

    # Tavsif
    description = models.TextField(
        verbose_name="Tavsif"
    )

    # Bog'langan ob'ektlar (ixtiyoriy)
    payment = models.ForeignKey(
        'payments.Payment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name="To'lov"
    )
    expense = models.ForeignKey(
        Expense,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name="Xarajat"
    )
    salary = models.ForeignKey(
        'finance.Salary',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name="Ish haqi"
    )

    # Kim kiritdi
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_transactions',
        verbose_name="Kim kiritdi"
    )

    class Meta:
        verbose_name = "Tranzaksiya"
        verbose_name_plural = "Tranzaksiyalar"
        ordering = ['-transaction_date', '-created_at']

    def __str__(self):
        sign = '+' if self.transaction_type == 'income' else '-'
        return f"{sign}{self.amount:,.0f} - {self.description[:50]}"


class Salary(BaseModel):
    """
    Ish haqi
    """

    class Status(models.TextChoices):
        CALCULATED = 'calculated', 'Hisoblangan'
        APPROVED = 'approved', 'Tasdiqlangan'
        PAID = 'paid', "To'langan"
        CANCELLED = 'cancelled', 'Bekor qilingan'

    # O'qituvchi
    teacher = models.ForeignKey(
        'teachers.Teacher',
        on_delete=models.PROTECT,
        related_name='salaries',
        verbose_name="O'qituvchi"
    )

    # Davr
    period_month = models.PositiveIntegerField(
        verbose_name="Oy"
    )
    period_year = models.PositiveIntegerField(
        verbose_name="Yil"
    )

    # Hisoblash
    base_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Asosiy ish haqi"
    )
    bonus = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Bonus"
    )
    deduction = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Ushlab qolish"
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Jami"
    )

    # Qo'shimcha ma'lumot
    total_lessons = models.PositiveIntegerField(
        default=0,
        verbose_name="Jami darslar"
    )
    total_students = models.PositiveIntegerField(
        default=0,
        verbose_name="Jami o'quvchilar"
    )
    calculation_details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Hisoblash tafsilotlari"
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CALCULATED,
        verbose_name="Status"
    )

    # Tasdiq va to'lov
    approved_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_salaries',
        verbose_name="Tasdiqlagan"
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Tasdiqlangan vaqt"
    )
    paid_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paid_salaries',
        verbose_name="To'lagan"
    )
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="To'langan vaqt"
    )

    # Izoh
    note = models.TextField(
        blank=True,
        null=True,
        verbose_name="Izoh"
    )

    class Meta:
        verbose_name = "Ish haqi"
        verbose_name_plural = "Ish haqlari"
        unique_together = ['teacher', 'period_month', 'period_year']
        ordering = ['-period_year', '-period_month']

    def __str__(self):
        return f"{self.teacher.full_name} - {self.period_month}/{self.period_year}"

    def save(self, *args, **kwargs):
        # Jami hisoblash
        self.total = self.base_salary + self.bonus - self.deduction
        super().save(*args, **kwargs)