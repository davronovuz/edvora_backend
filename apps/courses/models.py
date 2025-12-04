"""
Edvora - Courses & Subjects Models
"""

from django.db import models
from core.models import BaseModel


class Subject(BaseModel):
    """
    Fan/Yo'nalish
    Masalan: Ingliz tili, Matematika, Python, IELTS
    """

    name = models.CharField(
        max_length=255,
        verbose_name="Nomi"
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name="Slug"
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Tavsif"
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Icon (emoji yoki class)"
    )
    color = models.CharField(
        max_length=7,
        default='#3B82F6',
        verbose_name="Rang (hex)"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Faol"
    )

    class Meta:
        verbose_name = "Fan"
        verbose_name_plural = "Fanlar"
        ordering = ['name']

    def __str__(self):
        return self.name


class Course(BaseModel):
    """
    Kurs
    Masalan: IELTS 7.0, Python Basic, Matematika 9-sinf
    """

    class Level(models.TextChoices):
        BEGINNER = 'beginner', 'Boshlang\'ich'
        ELEMENTARY = 'elementary', 'Elementary'
        INTERMEDIATE = 'intermediate', 'O\'rta'
        UPPER_INTERMEDIATE = 'upper_intermediate', 'Upper-Intermediate'
        ADVANCED = 'advanced', 'Yuqori'

    # Asosiy
    name = models.CharField(
        max_length=255,
        verbose_name="Nomi"
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        related_name='courses',
        verbose_name="Fan"
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Tavsif"
    )

    # Daraja va davomiylik
    level = models.CharField(
        max_length=20,
        choices=Level.choices,
        default=Level.BEGINNER,
        verbose_name="Daraja"
    )
    duration_months = models.PositiveIntegerField(
        default=3,
        verbose_name="Davomiyligi (oy)"
    )
    total_lessons = models.PositiveIntegerField(
        default=36,
        verbose_name="Jami darslar soni"
    )

    # Narx
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Narxi (oylik)"
    )

    # Status
    is_active = models.BooleanField(
        default=True,
        verbose_name="Faol"
    )

    class Meta:
        verbose_name = "Kurs"
        verbose_name_plural = "Kurslar"
        ordering = ['subject', 'name']

    def __str__(self):
        return f"{self.name} ({self.subject.name})"