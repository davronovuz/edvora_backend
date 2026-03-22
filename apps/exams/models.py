"""
Edvora - Exams, Homework & Lesson Plans
Imtihonlar, uy vazifalari, baholar, dars rejalari
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import BaseModel


class Exam(BaseModel):
    """
    Imtihon yoki test
    """

    class ExamType(models.TextChoices):
        QUIZ = 'quiz', 'Quiz (tez test)'
        MIDTERM = 'midterm', 'Oraliq imtihon'
        FINAL = 'final', 'Yakuniy imtihon'
        PLACEMENT = 'placement', 'Daraja aniqlash'
        MOCK = 'mock', 'Sinov imtihon'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Qoralama'
        SCHEDULED = 'scheduled', 'Rejalashtirilgan'
        IN_PROGRESS = 'in_progress', "O'tkazilmoqda"
        COMPLETED = 'completed', 'Tugallangan'
        CANCELLED = 'cancelled', 'Bekor qilingan'

    group = models.ForeignKey(
        'groups.Group', on_delete=models.CASCADE,
        related_name='exams', verbose_name="Guruh"
    )
    title = models.CharField(max_length=255, verbose_name="Sarlavha")
    description = models.TextField(blank=True, null=True, verbose_name="Tavsif")
    exam_type = models.CharField(
        max_length=20, choices=ExamType.choices,
        default=ExamType.QUIZ, verbose_name="Turi"
    )
    max_score = models.DecimalField(
        max_digits=6, decimal_places=2, default=100,
        verbose_name="Maksimal ball"
    )
    passing_score = models.DecimalField(
        max_digits=6, decimal_places=2, default=60,
        verbose_name="O'tish bali"
    )
    exam_date = models.DateField(verbose_name="Imtihon sanasi")
    start_time = models.TimeField(blank=True, null=True, verbose_name="Boshlanish vaqti")
    duration_minutes = models.PositiveIntegerField(
        default=60, verbose_name="Davomiyligi (daqiqa)"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.DRAFT, verbose_name="Status"
    )
    created_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True,
        related_name='created_exams', verbose_name="Kim yaratdi"
    )

    class Meta:
        verbose_name = "Imtihon"
        verbose_name_plural = "Imtihonlar"
        ordering = ['-exam_date']

    def __str__(self):
        return f"{self.title} - {self.group.name}"

    @property
    def average_score(self):
        results = self.results.filter(status='graded')
        if not results.exists():
            return 0
        return round(
            sum(r.score for r in results) / results.count(), 1
        )

    @property
    def pass_rate(self):
        results = self.results.filter(status='graded')
        if not results.exists():
            return 0
        passed = results.filter(score__gte=self.passing_score).count()
        return round(passed / results.count() * 100, 1)


class ExamResult(BaseModel):
    """
    Imtihon natijasi - har bir o'quvchi uchun
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Kutilmoqda'
        GRADED = 'graded', 'Baholangan'
        ABSENT = 'absent', 'Kelmagan'

    exam = models.ForeignKey(
        Exam, on_delete=models.CASCADE,
        related_name='results', verbose_name="Imtihon"
    )
    student = models.ForeignKey(
        'students.Student', on_delete=models.CASCADE,
        related_name='exam_results', verbose_name="O'quvchi"
    )
    score = models.DecimalField(
        max_digits=6, decimal_places=2, default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Ball"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.PENDING, verbose_name="Status"
    )
    feedback = models.TextField(blank=True, null=True, verbose_name="Izoh")
    graded_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='graded_results', verbose_name="Kim baholadi"
    )
    graded_at = models.DateTimeField(blank=True, null=True, verbose_name="Baholangan vaqt")

    class Meta:
        verbose_name = "Imtihon natijasi"
        verbose_name_plural = "Imtihon natijalari"
        unique_together = ['exam', 'student']
        ordering = ['-score']

    def __str__(self):
        return f"{self.student.full_name} - {self.score}/{self.exam.max_score}"

    @property
    def percentage(self):
        if self.exam.max_score == 0:
            return 0
        return round(float(self.score) / float(self.exam.max_score) * 100, 1)

    @property
    def is_passed(self):
        return self.score >= self.exam.passing_score

    @property
    def grade_letter(self):
        """Harf baho: A, B, C, D, F"""
        pct = self.percentage
        if pct >= 90:
            return 'A'
        elif pct >= 80:
            return 'B'
        elif pct >= 70:
            return 'C'
        elif pct >= 60:
            return 'D'
        return 'F'


