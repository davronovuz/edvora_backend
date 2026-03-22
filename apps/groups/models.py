"""
Edvora - Groups Model
"""

from django.db import models
from core.models import BaseModel


class Group(BaseModel):
    """
    Guruh
    """

    class Status(models.TextChoices):
        FORMING = 'forming', 'Shakllanmoqda'
        ACTIVE = 'active', 'Faol'
        COMPLETED = 'completed', 'Tugallangan'
        CANCELLED = 'cancelled', 'Bekor qilingan'

    # Filial
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='groups',
        verbose_name="Filial"
    )

    # Asosiy
    name = models.CharField(
        max_length=100,
        verbose_name="Nomi"
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.PROTECT,
        related_name='groups',
        verbose_name="Kurs"
    )
    teacher = models.ForeignKey(
        'teachers.Teacher',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='groups',
        verbose_name="O'qituvchi"
    )

    # Vaqt
    start_date = models.DateField(
        verbose_name="Boshlanish sanasi"
    )
    end_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Tugash sanasi"
    )

    # Jadval
    days = models.JSONField(
        default=list,
        verbose_name="Kunlar",
        help_text="[0,2,4] = Dush, Chor, Juma"
    )
    start_time = models.TimeField(
        verbose_name="Boshlanish vaqti"
    )
    end_time = models.TimeField(
        verbose_name="Tugash vaqti"
    )
    room = models.ForeignKey(
        'rooms.Room',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='groups',
        verbose_name="Xona"
    )

    # Sig'im
    max_students = models.PositiveIntegerField(
        default=15,
        verbose_name="Max o'quvchilar"
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.FORMING,
        verbose_name="Status"
    )

    # Narx (kursdan farqli bo'lishi mumkin)
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Narxi (oylik)",
        help_text="Bo'sh qolsa kurs narxi ishlatiladi"
    )

    class Meta:
        verbose_name = "Guruh"
        verbose_name_plural = "Guruhlar"
        ordering = ['-start_date', 'name']

    def __str__(self):
        return f"{self.name} - {self.course.name}"

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    @property
    def students_count(self):
        return self.students.filter(is_active=True).count()

    @property
    def is_full(self):
        return self.students_count >= self.max_students

    @property
    def actual_price(self):
        """Guruh narxi yoki kurs narxi"""
        return self.price if self.price else self.course.price

    def get_days_display(self):
        """Kunlarni o'zbek tilida"""
        day_names = ['Du', 'Se', 'Cho', 'Pa', 'Ju', 'Sha', 'Ya']
        return ', '.join([day_names[d] for d in self.days if d < 7])


class GroupStudent(BaseModel):
    """
    Guruh - O'quvchi bog'lanishi
    """

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Faol'
        COMPLETED = 'completed', 'Tugallagan'
        DROPPED = 'dropped', 'Chiqib ketgan'
        TRANSFERRED = 'transferred', 'Ko\'chirilgan'
        FROZEN = 'frozen', 'Muzlatilgan'

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='students',
        verbose_name="Guruh"
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='groups',
        verbose_name="O'quvchi"
    )

    # Status
    is_active = models.BooleanField(
        default=True,
        verbose_name="Faol"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name="Status"
    )

    # Sanalar
    joined_date = models.DateField(
        auto_now_add=True,
        verbose_name="Qo'shilgan sana"
    )
    left_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Chiqib ketgan sana"
    )

    # Maxsus narx (chegirma bo'lsa)
    custom_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Maxsus narx"
    )
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="Chegirma %"
    )

    # Balans (guruh bo'yicha)
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Guruh balansi"
    )

    # Write-off (oylik yechib olish)
    last_write_off_date = models.DateField(
        blank=True, null=True,
        verbose_name="Oxirgi yechib olish sanasi"
    )
    next_write_off_date = models.DateField(
        blank=True, null=True,
        verbose_name="Keyingi yechib olish sanasi"
    )

    # Istisno narx (vaqtinchalik)
    exception_sum = models.DecimalField(
        max_digits=12, decimal_places=2,
        blank=True, null=True,
        verbose_name="Istisno summa"
    )
    exception_start_date = models.DateField(
        blank=True, null=True,
        verbose_name="Istisno boshi"
    )
    exception_end_date = models.DateField(
        blank=True, null=True,
        verbose_name="Istisno oxiri"
    )
    exception_reason = models.TextField(
        blank=True, null=True,
        verbose_name="Istisno sababi"
    )

    class Meta:
        verbose_name = "Guruh o'quvchisi"
        verbose_name_plural = "Guruh o'quvchilari"
        unique_together = ['group', 'student']
        ordering = ['student__first_name']

    def __str__(self):
        return f"{self.student.full_name} - {self.group.name}"

    @property
    def monthly_price(self):
        """Oylik to'lov miqdori"""
        # Istisno narx tekshirish
        if self.exception_sum is not None:
            from django.utils import timezone
            today = timezone.now().date()
            if self.exception_start_date:
                if self.exception_end_date:
                    if self.exception_start_date <= today <= self.exception_end_date:
                        return self.exception_sum
                else:
                    # End date yo'q = cheksiz istisno
                    if self.exception_start_date <= today:
                        return self.exception_sum

        if self.custom_price is not None:
            return self.custom_price

        base_price = self.group.actual_price
        if self.discount_percent > 0:
            discount = base_price * (self.discount_percent / 100)
            return base_price - discount

        return base_price

    @property
    def is_debtor(self):
        return self.balance < 0