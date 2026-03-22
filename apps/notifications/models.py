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


class AutoSMS(BaseModel):
    """
    Avtomatik SMS sozlamalari
    Qaysi hodisalarda SMS yuborilishi
    """

    class Trigger(models.TextChoices):
        DEBT_REMINDER = 'debt_reminder', 'Qarz eslatmasi'
        PAYMENT_RECEIVED = 'payment_received', "To'lov qabul qilindi"
        BIRTHDAY = 'birthday', "Tug'ilgan kun tabrigi"
        LESSON_REMINDER = 'lesson_reminder', 'Dars eslatmasi'
        GROUP_JOINED = 'group_joined', 'Guruhga qo\'shildi'
        GROUP_LEFT = 'group_left', 'Guruhdan chiqdi'
        FREEZE_STARTED = 'freeze_started', 'Muzlatildi'
        WRITE_OFF = 'write_off', 'Oylik yechib olindi'

    name = models.CharField(
        max_length=100,
        verbose_name="Nomi"
    )
    trigger = models.CharField(
        max_length=30,
        choices=Trigger.choices,
        unique=True,
        verbose_name="Trigger"
    )
    message_template = models.TextField(
        verbose_name="Xabar shabloni",
        help_text="Masalan: Hurmatli {student_name}, sizning {amount} so'm qarzingiz bor."
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Faol"
    )

    class Meta:
        verbose_name = "Avtomatik SMS"
        verbose_name_plural = "Avtomatik SMSlar"
        ordering = ['trigger']

    def __str__(self):
        return f"{self.name} ({self.get_trigger_display()})"

    def render_message(self, context):
        """Shablonni context bilan render qilish"""
        try:
            return self.message_template.format(**context)
        except KeyError:
            return self.message_template


class Reminder(BaseModel):
    """
    Eslatma - xodimlar uchun shaxsiy eslatmalar
    """

    class Priority(models.TextChoices):
        LOW = 'low', 'Past'
        NORMAL = 'normal', 'Normal'
        HIGH = 'high', 'Yuqori'

    # Kim yaratdi
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='reminders',
        verbose_name="Kim yaratdi"
    )

    title = models.CharField(
        max_length=255,
        verbose_name="Sarlavha"
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Tavsif"
    )

    # Vaqt
    remind_at = models.DateTimeField(
        verbose_name="Eslatish vaqti"
    )

    # Bog'langan ob'ekt (ixtiyoriy)
    related_student = models.ForeignKey(
        'students.Student',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reminders',
        verbose_name="O'quvchi"
    )
    related_group = models.ForeignKey(
        'groups.Group',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reminders',
        verbose_name="Guruh"
    )

    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.NORMAL,
        verbose_name="Muhimlik"
    )

    is_completed = models.BooleanField(
        default=False,
        verbose_name="Bajarildi"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Bajarilgan vaqt"
    )

    is_notified = models.BooleanField(
        default=False,
        verbose_name="Eslatildi"
    )

    class Meta:
        verbose_name = "Eslatma"
        verbose_name_plural = "Eslatmalar"
        ordering = ['remind_at']

    def __str__(self):
        return f"{self.title} - {self.remind_at.strftime('%Y-%m-%d %H:%M')}"

    def complete(self):
        from django.utils import timezone
        self.is_completed = True
        self.completed_at = timezone.now()
        self.save(update_fields=['is_completed', 'completed_at'])