class Homework(BaseModel):
    """
    Uy vazifasi
    """

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Faol'
        CLOSED = 'closed', 'Yopilgan'
        CANCELLED = 'cancelled', 'Bekor qilingan'

    group = models.ForeignKey(
        'groups.Group', on_delete=models.CASCADE,
        related_name='homeworks', verbose_name="Guruh"
    )
    title = models.CharField(max_length=255, verbose_name="Sarlavha")
    description = models.TextField(verbose_name="Tavsif")
    max_score = models.DecimalField(
        max_digits=6, decimal_places=2, default=10,
        verbose_name="Maksimal ball"
    )
    assigned_date = models.DateField(verbose_name="Berilgan sana")
    due_date = models.DateField(verbose_name="Topshirish muddati")
    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.ACTIVE, verbose_name="Status"
    )
    attachment = models.FileField(
        upload_to='homeworks/', blank=True, null=True,
        verbose_name="Fayl"
    )
    created_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True,
        related_name='created_homeworks', verbose_name="Kim berdi"
    )

    class Meta:
        verbose_name = "Uy vazifasi"
        verbose_name_plural = "Uy vazifalari"
        ordering = ['-due_date']

    def __str__(self):
        return f"{self.title} - {self.group.name}"

    @property
    def is_overdue(self):
        from django.utils import timezone
        return self.due_date < timezone.now().date() and self.status == self.Status.ACTIVE

    @property
    def submission_rate(self):
        from apps.groups.models import GroupStudent
        total = GroupStudent.objects.filter(group=self.group, is_active=True).count()
        submitted = self.submissions.exclude(status='pending').count()
        if total == 0:
            return 0
        return round(submitted / total * 100, 1)


class HomeworkSubmission(BaseModel):
    """
    Uy vazifasi topshirish
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Topshirilmagan'
        SUBMITTED = 'submitted', 'Topshirilgan'
        GRADED = 'graded', 'Baholangan'
        LATE = 'late', 'Kechikib topshirilgan'
        RESUBMIT = 'resubmit', 'Qayta topshirish kerak'

    homework = models.ForeignKey(
        Homework, on_delete=models.CASCADE,
        related_name='submissions', verbose_name="Vazifa"
    )
    student = models.ForeignKey(
        'students.Student', on_delete=models.CASCADE,
        related_name='homework_submissions', verbose_name="O'quvchi"
    )
    score = models.DecimalField(
        max_digits=6, decimal_places=2, default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Ball"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.PENDING, verbose_name="Status"
    )
    submitted_at = models.DateTimeField(blank=True, null=True, verbose_name="Topshirilgan vaqt")
    attachment = models.FileField(
        upload_to='homework_submissions/', blank=True, null=True,
        verbose_name="Topshiriq fayli"
    )
    comment = models.TextField(blank=True, null=True, verbose_name="O'quvchi izohi")
    feedback = models.TextField(blank=True, null=True, verbose_name="O'qituvchi izohi")
    graded_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='graded_submissions', verbose_name="Kim baholadi"
    )

    class Meta:
        verbose_name = "Vazifa topshirish"
        verbose_name_plural = "Vazifa topshirishlar"
        unique_together = ['homework', 'student']
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.student.full_name} - {self.homework.title}"

    @property
    def is_late(self):
        if not self.submitted_at:
            return False
        return self.submitted_at.date() > self.homework.due_date


class LessonPlan(BaseModel):
    """
    Dars rejasi - har bir dars uchun reja
    O'qituvchi nima o'tishini, materiallarni, maqsadlarni belgilaydi
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Qoralama'
        READY = 'ready', 'Tayyor'
        COMPLETED = 'completed', 'O\'tildi'
        CANCELLED = 'cancelled', 'Bekor'

    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.CASCADE,
        related_name='lesson_plans',
        verbose_name="Guruh"
    )
    lesson_number = models.PositiveIntegerField(
        verbose_name="Dars raqami"
    )
    title = models.CharField(
        max_length=255,
        verbose_name="Mavzu"
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Tavsif"
    )
    objectives = models.TextField(
        blank=True,
        null=True,
        verbose_name="Dars maqsadlari"
    )
    materials = models.TextField(
        blank=True,
        null=True,
        verbose_name="Materiallar (darslik, video, link...)"
    )
    homework_description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Uy vazifasi tavsifi"
    )
    date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Dars sanasi"
    )
    duration_minutes = models.PositiveIntegerField(
        default=90,
        verbose_name="Davomiylik (daqiqa)"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Holat"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="O'qituvchi eslatmalari"
    )
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='lesson_plans',
        verbose_name="Yaratgan"
    )

    class Meta:
        verbose_name = "Dars rejasi"
        verbose_name_plural = "Dars rejalari"
        ordering = ['group', 'lesson_number']
        unique_together = ['group', 'lesson_number']

    def __str__(self):
        return f"{self.group.name} - #{self.lesson_number}: {self.title}"
