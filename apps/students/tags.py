"""
Edvora - Tags Model
Universal teg tizimi
"""

from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from core.models import BaseModel


class Tag(BaseModel):
    """
    Teg - rangli yorliq
    """
    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Nomi"
    )
    color = models.CharField(
        max_length=7,
        default='#3B82F6',
        verbose_name="Rang",
        help_text="HEX formatda: #FF5733"
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Tavsif"
    )

    class Meta:
        verbose_name = "Teg"
        verbose_name_plural = "Teglar"
        ordering = ['name']

    def __str__(self):
        return self.name


class TaggedItem(BaseModel):
    """
    Teg bog'lanishi - har qanday modelga teg qo'shish
    """
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        related_name='tagged_items',
        verbose_name="Teg"
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name="Model turi"
    )
    object_id = models.UUIDField(
        verbose_name="Ob'ekt ID"
    )
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        verbose_name = "Teg bog'lanishi"
        verbose_name_plural = "Teg bog'lanishlari"
        unique_together = ['tag', 'content_type', 'object_id']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f"{self.tag.name} -> {self.content_type.model}:{self.object_id}"
