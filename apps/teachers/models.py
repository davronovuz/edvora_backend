"""
Edvora - Teachers Model
"""

from django.db import models
from core.models import BaseModel


class Teacher(BaseModel):
    """
    O'qituvchi
    """

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Faol'
        INACTIVE = 'inactive', 'Faol emas'
        ON_LEAVE = 'on_leave', 'Ta\'tilda'

    # User bilan bog'lanish (agar tizimga kirsa)
    user = models.OneToOneField(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='teacher_profile',
        verbose_name="Foydalanuvchi"
    )

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
        upload_to='teachers/photos/',
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
    address = models.TextField(
        blank=True,
        null=True,
        verbose_name="Manzil"
    )
    bio = models.TextField(
        blank=True,
        null=True,
        verbose_name="Bio"
    )

    # O'qitadigan fanlar
    subjects = models.ManyToManyField(
        'courses.Subject',
        related_name='teachers',
        blank=True,
        verbose_name="Fanlar"
    )

    # Ish haqqi
    salary_type = models.CharField(
        max_length=20,
        choices=[
            ('fixed', 'Belgilangan'),
            ('hourly', 'Soatlik'),
            ('percent', 'Foizli'),
        ],
        default='fixed',
        verbose_name="Ish haqi turi"
    )
    salary_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Ish haqi miqdori"
    )
    salary_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="Ish haqi foizi"
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name="Status"
    )
    hired_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Ishga kirgan sana"
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

    class Meta:
        verbose_name = "O'qituvchi"
        verbose_name_plural = "O'qituvchilar"
        ordering = ['first_name', 'last_name']

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE