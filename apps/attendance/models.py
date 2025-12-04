"""
Edvora - Attendance Model
Davomat qayd qilish
"""

from django.db import models
from core.models import BaseModel


class Attendance(BaseModel):
    """
    Davomat
    Har bir dars uchun har bir o'quvchining davomati
    """

    class Status(models.TextChoices):
        PRESENT = 'present', 'Keldi'
        ABSENT = 'absent', 'Kelmadi'
        LATE = 'late', 'Kechikdi'
        EXCUSED = 'excused', 'Sababli'

    # Guruh va o'quvchi
    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name="Guruh"
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name="O'quvchi"
    )

    # Sana va vaqt
    date = models.DateField(
        verbose_name="Sana"
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PRESENT,
        verbose_name="Status"
    )

    # Kim tomonidan
    marked_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='marked_attendances',
        verbose_name="Kim belgiladi"
    )

    # Izoh
    note = models.TextField(
        blank=True,
        null=True,
        verbose_name="Izoh"
    )

    class Meta:
        verbose_name = "Davomat"
        verbose_name_plural = "Davomatlar"
        unique_together = ['group', 'student', 'date']
        ordering = ['-date', 'student__first_name']

    def __str__(self):
        return f"{self.student.full_name} - {self.date} - {self.get_status_display()}"


class AttendanceSession(BaseModel):
    """
    Davomat sessiyasi
    Bir guruhning bir kunlik davomati
    """

    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.CASCADE,
        related_name='attendance_sessions',
        verbose_name="Guruh"
    )
    date = models.DateField(
        verbose_name="Sana"
    )

    # Statistika
    total_students = models.PositiveIntegerField(
        default=0,
        verbose_name="Jami o'quvchilar"
    )
    present_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Kelganlar"
    )
    absent_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Kelmaganlar"
    )
    late_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Kechikkanlar"
    )

    # Kim tomonidan
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_sessions',
        verbose_name="Kim yaratdi"
    )

    class Meta:
        verbose_name = "Davomat sessiyasi"
        verbose_name_plural = "Davomat sessiyalari"
        unique_together = ['group', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.group.name} - {self.date}"

    def update_stats(self):
        """Statistikani yangilash"""
        attendances = Attendance.objects.filter(group=self.group, date=self.date)
        self.total_students = attendances.count()
        self.present_count = attendances.filter(status='present').count()
        self.absent_count = attendances.filter(status='absent').count()
        self.late_count = attendances.filter(status='late').count()
        self.save()