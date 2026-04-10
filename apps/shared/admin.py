"""
MarkazEdu - Shared Admin
Admin paneldan markaz yaratganda avtomatik:
  1. Tenant (schema) yaratiladi
  2. Domain (slug.markazedu.uz) yaratiladi
  3. Owner user yaratiladi
"""

import logging
from django import forms
from django.contrib import admin, messages
from django_tenants.admin import TenantAdminMixin
from django_tenants.utils import schema_context
from .models import Tenant, Domain, Plan, BillingInvoice, BillingPayment

logger = logging.getLogger(__name__)


class TenantAdminForm(forms.ModelForm):
    """Tenant form — owner paroli bilan"""
    owner_password = forms.CharField(
        label="Egasi paroli",
        widget=forms.PasswordInput(attrs={'placeholder': 'Parol kiriting'}),
        required=False,
        help_text="Yangi markaz yaratganda parol kiriting. Tahrirlashda bo'sh qoldirsangiz o'zgarmaydi."
    )

    class Meta:
        model = Tenant
        fields = '__all__'


@admin.register(Tenant)
class TenantAdmin(TenantAdminMixin, admin.ModelAdmin):
    form = TenantAdminForm
    list_display = ['name', 'slug', 'owner_name', 'owner_email', 'status', 'plan', 'created_at']
    list_filter = ['status', 'plan', 'created_at']
    search_fields = ['name', 'slug', 'owner_name', 'owner_email']
    readonly_fields = ['schema_name', 'created_at', 'updated_at']

    fieldsets = (
        ('Asosiy', {
            'fields': ('name', 'slug', 'schema_name'),
            'description': "Slug = subdomen nomi. Masalan: 'ziyo' → ziyo.markazedu.uz"
        }),
        ('Egasi', {
            'fields': ('owner_name', 'owner_email', 'owner_phone', 'owner_password'),
            'description': "Markaz egasi — login qilish uchun email va parol"
        }),
        ('Branding', {
            'fields': ('logo', 'login_background', 'primary_color'),
            'description': "Login sahifasida ko'rinadigan logo, fon rasmi va asosiy rang",
            'classes': ('collapse',)
        }),
        ('Manzil', {
            'fields': ('address', 'city'),
            'classes': ('collapse',)
        }),
        ('Obuna', {
            'fields': ('plan', 'status', 'trial_ends_at', 'subscription_ends_at')
        }),
        ('Sozlamalar', {
            'fields': ('timezone', 'language', 'currency', 'settings'),
            'classes': ('collapse',)
        }),
        ('Vaqt', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        """
        Tenant saqlanganda:
        - Yangi bo'lsa: schema_name = slug, domain + owner user yaratiladi
        - Tahrirlash bo'lsa: owner paroli yangilanadi (agar kiritilgan bo'lsa)
        """
        is_new = not change
        owner_password = form.cleaned_data.get('owner_password', '')

        if is_new:
            # schema_name = slug
            obj.schema_name = obj.slug

            if not owner_password:
                messages.error(request, "Yangi markaz uchun egasi parolini kiriting!")
                return

        # Tenant saqlash (schema yaratiladi)
        super().save_model(request, obj, form, change)

        if is_new:
            # Domain yaratish
            domain_name = f"{obj.slug}.markazedu.uz"
            try:
                if not Domain.objects.filter(domain=domain_name).exists():
                    Domain.objects.create(
                        domain=domain_name,
                        tenant=obj,
                        is_primary=True,
                    )
                    messages.success(request, f"Domain yaratildi: {domain_name}")
            except Exception as e:
                logger.error(f"Domain yaratishda xato: {e}")
                messages.warning(request, f"Domain yaratishda xato: {e}")

            # Owner user yaratish
            try:
                with schema_context(obj.schema_name):
                    from django.contrib.auth import get_user_model
                    User = get_user_model()

                    if not User.objects.filter(email=obj.owner_email).exists():
                        User.objects.create_user(
                            email=obj.owner_email,
                            password=owner_password,
                            full_name=obj.owner_name,
                            phone=obj.owner_phone or '',
                            role='owner',
                            is_staff=True,
                            is_superuser=True,
                        )
                        messages.success(
                            request,
                            f"Owner yaratildi: {obj.owner_email} | "
                            f"Login: https://{domain_name}/login"
                        )
                    else:
                        messages.info(request, f"User allaqachon mavjud: {obj.owner_email}")
            except Exception as e:
                logger.error(f"Owner yaratishda xato: {e}")
                messages.warning(request, f"Owner yaratishda xato: {e}")

        elif owner_password:
            # Tahrirlashda parol yangilash
            try:
                with schema_context(obj.schema_name):
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    user = User.objects.filter(email=obj.owner_email).first()
                    if user:
                        user.set_password(owner_password)
                        user.save()
                        messages.success(request, f"Parol yangilandi: {obj.owner_email}")
            except Exception as e:
                logger.error(f"Parol yangilashda xato: {e}")


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ['domain', 'tenant', 'is_primary']
    list_filter = ['is_primary']
    search_fields = ['domain', 'tenant__name']


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'plan_type', 'price_monthly', 'max_students', 'is_active', 'is_popular',
                    'sort_order']
    list_filter = ['plan_type', 'is_active', 'is_popular']
    search_fields = ['name', 'slug']
    list_editable = ['is_active', 'is_popular', 'sort_order']

    fieldsets = (
        ('Asosiy', {
            'fields': ('name', 'slug', 'plan_type', 'description')
        }),
        ('Narxlar', {
            'fields': ('price_monthly', 'price_yearly')
        }),
        ('Limitlar', {
            'fields': ('max_students', 'max_groups', 'max_teachers', 'max_admins')
        }),
        ('Features', {
            'fields': ('features',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'is_popular', 'sort_order')
        }),
    )


@admin.register(BillingInvoice)
class BillingInvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'tenant', 'total', 'status', 'due_date', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['invoice_number', 'tenant__name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(BillingPayment)
class BillingPaymentAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'amount', 'payment_method', 'status', 'created_at']
    list_filter = ['payment_method', 'status', 'created_at']
    search_fields = ['invoice__invoice_number', 'external_id']
    readonly_fields = ['created_at', 'updated_at']
