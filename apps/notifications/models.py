"""
Edvora - Notifications Model
Xabarnomalar tizimi
"""

from django.db import models
from core.models import BaseModel


class Notification(BaseModel):
    """
    Xabarnoma
    """

    class NotificationType(models.TextChoices):
        PAYMENT = 'payment', "To'lov"
        PAYMENT_REMINDER = 'payment_reminder', "To'lov eslatmasi"
        ATTENDANCE = 'attendance', 'Davomat'
        GROUP = 'group', 'Guruh'
        SCHEDULE = 'schedule', 'Jadval'
        SYSTEM = 'system', 'Tizim'
        MARKETING = 'marketing', 'Marketing'

    class Channel(models.TextChoices):
        IN_APP = 'in_app', 'Ilova ichida'
        TELEGRAM = 'telegram', 'Telegram'
        SMS = 'sms', 'SMS'
        EMAIL = 'email', 'Email'

    class Priority(models.TextChoices):
        LOW = 'low', 'Past'
        NORMAL = 'normal', 'Normal'
        HIGH = 'high', 'Yuqori'
        URGENT = 'urgent', 'Shoshilinch'

    # Kimga
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name="Foydalanuvchi"
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name="O'quvchi"
    )
    teacher = models.ForeignKey(
        'teachers.Teacher',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name="O'qituvchi"
    )

    # Xabarnoma
    title = models.CharField(
        max_length=255,
        verbose_name="Sarlavha"
    )
    message = models.TextField(
        verbose_name="Xabar"
    )

    # Tur va kanal
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM,
        verbose_name="Turi"
    )
    channel = models.CharField(
        max_length=20,
        choices=Channel.choices,
        default=Channel.IN_APP,
        verbose_name="Kanal"
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL,
        verbose_name="Muhimlik"
    )

    # Status
    is_read = models.BooleanField(
        default=False,
        verbose_name="O'qilgan"
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="O'qilgan vaqt"
    )
    is_sent = models.BooleanField(
        default=False,
        verbose_name="Yuborilgan"
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Yuborilgan vaqt"
    )

    # Bog'langan ob'ekt (ixtiyoriy)
    related_model = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Bog'langan model"
    )
    related_id = models.UUIDField(
        blank=True,
        null=True,
        verbose_name="Bog'langan ID"
    )

    # Qo'shimcha data
    data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Qo'shimcha ma'lumot"
    )

    class Meta:
        verbose_name = "Xabarnoma"
        verbose_name_plural = "Xabarnomalar"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['student', 'is_read']),
        ]

    def __str__(self):
        return f"{self.title} - {self.get_notification_type_display()}"

    def mark_as_read(self):
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class NotificationTemplate(BaseModel):
    """
    Xabarnoma shablonlari
    """

    name = models.CharField(
        max_length=100,
        verbose_name="Nomi"
    )
    slug = models.SlugField(
        max_length=50,
        unique=True,
        verbose_name="Slug"
    )

    notification_type = models.CharField(
        max_length=20,
        choices=Notification.NotificationType.choices,
        verbose_name="Turi"
    )

    # Shablonlar
    title_template = models.CharField(
        max_length=255,
        verbose_name="Sarlavha shabloni"
    )
    message_template = models.TextField(
        verbose_name="Xabar shabloni",
        help_text="Masalan: Hurmatli {student_name}, sizning {month} oyi uchun to'lovingiz..."
    )

    # Qaysi kanallarda yuborish
    channels = models.JSONField(
        default=list,
        verbose_name="Kanallar",
        help_text="['telegram', 'sms', 'in_app']"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Faol"
    )

    class Meta:
        verbose_name = "Xabarnoma shabloni"
        verbose_name_plural = "Xabarnoma shablonlari"
        ordering = ['name']

    def __str__(self):
        return self.name

    def render(self, context):
        """Shablonni context bilan render qilish"""
        title = self.title_template.format(**context)
        message = self.message_template.format(**context)
        return title, message


class NotificationLog(BaseModel):
    """
    Yuborilgan xabarnomalar logi
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Kutilmoqda'
        SENT = 'sent', 'Yuborildi'
        DELIVERED = 'delivered', 'Yetkazildi'
        FAILED = 'failed', 'Xato'

    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name="Xabarnoma"
    )

    channel = models.CharField(
        max_length=20,
        choices=Notification.Channel.choices,
        verbose_name="Kanal"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Status"
    )

    # Tashqi tizim javobi
    external_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Tashqi ID"
    )
    response = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Javob"
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name="Xato xabari"
    )

    class Meta:
        verbose_name = "Xabarnoma logi"
        verbose_name_plural = "Xabarnoma loglari"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.notification.title} - {self.channel} - {self.status}"