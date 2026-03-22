"""
Edvora - Branch (Filial) Model
O'quv markazning filiallari
"""

from django.db import models
from core.models import BaseModel


class Branch(BaseModel):
    """
    Filial - o'quv markaz bo'limlari
    """

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Faol'
        INACTIVE = 'inactive', 'Faol emas'

    name = models.CharField(
        max_length=200,
        verbose_name="Nomi"
    )
    address = models.TextField(
        verbose_name="Manzil"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Telefon"
    )
    phone_secondary = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Qo'shimcha telefon"
    )

    # Lokatsiya
    city = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Shahar"
    )
    district = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Tuman"
    )
    landmark = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Mo'ljal",
        help_text="Yaqin atrofdagi taniqli joy"
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name="Kenglik (lat)"
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name="Uzunlik (lng)"
    )

    # Ish vaqti
    working_hours = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Ish vaqti",
        help_text='{"start": "08:00", "end": "21:00"}'
    )
    working_days = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Ish kunlari",
        help_text="[0,1,2,3,4,5] = Dush-Shanba"
    )

    # Boshqaruvchi
    manager_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Boshqaruvchi ismi"
    )
    manager_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Boshqaruvchi telefoni"
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name="Status"
    )
    is_main = models.BooleanField(
        default=False,
        verbose_name="Asosiy filial"
    )

    class Meta:
        verbose_name = "Filial"
        verbose_name_plural = "Filiallar"
        ordering = ['-is_main', 'name']

    def __str__(self):
        return self.name

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    @property
    def groups_count(self):
        return self.groups.filter(status='active').count()

    @property
    def rooms_count(self):
        return self.rooms.count()

    @property
    def teachers_count(self):
        return self.teachers.filter(status='active').count()

    @property
    def students_count(self):
        return self.students.filter(status='active').count()
