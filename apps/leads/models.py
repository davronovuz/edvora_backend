"""
Edvora - Leads Model
Potentsial o'quvchilar (marketing va sales)
"""

from django.db import models
from core.models import BaseModel


class Lead(BaseModel):
    """
    Lead - Potentsial o'quvchi
    Qo'ng'iroq qilgan, so'ragan, ariza qoldirgan
    """

    class Status(models.TextChoices):
        NEW = 'new', 'Yangi'
        CONTACTED = 'contacted', "Bog'lanildi"
        INTERESTED = 'interested', 'Qiziqdi'
        TRIAL = 'trial', 'Sinov darsida'
        NEGOTIATION = 'negotiation', 'Kelishilmoqda'
        CONVERTED = 'converted', "O'quvchi bo'ldi"
        LOST = 'lost', 'Yo\'qotildi'

    class Source(models.TextChoices):
        WEBSITE = 'website', 'Veb-sayt'
        INSTAGRAM = 'instagram', 'Instagram'
        TELEGRAM = 'telegram', 'Telegram'
        FACEBOOK = 'facebook', 'Facebook'
        REFERRAL = 'referral', 'Tavsiya'
        WALK_IN = 'walk_in', "O'zi keldi"
        PHONE = 'phone', "Telefon qo'ng'iroq"
        OTHER = 'other', 'Boshqa'

    class Priority(models.TextChoices):
        LOW = 'low', 'Past'
        MEDIUM = 'medium', "O'rta"
        HIGH = 'high', 'Yuqori'

    # Shaxsiy ma'lumotlar
    first_name = models.CharField(
        max_length=100,
        verbose_name="Ism"
    )
    last_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
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

    # Qiziqishi
    interested_course = models.ForeignKey(
        'courses.Course',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leads',
        verbose_name="Qiziqgan kurs"
    )
    interested_subject = models.ForeignKey(
        'courses.Subject',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leads',
        verbose_name="Qiziqgan fan"
    )

    # Status va manba
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        verbose_name="Status"
    )
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.PHONE,
        verbose_name="Manba"
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        verbose_name="Muhimlik"
    )

    # Mas'ul
    assigned_to = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_leads',
        verbose_name="Mas'ul"
    )

    # Keyingi aloqa
    next_contact_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Keyingi aloqa vaqti"
    )

    # Konversiya (o'quvchi bo'lganda)
    converted_student = models.ForeignKey(
        'students.Student',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lead_source',
        verbose_name="O'quvchi"
    )
    converted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Konversiya vaqti"
    )

    # Yo'qotish sababi
    lost_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name="Yo'qotish sababi"
    )

    # Izohlar
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Izoh"
    )

    # UTM parametrlari (marketing analytics)
    utm_source = models.CharField(max_length=100, blank=True, null=True)
    utm_medium = models.CharField(max_length=100, blank=True, null=True)
    utm_campaign = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = "Lead"
        verbose_name_plural = "Leadlar"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} - {self.get_status_display()}"

    @property
    def full_name(self):
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name

    @property
    def is_converted(self):
        return self.status == self.Status.CONVERTED


class LeadActivity(BaseModel):
    """
    Lead faoliyati
    Qo'ng'iroqlar, xabarlar, uchrashuvlar tarixi
    """

    class ActivityType(models.TextChoices):
        CALL = 'call', "Qo'ng'iroq"
        SMS = 'sms', 'SMS'
        EMAIL = 'email', 'Email'
        MEETING = 'meeting', 'Uchrashuv'
        TRIAL = 'trial', 'Sinov dars'
        NOTE = 'note', 'Izoh'
        STATUS_CHANGE = 'status_change', 'Status o\'zgarishi'

    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name='activities',
        verbose_name="Lead"
    )

    activity_type = models.CharField(
        max_length=20,
        choices=ActivityType.choices,
        verbose_name="Turi"
    )

    description = models.TextField(
        verbose_name="Tavsif"
    )

    # Qo'ng'iroq uchun
    call_duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Qo'ng'iroq davomiyligi (sekund)"
    )

    # Kim qildi
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='lead_activities',
        verbose_name="Kim qildi"
    )

    class Meta:
        verbose_name = "Lead faoliyati"
        verbose_name_plural = "Lead faoliyatlari"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.lead.full_name} - {self.get_activity_type_display()}"