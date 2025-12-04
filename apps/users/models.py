"""
Edvora - Custom User Model
Tenant ichidagi foydalanuvchilar (Owner, Admin, Teacher, Accountant, Registrar)
"""

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from core.models import BaseModel


class UserManager(BaseUserManager):
    """
    Custom User Manager
    """

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email majburiy")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.OWNER)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser is_staff=True bo'lishi kerak")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser is_superuser=True bo'lishi kerak")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    """
    Custom User Model

    Rollar:
    - owner: Markaz egasi (hamma narsa)
    - admin: Administrator (ko'p narsa, moliya cheklangan)
    - teacher: O'qituvchi (faqat o'z guruhlari)
    - accountant: Buxgalter (faqat moliya)
    - registrar: Qabul (faqat yangi o'quvchi)
    """

    class Role(models.TextChoices):
        OWNER = 'owner', 'Markaz egasi'
        ADMIN = 'admin', 'Administrator'
        TEACHER = 'teacher', "O'qituvchi"
        ACCOUNTANT = 'accountant', 'Buxgalter'
        REGISTRAR = 'registrar', 'Qabul'

    # Auth fields
    email = models.EmailField(
        unique=True,
        verbose_name="Email"
    )
    phone = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Telefon"
    )

    # Profile
    first_name = models.CharField(
        max_length=100,
        verbose_name="Ism"
    )
    last_name = models.CharField(
        max_length=100,
        verbose_name="Familiya"
    )
    avatar = models.ImageField(
        upload_to='users/avatars/',
        null=True,
        blank=True,
        verbose_name="Rasm"
    )

    # Role & Permissions
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.ADMIN,
        verbose_name="Rol"
    )
    custom_permissions = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Maxsus ruxsatlar"
    )

    # Status
    is_active = models.BooleanField(
        default=True,
        verbose_name="Faol"
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name="Staff"
    )

    # Dates
    last_login_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Oxirgi IP"
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def short_name(self):
        return self.first_name

    # =========================================================================
    # PERMISSION METHODS
    # =========================================================================

    def has_role(self, role):
        """Foydalanuvchi bu rolga egami?"""
        return self.role == role

    def is_owner(self):
        return self.role == self.Role.OWNER

    def is_admin(self):
        return self.role == self.Role.ADMIN

    def is_teacher(self):
        return self.role == self.Role.TEACHER

    def is_accountant(self):
        return self.role == self.Role.ACCOUNTANT

    def is_registrar(self):
        return self.role == self.Role.REGISTRAR

    def has_permission(self, permission):
        """
        Maxsus permission tekshirish

        Usage:
            user.has_permission('students.create')
            user.has_permission('payments.refund')
        """
        # Owner has all permissions
        if self.is_owner():
            return True

        # Check custom permissions
        if permission in self.custom_permissions:
            return self.custom_permissions[permission]

        # Check role-based default permissions
        return self._get_default_permission(permission)

    def _get_default_permission(self, permission):
        """Role bo'yicha default permission"""
        role_permissions = {
            self.Role.ADMIN: {
                'students.view': True,
                'students.create': True,
                'students.update': True,
                'students.delete': False,
                'teachers.view': True,
                'teachers.create': False,
                'groups.view': True,
                'groups.create': True,
                'groups.update': True,
                'attendance.view': True,
                'attendance.mark': True,
                'payments.view': True,
                'payments.create': True,
                'payments.refund': False,
                'finance.view': False,
                'salaries.view': False,
                'settings.view': False,
            },
            self.Role.TEACHER: {
                'students.view': True,
                'students.create': False,
                'groups.view': True,
                'attendance.view': True,
                'attendance.mark': True,
                'payments.view': False,
                'finance.view': False,
                'salaries.view_own': True,
            },
            self.Role.ACCOUNTANT: {
                'students.view': True,
                'teachers.view': True,
                'payments.view': True,
                'payments.create': True,
                'payments.refund': False,
                'finance.view': True,
                'salaries.view': True,
                'salaries.calculate': True,
            },
            self.Role.REGISTRAR: {
                'students.view': True,
                'students.create': True,
                'groups.view': True,
                'payments.view': True,
                'payments.create': True,
                'leads.view': True,
                'leads.create': True,
                'leads.update': True,
            },
        }

        user_perms = role_permissions.get(self.role, {})
        return user_perms.get(permission, False)

    def get_all_permissions_list(self):
        """Barcha permissions ro'yxati"""
        all_permissions = [
            'students.view', 'students.create', 'students.update', 'students.delete',
            'teachers.view', 'teachers.create', 'teachers.update', 'teachers.delete',
            'courses.view', 'courses.create', 'courses.update', 'courses.delete',
            'groups.view', 'groups.create', 'groups.update', 'groups.delete',
            'attendance.view', 'attendance.mark',
            'payments.view', 'payments.create', 'payments.refund',
            'finance.view', 'finance.export',
            'salaries.view', 'salaries.calculate', 'salaries.approve', 'salaries.pay',
            'leads.view', 'leads.create', 'leads.update', 'leads.convert',
            'settings.view', 'settings.update',
            'users.view', 'users.create', 'users.update', 'users.delete',
        ]
        return all_permissions

    def get_permissions_dict(self):
        """Foydalanuvchining barcha permissions'ini dict ko'rinishida"""
        result = {}
        for perm in self.get_all_permissions_list():
            result[perm] = self.has_permission(perm)
        return result