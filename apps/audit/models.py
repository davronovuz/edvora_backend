"""
Edvora - Audit Log Model
Barcha o'zgarishlarni kuzatish: kim, qachon, nima qildi
"""

from django.db import models
from core.models import BaseModel


class AuditLog(BaseModel):
    """
    Audit log - barcha CRUD operatsiyalarni kuzatish
    """

    class Action(models.TextChoices):
        CREATE = 'create', 'Yaratish'
        UPDATE = 'update', 'Yangilash'
        DELETE = 'delete', "O'chirish"
        LOGIN = 'login', 'Kirish'
        LOGOUT = 'logout', 'Chiqish'
        PASSWORD_CHANGE = 'password_change', 'Parol o\'zgartirish'
        PAYMENT = 'payment', "To'lov"
        REFUND = 'refund', 'Qaytarish'
        TRANSFER = 'transfer', "O'tkazish"
        EXPORT = 'export', 'Eksport'

    user = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='audit_logs', verbose_name="Foydalanuvchi"
    )
    action = models.CharField(
        max_length=20, choices=Action.choices, verbose_name="Amal"
    )

    # Qaysi model va ob'ekt
    model_name = models.CharField(max_length=100, verbose_name="Model nomi")
    object_id = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Ob'ekt ID"
    )
    object_repr = models.CharField(
        max_length=500, blank=True, null=True,
        verbose_name="Ob'ekt tavsifi"
    )

    # O'zgarishlar
    changes = models.JSONField(
        default=dict, blank=True, verbose_name="O'zgarishlar",
        help_text='{"field": {"old": "...", "new": "..."}}'
    )
    extra_data = models.JSONField(
        default=dict, blank=True, verbose_name="Qo'shimcha ma'lumot"
    )

    # Texnik
    ip_address = models.GenericIPAddressField(
        blank=True, null=True, verbose_name="IP manzil"
    )
    user_agent = models.TextField(blank=True, null=True, verbose_name="User Agent")

    class Meta:
        verbose_name = "Audit log"
        verbose_name_plural = "Audit loglar"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['action', '-created_at']),
        ]

    def __str__(self):
        user_str = self.user.get_full_name() if self.user else 'System'
        return f"{user_str} - {self.get_action_display()} - {self.model_name}"

    @classmethod
    def log(cls, user, action, model_name, object_id=None,
            object_repr=None, changes=None, extra_data=None,
            ip_address=None, user_agent=None):
        """Audit log yozish uchun helper method"""
        return cls.objects.create(
            user=user,
            action=action,
            model_name=model_name,
            object_id=str(object_id) if object_id else None,
            object_repr=str(object_repr)[:500] if object_repr else None,
            changes=changes or {},
            extra_data=extra_data or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
