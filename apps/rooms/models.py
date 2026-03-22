"""
Edvora - Rooms (Xonalar) Model
Xona boshqaruvi, sig'im, jihozlar, band/bo'sh vaqtlar
"""

from django.db import models
from core.models import BaseModel


class Room(BaseModel):
    """
    Xona - o'quv markaz xonalari
    """

    class RoomType(models.TextChoices):
        CLASSROOM = 'classroom', "Sinf xona"
        LAB = 'lab', 'Laboratoriya'
        CONFERENCE = 'conference', "Majlis xonasi"
        OFFICE = 'office', 'Ofis'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Faol'
        MAINTENANCE = 'maintenance', "Ta'mirda"
        INACTIVE = 'inactive', 'Faol emas'

    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rooms',
        verbose_name="Filial"
    )
    name = models.CharField(max_length=100, verbose_name="Nomi")
    number = models.CharField(
        max_length=20, unique=True, verbose_name="Xona raqami",
        help_text="Masalan: 101, A-201"
    )
    floor = models.PositiveIntegerField(default=1, verbose_name="Qavat")
    room_type = models.CharField(
        max_length=20, choices=RoomType.choices,
        default=RoomType.CLASSROOM, verbose_name="Xona turi"
    )
    capacity = models.PositiveIntegerField(verbose_name="Sig'imi (o'rin)")
    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.ACTIVE, verbose_name="Status"
    )

    # Jihozlar
    equipment = models.JSONField(
        default=list, blank=True, verbose_name="Jihozlar",
        help_text='["proyektor", "doska", "kompyuter"]'
    )
    has_projector = models.BooleanField(default=False, verbose_name="Proyektor")
    has_whiteboard = models.BooleanField(default=True, verbose_name="Doska")
    has_computers = models.BooleanField(default=False, verbose_name="Kompyuterlar")
    has_air_conditioning = models.BooleanField(default=False, verbose_name="Konditsioner")

    photo = models.ImageField(upload_to='rooms/', blank=True, null=True, verbose_name="Rasm")
    hourly_rate = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Soatlik narx"
    )
    description = models.TextField(blank=True, null=True, verbose_name="Tavsif")

    class Meta:
        verbose_name = "Xona"
        verbose_name_plural = "Xonalar"
        ordering = ['number']

    def __str__(self):
        return f"{self.number} - {self.name} ({self.capacity} o'rin)"

    @property
    def is_available(self):
        return self.status == self.Status.ACTIVE

    def is_available_at(self, date, start_time, end_time, exclude_group_id=None):
        """Berilgan vaqtda xona bo'shmi? Schedule conflict detection."""
        from apps.groups.models import Group
        weekday = date.weekday()

        conflicting = Group.objects.filter(
            room=self,
            status__in=['forming', 'active'],
            start_date__lte=date,
            days__contains=weekday,
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=date)
        ).filter(
            start_time__lt=end_time,
            end_time__gt=start_time,
        )

        if exclude_group_id:
            conflicting = conflicting.exclude(id=exclude_group_id)

        return not conflicting.exists()

    def get_schedule_for_date(self, date):
        """Berilgan kunga xona jadvali"""
        from apps.groups.models import Group
        weekday = date.weekday()
        return Group.objects.filter(
            room=self,
            status__in=['forming', 'active'],
            start_date__lte=date,
            days__contains=weekday,
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=date)
        ).select_related('course', 'teacher').order_by('start_time')
