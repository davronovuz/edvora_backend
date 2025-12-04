"""
Edvora - Analytics Models
Dashboard va hisobotlar uchun cached data
"""

from django.db import models
from core.models import BaseModel


class DailyStats(BaseModel):
    """
    Kunlik statistika (cache uchun)
    Har kuni avtomatik yangilanadi
    """

    date = models.DateField(
        unique=True,
        verbose_name="Sana"
    )

    # O'quvchilar
    total_students = models.PositiveIntegerField(default=0)
    active_students = models.PositiveIntegerField(default=0)
    new_students = models.PositiveIntegerField(default=0)

    # Guruhlar
    total_groups = models.PositiveIntegerField(default=0)
    active_groups = models.PositiveIntegerField(default=0)

    # O'qituvchilar
    total_teachers = models.PositiveIntegerField(default=0)
    active_teachers = models.PositiveIntegerField(default=0)

    # Moliya
    total_income = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_expense = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_salary = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Davomat
    attendance_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Leadlar
    total_leads = models.PositiveIntegerField(default=0)
    converted_leads = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Kunlik statistika"
        verbose_name_plural = "Kunlik statistikalar"
        ordering = ['-date']

    def __str__(self):
        return f"Stats - {self.date}"


class MonthlyStats(BaseModel):
    """
    Oylik statistika
    """

    year = models.PositiveIntegerField(verbose_name="Yil")
    month = models.PositiveIntegerField(verbose_name="Oy")

    # O'quvchilar
    total_students = models.PositiveIntegerField(default=0)
    new_students = models.PositiveIntegerField(default=0)
    dropped_students = models.PositiveIntegerField(default=0)

    # Moliya
    total_income = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_expense = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_salary = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    net_profit = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Davomat
    average_attendance_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Leadlar
    total_leads = models.PositiveIntegerField(default=0)
    converted_leads = models.PositiveIntegerField(default=0)
    conversion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Oylik statistika"
        verbose_name_plural = "Oylik statistikalar"
        unique_together = ['year', 'month']
        ordering = ['-year', '-month']

    def __str__(self):
        return f"Stats - {self.month}/{self.year}"