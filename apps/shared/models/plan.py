"""
Edvora - Plan Model
SaaS tarif rejalari
"""

from django.db import models
from core.models import BaseModel


class Plan(BaseModel):
    """
    Tarif rejasi modeli
    Starter, Pro, Business
    """

    class PlanType(models.TextChoices):
        STARTER = 'starter', 'Starter'
        PRO = 'pro', 'Pro'
        BUSINESS = 'business', 'Business'
        ENTERPRISE = 'enterprise', 'Enterprise'

    # Asosiy
    name = models.CharField(
        max_length=100,
        verbose_name="Nomi"
    )
    slug = models.SlugField(
        max_length=50,
        unique=True,
        verbose_name="Slug"
    )
    plan_type = models.CharField(
        max_length=20,
        choices=PlanType.choices,
        default=PlanType.STARTER,
        verbose_name="Tarif turi"
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Tavsif"
    )

    # Narxlar
    price_monthly = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Oylik narx"
    )
    price_yearly = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Yillik narx"
    )

    # Limitlar
    max_students = models.IntegerField(
        default=50,
        verbose_name="Max o'quvchilar"
    )
    max_groups = models.IntegerField(
        default=10,
        verbose_name="Max guruhlar"
    )
    max_teachers = models.IntegerField(
        default=5,
        verbose_name="Max o'qituvchilar"
    )
    max_admins = models.IntegerField(
        default=2,
        verbose_name="Max adminlar"
    )

    # Features (JSON)
    features = models.JSONField(
        default=dict,
        verbose_name="Imkoniyatlar"
    )

    # Status
    is_active = models.BooleanField(
        default=True,
        verbose_name="Faol"
    )
    is_popular = models.BooleanField(
        default=False,
        verbose_name="Mashhur"
    )
    sort_order = models.IntegerField(
        default=0,
        verbose_name="Tartib"
    )

    class Meta:
        verbose_name = "Tarif"
        verbose_name_plural = "Tariflar"
        ordering = ['sort_order', 'price_monthly']

    def __str__(self):
        return f"{self.name} - {self.price_monthly:,.0f} so'm/oy"

    @classmethod
    def get_default_features(cls, plan_type):
        """Har bir tarif turi uchun default features"""
        features = {
            'starter': {
                'students': True,
                'groups': True,
                'attendance': True,
                'payments': True,
                'telegram_bot': False,
                'online_payment': False,
                'sms_notifications': False,
                'finance_reports': False,
                'marketing': False,
                'ai_features': False,
                'api_access': False,
                'priority_support': False,
            },
            'pro': {
                'students': True,
                'groups': True,
                'attendance': True,
                'payments': True,
                'telegram_bot': True,
                'online_payment': True,
                'sms_notifications': True,
                'finance_reports': True,
                'marketing': False,
                'ai_features': False,
                'api_access': False,
                'priority_support': False,
            },
            'business': {
                'students': True,
                'groups': True,
                'attendance': True,
                'payments': True,
                'telegram_bot': True,
                'online_payment': True,
                'sms_notifications': True,
                'finance_reports': True,
                'marketing': True,
                'ai_features': True,
                'api_access': True,
                'priority_support': True,
            },
            'enterprise': {
                'students': True,
                'groups': True,
                'attendance': True,
                'payments': True,
                'telegram_bot': True,
                'online_payment': True,
                'sms_notifications': True,
                'finance_reports': True,
                'marketing': True,
                'ai_features': True,
                'api_access': True,
                'priority_support': True,
                'custom_features': True,
                'dedicated_support': True,
            },
        }
        return features.get(plan_type, features['starter'])

    def has_feature(self, feature_name):
        """Tarif bu feature'ga ega ekanligini tekshirish"""
        return self.features.get(feature_name, False)