"""
Edvora - Invoice Service

Orkestratsiya: strategy + discount engine = tayyor invoice.

Asosiy public API:
    InvoiceService.generate(group_student, year, month)
    InvoiceService.generate_for_group(group, year, month)
    InvoiceService.resolve_profile(group_student)
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from django.db import transaction

from apps.billing.models import BillingProfile, Invoice, InvoiceLine
from apps.billing.registry import get_strategy
from apps.billing.strategies.base import InvoiceContext

from .discount_engine import DiscountEngine


class InvoiceService:
    """
    Invoice generatsiya qilish uchun asosiy servis.
    """

    def __init__(self):
        self.discount_engine = DiscountEngine()

    def generate(
        self,
        group_student,
        year: int,
        month: int,
        promo_code: Optional[str] = None,
        force: bool = False,
    ) -> Optional[Invoice]:
        """
        Bitta group_student uchun oylik invoice yaratadi.

        Args:
            group_student: GroupStudent instance
            year, month: davr
            promo_code: ixtiyoriy promo kod
            force: True bo'lsa mavjud invoice'ni qayta hisoblaydi

        Returns: Invoice yoki None (allaqachon bor va force=False)
        """
        # Mavjudligini tekshirish
        existing = Invoice.objects.filter(
            group_student=group_student,
            period_year=year,
            period_month=month,
        ).exclude(status=Invoice.Status.CANCELLED).first()

        if existing and not force:
            return None

        if existing and force:
            # Eski invoice'ni bekor qilish
            existing.status = Invoice.Status.CANCELLED
            existing.save(update_fields=['status', 'updated_at'])

        # Profile aniqlash
        profile = self.resolve_profile(group_student)
        if not profile:
            return None

        # Strategy olish
        strategy = get_strategy(profile)

        # Context yaratish
        ctx = InvoiceContext(
            group_student=group_student,
            profile=profile,
            period_year=year,
            period_month=month,
        )

        with transaction.atomic():
            # Invoice yaratish (strategy)
            invoice = strategy.generate(ctx)
            if invoice is None:
                return None

            # Chegirmalarni qo'llash
            self.discount_engine.apply(invoice, promo_code=promo_code)

        return invoice

    def generate_for_group(
        self,
        group,
        year: int,
        month: int,
    ) -> list[Invoice]:
        """
        Butun guruh uchun oylik invoice'larni yaratadi.
        Faqat faol o'quvchilar uchun.

        Returns: yaratilgan Invoice'lar ro'yxati
        """
        from apps.groups.models import GroupStudent

        group_students = GroupStudent.objects.filter(
            group=group,
            is_active=True,
            status=GroupStudent.Status.ACTIVE,
        ).select_related('student', 'group', 'group__course')

        invoices = []
        for gs in group_students:
            inv = self.generate(gs, year, month)
            if inv is not None:
                invoices.append(inv)
        return invoices

    def generate_for_branch(
        self,
        branch,
        year: int,
        month: int,
    ) -> list[Invoice]:
        """
        Butun filial uchun oylik invoice'larni yaratadi.
        """
        from apps.groups.models import Group

        groups = Group.objects.filter(
            branch=branch,
            status='active',
        )

        invoices = []
        for group in groups:
            invoices.extend(self.generate_for_group(group, year, month))
        return invoices

    @staticmethod
    def resolve_profile(group_student) -> Optional[BillingProfile]:
        """
        GroupStudent uchun billing profile aniqlash.

        Iyerarxiya (yuqoridan pastga, birinchi topilgan qaytariladi):
            1. GroupStudent.billing_profile (individual override)
            2. Group.billing_profile (guruh darajasi)
            3. Course.billing_profile (kurs darajasi)
            4. Branch default (filial is_default=True)
            5. Global default (branch=None, is_default=True)
        """
        # 1. GroupStudent individual
        if group_student.billing_profile_id:
            return group_student.billing_profile

        group = group_student.group

        # 2. Group level
        if group.billing_profile_id:
            return group.billing_profile

        # 3. Course level
        if group.course_id and hasattr(group.course, 'billing_profile_id'):
            if group.course.billing_profile_id:
                return group.course.billing_profile

        # 4. Branch default
        if group.branch_id:
            profile = BillingProfile.objects.filter(
                branch_id=group.branch_id,
                is_default=True,
                is_active=True,
            ).first()
            if profile:
                return profile

        # 5. Global default
        profile = BillingProfile.objects.filter(
            branch__isnull=True,
            is_default=True,
            is_active=True,
        ).first()

        return profile
