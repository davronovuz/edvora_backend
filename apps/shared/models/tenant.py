"""
Edvora - Tenant Model
Har bir o'quv markaz = 1 Tenant
"""

from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from core.models import TimeStampedModel


class Tenant(TenantMixin, TimeStampedModel):
    """
    O'quv markaz (Tenant) modeli
    Har bir markaz alohida schema'da ishlaydi
    """

    class Status(models.TextChoices):
        TRIAL = 'trial', 'Sinov'
        ACTIVE = 'active', 'Faol'
        SUSPENDED = 'suspended', "To'xtatilgan"
        CANCELLED = 'cancelled', 'Bekor qilingan'

    # Asosiy ma'lumotlar
    name = models.CharField(
        max_length=255,
        verbose_name="Markaz nomi"
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name="Slug"
    )

    # Egasi ma'lumotlari
    owner_name = models.CharField(
        max_length=255,
        verbose_name="Egasi ismi"
    )
    owner_email = models.EmailField(
        verbose_name="Egasi email"
    )
    owner_phone = models.CharField(
        max_length=20,
        verbose_name="Egasi telefoni"
    )

    # Manzil
    address = models.TextField(
        blank=True,
        null=True,
        verbose_name="Manzil"
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Shahar"
    )

    # Branding
    logo = models.ImageField(
        upload_to='tenants/logos/',
        blank=True,
        null=True,
        verbose_name="Logo"
    )

    # Obuna
    plan = models.ForeignKey(
        'shared.Plan',
        on_delete=models.PROTECT,
        related_name='tenants',
        null=True,
        blank=True,
        verbose_name="Tarif rejasi"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TRIAL,
        verbose_name="Status"
    )
    trial_ends_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Sinov tugash vaqti"
    )
    subscription_ends_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Obuna tugash vaqti"
    )

    # Sozlamalar
    settings = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Sozlamalar"
    )
    timezone = models.CharField(
        max_length=50,
        default='Asia/Tashkent',
        verbose_name="Vaqt zonasi"
    )
    language = models.CharField(
        max_length=10,
        default='uz',
        verbose_name="Til"
    )
    currency = models.CharField(
        max_length=3,
        default='UZS',
        verbose_name="Valyuta"
    )

    # django-tenants uchun
    auto_create_schema = True
    auto_drop_schema = True

    class Meta:
        verbose_name = "Markaz"
        verbose_name_plural = "Markazlar"
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    @property
    def is_trial(self):
        return self.status == self.Status.TRIAL

    def get_default_settings(self):
        """Default sozlamalar"""
        return {
            'attendance_methods': ['manual', 'qr'],
            'payment_methods': ['cash', 'card'],
            'notification_channels': ['telegram', 'sms'],
            'working_days': [0, 1, 2, 3, 4, 5],  # Mon-Sat
            'working_hours': {'start': '08:00', 'end': '21:00'},
        }


class Domain(DomainMixin):
    """
    Domain modeli
    Har bir tenant uchun subdomain
    Masalan: najot.edvora.uz
    """

    class Meta:
        verbose_name = "Domain"
        verbose_name_plural = "Domainlar"

    def __str__(self):
        return self.domain