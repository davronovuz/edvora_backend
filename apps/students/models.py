"""
Edvora - Students Model
"""

from django.db import models
from core.models import BaseModel


class Student(BaseModel):
    """
    O'quvchi
    """

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Faol'
        INACTIVE = 'inactive', 'Faol emas'
        GRADUATED = 'graduated', 'Bitirgan'
        DROPPED = 'dropped', 'Chiqib ketgan'
        FROZEN = 'frozen', 'Muzlatilgan'

    class Gender(models.TextChoices):
        MALE = 'male', 'Erkak'
        FEMALE = 'female', 'Ayol'

    # Filial
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students',
        verbose_name="Filial"
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
        upload_to='students/photos/',
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
    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
        blank=True,
        null=True,
        verbose_name="Jinsi"
    )
    address = models.TextField(
        blank=True,
        null=True,
        verbose_name="Manzil"
    )

    # Ota-ona
    parent_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Ota-ona ismi"
    )
    parent_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Ota-ona telefoni"
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name="Status"
    )
    enrolled_date = models.DateField(
        auto_now_add=True,
        verbose_name="Ro'yxatdan o'tgan sana"
    )

    # Balans
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Balans"
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

    # Passport
    passport_series = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Pasport seriya raqami"
    )

    # Muzlatish (Freeze)
    freeze_start_date = models.DateField(
        blank=True, null=True,
        verbose_name="Muzlatish boshi"
    )
    freeze_end_date = models.DateField(
        blank=True, null=True,
        verbose_name="Muzlatish oxiri"
    )
    freeze_reason = models.TextField(
        blank=True, null=True,
        verbose_name="Muzlatish sababi"
    )

    # Arxiv
    archive_reason = models.TextField(
        blank=True, null=True,
        verbose_name="Arxiv sababi"
    )
    archived_at = models.DateTimeField(
        blank=True, null=True,
        verbose_name="Arxivga olingan vaqt"
    )

    # Izoh
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Izoh"
    )

    # Qayerdan keldi
    source = models.CharField(
        max_length=50,
        choices=[
            ('website', 'Veb-sayt'),
            ('instagram', 'Instagram'),
            ('telegram', 'Telegram'),
            ('referral', 'Tavsiya'),
            ('walk_in', 'O\'zi keldi'),
            ('other', 'Boshqa'),
        ],
        default='walk_in',
        verbose_name="Manba"
    )

    class Meta:
        verbose_name = "O'quvchi"
        verbose_name_plural = "O'quvchilar"
        ordering = ['-created_at']

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    @property
    def has_debt(self):
        return self.balance < 0

    @property
    def is_frozen(self):
        if not self.freeze_start_date:
            return False
        from django.utils import timezone
        today = timezone.now().date()
        if self.freeze_end_date:
            return self.freeze_start_date <= today <= self.freeze_end_date
        return self.freeze_start_date <= today

    def freeze(self, start_date, end_date=None, reason=''):
        self.status = self.Status.FROZEN
        self.freeze_start_date = start_date
        self.freeze_end_date = end_date
        self.freeze_reason = reason
        self.save()
        # GroupStudent recordlarni ham muzlatish
        self.groups.filter(is_active=True).update(status='frozen')

    def unfreeze(self):
        self.status = self.Status.ACTIVE
        self.freeze_start_date = None
        self.freeze_end_date = None
        self.freeze_reason = None
        self.save()
        # GroupStudent recordlarni ham aktivlashtirish
        self.groups.filter(status='frozen').update(status='active')

    def archive(self, reason=''):
        from django.utils import timezone
        self.status = self.Status.INACTIVE
        self.archive_reason = reason
        self.archived_at = timezone.now()
        self.save()


class StudentGroupNote(BaseModel):
    """
    O'quvchi uchun guruh ichidagi izoh (xulq, progress, ota-ona bilan aloqa)
    """

    class NoteType(models.TextChoices):
        BEHAVIOR = 'behavior', "Xulq"
        PROGRESS = 'progress', "O'zlashtirish"
        PARENT_CONTACT = 'parent_contact', "Ota-ona bilan aloqa"
        OTHER = 'other', "Boshqa"

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='group_notes',
        verbose_name="O'quvchi",
    )
    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.CASCADE,
        related_name='student_notes',
        verbose_name="Guruh",
    )
    note_type = models.CharField(
        max_length=20,
        choices=NoteType.choices,
        default=NoteType.OTHER,
        verbose_name="Turi",
    )
    content = models.TextField(verbose_name="Mazmun")
    is_pinned = models.BooleanField(default=False, verbose_name="Tepada")
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='authored_group_notes',
        verbose_name="Kim yozdi",
    )

    class Meta:
        verbose_name = "Guruh izohi"
        verbose_name_plural = "Guruh izohlari"
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return f"{self.student.full_name} — {self.group.name} — {self.get_note_type_display()}"