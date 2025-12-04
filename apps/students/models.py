"""
Edvora - Students Model
"""

from django.db import models
from core.models import BaseModel


class Student(BaseModel):
    """
    O'quvchi
    """

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Faol'
        INACTIVE = 'inactive', 'Faol emas'
        GRADUATED = 'graduated', 'Bitirgan'
        DROPPED = 'dropped', 'Chiqib ketgan'
        FROZEN = 'frozen', 'Muzlatilgan'

    class Gender(models.TextChoices):
        MALE = 'male', 'Erkak'
        FEMALE = 'female', 'Ayol'

    # Shaxsiy ma'lumotlar
    first_name = models.CharField(
        max_length=100,
        verbose_name="Ism"
    )
    last_name = models.CharField(
        max_length=100,
        verbose_name="Familiya"
    )
    phone = models.CharField(
        max_length=20,
        verbose_name="Telefon"
    )
    phone_secondary = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Qo'shimcha telefon"
    )
    email = models.EmailField(
        blank=True,
        null=True,
        verbose_name="Email"
    )
    photo = models.ImageField(
        upload_to='students/photos/',
        blank=True,
        null=True,
        verbose_name="Rasm"
    )

    # Qo'shimcha
    birth_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Tug'ilgan sana"
    )
    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
        blank=True,
        null=True,
        verbose_name="Jinsi"
    )
    address = models.TextField(
        blank=True,
        null=True,
        verbose_name="Manzil"
    )

    # Ota-ona
    parent_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Ota-ona ismi"
    )
    parent_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Ota-ona telefoni"
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name="Status"
    )
    enrolled_date = models.DateField(
        auto_now_add=True,
        verbose_name="Ro'yxatdan o'tgan sana"
    )

    # Balans
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Balans"
    )

    # Telegram
    telegram_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Telegram ID"
    )
    telegram_username = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Telegram username"
    )

    # Izoh
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Izoh"
    )

    # Qayerdan keldi
    source = models.CharField(
        max_length=50,
        choices=[
            ('website', 'Veb-sayt'),
            ('instagram', 'Instagram'),
            ('telegram', 'Telegram'),
            ('referral', 'Tavsiya'),
            ('walk_in', 'O\'zi keldi'),
            ('other', 'Boshqa'),
        ],
        default='walk_in',
        verbose_name="Manba"
    )

    class Meta:
        verbose_name = "O'quvchi"
        verbose_name_plural = "O'quvchilar"
        ordering = ['-created_at']

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    @property
    def has_debt(self):
        return self.balance < 0