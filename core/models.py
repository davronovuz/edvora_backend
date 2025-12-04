"""
Edvora - Base Models
Barcha modellar uchun umumiy base class
"""

import uuid
from django.db import models


class TimeStampedModel(models.Model):
    """
    Barcha modellar uchun created_at va updated_at fieldlar
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqt")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqt")

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """
    UUID primary key ishlatadigan modellar uchun
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="ID"
    )

    class Meta:
        abstract = True


class BaseModel(UUIDModel, TimeStampedModel):
    """
    Asosiy base model - UUID + timestamps
    Barcha modellar shundan meros oladi
    """

    class Meta:
        abstract = True
        ordering = ['-created_at']