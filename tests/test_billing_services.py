"""
Edvora - Billing Services Tests (Stage 4)

3 ta servis uchun testlar:
    - DiscountEngine: auto-apply, stackable, first_month, loyalty
    - PaymentAllocator: FIFO, partial, overpay
    - InvoiceService: generate, profile resolution, duplicate protection
"""

from datetime import date, time, timedelta
from decimal import Decimal

import pytest

from apps.billing.models import (
    BillingProfile,
    Discount,
    Invoice,
    InvoiceLine,
    StudentLeave,
)
from apps.billing.services.discount_engine import DiscountEngine
from apps.billing.services.invoice_service import InvoiceService
from apps.billing.services.payment_allocator import AllocationResult, PaymentAllocator
from apps.billing.strategies.base import InvoiceContext
from apps.billing.strategies.monthly_flat import MonthlyFlatStrategy


pytestmark = pytest.mark.django_db


# =============================================================================
# Fixtures
# =============================================================================

def make_profile(**kwargs):
    defaults = dict(
        name="Default Flat",
        mode=BillingProfile.Mode.MONTHLY_FLAT,
        is_default=True,
    )
    defaults.update(kwargs)
    return BillingProfile.objects.create(**defaults)


@pytest.fixture
def profile():
    return make_profile()


@pytest.fixture
def april_group(create_course, create_teacher):
    from apps.groups.models import Group
    return Group.objects.create(
        name="Service Test Group",
        course=create_course(price=Decimal("500000")),
        teacher=create_teacher(),
        start_date=date(2026, 3, 1),
        days=[0, 2, 4],
        start_time=time(9, 0),
        end_time=time(11, 0),
        max_students=15,
        status='active',
        price=Decimal("500000"),
    )


@pytest.fixture
def gs(april_group, create_student):
    from apps.groups.models import GroupStudent
    return GroupStudent.objects.create(
        group=april_group,
        student=create_student(),
        joined_date=date(2026, 4, 1),
        is_active=True,
        status='active',
    )


def make_invoice(profile, gs, month=4, year=2026, **kwargs):
    defaults = dict(
        student=gs.student,
        group=gs.group,
        group_student=gs,
        billing_profile=profile,
        period_month=month,
        period_year=year,
        period_start=date(year, month, 1),
        period_end=date(year, month, 28),
        base_amount=Decimal("500000"),
        due_date=date(year, month, 10),
        billable_days=30,
        total_period_days=30,
        status=Invoice.Status.UNPAID,
    )
    defaults.update(kwargs)
    return Invoice.objects.create(**defaults)


def make_payment(student, amount, **kwargs):
    """Payment yaratish — save() dagi balance bug ni chetlab o'tish."""
    from apps.payments.models import Payment
    from core.utils.helpers import generate_invoice_number
    import uuid
    defaults = dict(
        student=student,
        amount=Decimal(amount),
        payment_method='cash',
        payment_type='tuition',
        status='completed',
        receipt_number=generate_invoice_number('TPAY'),
    )
    defaults.update(kwargs)
    # UUID model tufayli pk=None bo'lmaydi, shuning uchun
    # Payment.save() ichidagi is_new logikasi buziladi.
    # super().save() ni to'g'ridan-to'g'ri chaqiramiz.
    obj = Payment(**defaults)
    from django.db import models as _m
    _m.Model.save(obj)
    return obj


# =============================================================================
# DiscountEngine
# =============================================================================

class TestDiscountEngine:
    def test_apply_student_discount(self, profile, gs):
        """Student'ga biriktirilgan foiz chegirma qo'llanadi."""
        inv = make_invoice(profile, gs)
        InvoiceLine.objects.create(
            invoice=inv, kind=InvoiceLine.Kind.BASE,
            description="Base", amount=Decimal("500000"),
        )

        Discount.objects.create(
            kind=Discount.Kind.STUDENT_PERCENT,
            name="Aliga 20%",
            value_type=Discount.ValueType.PERCENT,
            value=Decimal("20"),
            start_date=date(2026, 1, 1),
            student=gs.student,
        )

        engine = DiscountEngine()
        lines = engine.apply(inv)

        assert len(lines) == 1
        assert lines[0].amount == Decimal("100000.00")
        inv.refresh_from_db()
        assert inv.discount_amount == Decimal("100000.00")
        assert inv.total_amount == Decimal("400000.00")

    def test_group_discount(self, profile, gs):
        """Guruhga biriktirilgan chegirma."""
        inv = make_invoice(profile, gs)

        Discount.objects.create(
            kind=Discount.Kind.GROUP_PROMO,
            name="Guruh aksiya 10%",
            value_type=Discount.ValueType.PERCENT,
            value=Decimal("10"),
            start_date=date(2026, 1, 1),
            group=gs.group,
        )

        engine = DiscountEngine()
        lines = engine.apply(inv)
        assert len(lines) == 1
        assert lines[0].amount == Decimal("50000.00")

    def test_stackable_discounts(self, profile, gs):
        """Stackable bo'lganlar hammasi qo'llanadi."""
        inv = make_invoice(profile, gs)

        Discount.objects.create(
            kind=Discount.Kind.STUDENT_PERCENT,
            name="Sibling 10%",
            value_type=Discount.ValueType.PERCENT,
            value=Decimal("10"),
            start_date=date(2026, 1, 1),
            student=gs.student,
            stackable=True,
        )
        Discount.objects.create(
            kind=Discount.Kind.STUDENT_FIXED,
            name="Bonus 20,000",
            value_type=Discount.ValueType.FIXED,
            value=Decimal("20000"),
            start_date=date(2026, 1, 1),
            student=gs.student,
            stackable=True,
        )

        engine = DiscountEngine()
        lines = engine.apply(inv)
        assert len(lines) == 2
        inv.refresh_from_db()
        # 10% of 500,000 = 50,000 + 20,000 = 70,000
        assert inv.discount_amount == Decimal("70000.00")

    def test_non_stackable_priority(self, profile, gs):
        """Non-stackable bo'lsa, eng yuqori priority'li tanlaydi."""
        inv = make_invoice(profile, gs)

        Discount.objects.create(
            kind=Discount.Kind.STUDENT_PERCENT,
            name="Low priority 5%",
            value_type=Discount.ValueType.PERCENT,
            value=Decimal("5"),
            start_date=date(2026, 1, 1),
            student=gs.student,
            stackable=False,
            priority=1,
        )
        Discount.objects.create(
            kind=Discount.Kind.SCHOLARSHIP,
            name="Stipendiya 50%",
            value_type=Discount.ValueType.PERCENT,
            value=Decimal("50"),
            start_date=date(2026, 1, 1),
            student=gs.student,
            stackable=False,
            priority=10,
        )

        engine = DiscountEngine()
        lines = engine.apply(inv)
        assert len(lines) == 1
        assert lines[0].amount == Decimal("250000.00")

    def test_expired_discount_ignored(self, profile, gs):
        """Muddati o'tgan chegirma qo'llanmaydi."""
        inv = make_invoice(profile, gs)

        Discount.objects.create(
            kind=Discount.Kind.STUDENT_PERCENT,
            name="Eski 20%",
            value_type=Discount.ValueType.PERCENT,
            value=Decimal("20"),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),  # o'tgan
            student=gs.student,
        )

        engine = DiscountEngine()
        lines = engine.apply(inv)
        assert len(lines) == 0

    def test_no_discount(self, profile, gs):
        """Hech qanday chegirma yo'q — bo'sh ro'yxat."""
        inv = make_invoice(profile, gs)
        engine = DiscountEngine()
        lines = engine.apply(inv)
        assert len(lines) == 0
        inv.refresh_from_db()
        assert inv.discount_amount == Decimal("0")

    def test_promo_code(self, profile, gs):
        """Promo kod orqali chegirma qo'llash."""
        inv = make_invoice(profile, gs)

        Discount.objects.create(
            kind=Discount.Kind.PROMO_CODE,
            name="Yangi yil",
            code="NY2026",
            value_type=Discount.ValueType.PERCENT,
            value=Decimal("15"),
            start_date=date(2026, 1, 1),
            max_uses=100,
            uses_count=0,
        )

        engine = DiscountEngine()
        lines = engine.apply(inv, promo_code="NY2026")
        assert len(lines) == 1
        assert lines[0].amount == Decimal("75000.00")
        # uses_count oshganini tekshirish
        d = Discount.objects.get(code="NY2026")
        assert d.uses_count == 1

    def test_first_month_only(self, profile, gs):
        """applies_to_first_month_only: birinchi oyda ishlaydi, ikkinchida yo'q."""
        Discount.objects.create(
            kind=Discount.Kind.FIRST_MONTH,
            name="Birinchi oy 30%",
            value_type=Discount.ValueType.PERCENT,
            value=Decimal("30"),
            start_date=date(2026, 1, 1),
            student=gs.student,
            applies_to_first_month_only=True,
        )

        engine = DiscountEngine()

        # Birinchi invoice
        inv1 = make_invoice(profile, gs, month=4)
        lines = engine.apply(inv1)
        assert len(lines) == 1

        # Ikkinchi invoice — chegirma yo'q
        inv2 = make_invoice(profile, gs, month=5)
        lines2 = engine.apply(inv2)
        assert len(lines2) == 0


# =============================================================================
# PaymentAllocator
# =============================================================================

class TestPaymentAllocator:
    def test_full_payment(self, profile, gs):
        """To'liq to'lov = invoice PAID."""
        inv = make_invoice(profile, gs)
        payment = make_payment(gs.student, "500000")

        allocator = PaymentAllocator()
        result = allocator.allocate(payment)

        assert len(result.allocated) == 1
        assert result.allocated[0][1] == Decimal("500000")
        assert result.remaining == Decimal("0")
        assert len(result.paid_invoices) == 1

        inv.refresh_from_db()
        assert inv.status == Invoice.Status.PAID

    def test_partial_payment(self, profile, gs):
        """Qisman to'lov = PARTIAL."""
        inv = make_invoice(profile, gs)
        payment = make_payment(gs.student, "200000")

        allocator = PaymentAllocator()
        result = allocator.allocate(payment)

        assert result.allocated[0][1] == Decimal("200000")
        assert result.remaining == Decimal("0")

        inv.refresh_from_db()
        assert inv.status == Invoice.Status.PARTIAL
        assert inv.paid_amount == Decimal("200000")

    def test_fifo_two_invoices(self, profile, gs, create_student):
        """FIFO: eski invoice avval to'lanadi."""
        from apps.groups.models import GroupStudent
        # 2 ta invoice yaratish uchun farqli group_student kerak (constraint)
        gs2 = GroupStudent.objects.create(
            group=gs.group,
            student=create_student(first_name="Vali", phone="+998901112299"),
            joined_date=date(2026, 4, 1),
            is_active=True,
            status='active',
        )

        inv_march = make_invoice(profile, gs2, month=3)
        inv_april = make_invoice(profile, gs2, month=4)

        # 700,000 to'lov (birinchi to'liq + ikkinchisiga 200,000)
        payment = make_payment(gs2.student, "700000")

        allocator = PaymentAllocator()
        result = allocator.allocate(payment)

        assert len(result.allocated) == 2
        assert result.paid_invoices[0].period_month == 3
        assert result.remaining == Decimal("0")

        inv_march.refresh_from_db()
        assert inv_march.status == Invoice.Status.PAID

        inv_april.refresh_from_db()
        assert inv_april.status == Invoice.Status.PARTIAL
        assert inv_april.paid_amount == Decimal("200000")

    def test_overpayment_remaining(self, profile, gs):
        """Ortiqcha to'lov — remaining qaytadi."""
        inv = make_invoice(profile, gs)
        payment = make_payment(gs.student, "600000")

        allocator = PaymentAllocator()
        result = allocator.allocate(payment)

        assert result.remaining == Decimal("100000")

        inv.refresh_from_db()
        assert inv.status == Invoice.Status.PAID

    def test_no_invoices(self, profile, gs):
        """Invoice bo'lmasa — hamma remaining qaytadi."""
        payment = make_payment(gs.student, "500000")

        allocator = PaymentAllocator()
        result = allocator.allocate(payment)

        assert result.remaining == Decimal("500000")
        assert len(result.allocated) == 0

    def test_allocate_to_specific_invoice(self, profile, gs):
        """Konkret invoice'ga taqsimlash."""
        inv = make_invoice(profile, gs)
        payment = make_payment(gs.student, "300000")

        allocator = PaymentAllocator()
        allocated = allocator.allocate_to_invoice(payment, inv)

        assert allocated == Decimal("300000")
        inv.refresh_from_db()
        assert inv.paid_amount == Decimal("300000")
        assert inv.status == Invoice.Status.PARTIAL


# =============================================================================
# InvoiceService
# =============================================================================

class TestInvoiceService:
    def test_generate_basic(self, profile, gs):
        """Oddiy invoice generatsiya."""
        svc = InvoiceService()
        inv = svc.generate(gs, 2026, 4)

        assert inv is not None
        assert inv.base_amount == Decimal("500000.00")
        assert inv.status == Invoice.Status.UNPAID

    def test_duplicate_protection(self, profile, gs):
        """Ikkinchi marta chaqirilsa None qaytadi."""
        svc = InvoiceService()
        inv1 = svc.generate(gs, 2026, 4)
        inv2 = svc.generate(gs, 2026, 4)

        assert inv1 is not None
        assert inv2 is None

    def test_force_regenerate(self, profile, gs):
        """force=True bo'lsa eski bekor qilinib yangi yaratiladi."""
        svc = InvoiceService()
        inv1 = svc.generate(gs, 2026, 4)
        inv2 = svc.generate(gs, 2026, 4, force=True)

        assert inv2 is not None
        assert inv2.pk != inv1.pk

        inv1.refresh_from_db()
        assert inv1.status == Invoice.Status.CANCELLED

    def test_generate_with_discount(self, profile, gs):
        """Discount avtomatik qo'llanadi."""
        Discount.objects.create(
            kind=Discount.Kind.STUDENT_PERCENT,
            name="20%",
            value_type=Discount.ValueType.PERCENT,
            value=Decimal("20"),
            start_date=date(2026, 1, 1),
            student=gs.student,
        )

        svc = InvoiceService()
        inv = svc.generate(gs, 2026, 4)

        assert inv.discount_amount == Decimal("100000.00")
        assert inv.total_amount == Decimal("400000.00")

    def test_resolve_profile_global_default(self, profile, gs):
        """Global default profile topadi."""
        resolved = InvoiceService.resolve_profile(gs)
        assert resolved is not None
        assert resolved.pk == profile.pk

    def test_resolve_profile_branch(self, gs):
        """Branch default profile topadi."""
        from apps.branches.models import Branch
        branch = Branch.objects.create(name="Filial-1", address="X")
        gs.group.branch = branch
        gs.group.save()

        branch_profile = BillingProfile.objects.create(
            name="Branch Flat",
            mode=BillingProfile.Mode.MONTHLY_FLAT,
            branch=branch,
            is_default=True,
        )
        # Global ham bor
        BillingProfile.objects.create(
            name="Global",
            mode=BillingProfile.Mode.MONTHLY_FLAT,
            is_default=True,
        )

        resolved = InvoiceService.resolve_profile(gs)
        assert resolved.pk == branch_profile.pk

    def test_no_profile_returns_none(self, gs):
        """Profile topilmasa None."""
        resolved = InvoiceService.resolve_profile(gs)
        assert resolved is None

    def test_generate_for_group(self, profile, april_group, create_student):
        """Butun guruh uchun invoice generatsiya."""
        from apps.groups.models import GroupStudent
        # 3 ta o'quvchi
        for i in range(3):
            GroupStudent.objects.create(
                group=april_group,
                student=create_student(
                    first_name=f"Student{i}",
                    phone=f"+99890{i}111111",
                ),
                joined_date=date(2026, 4, 1),
                is_active=True,
                status='active',
            )

        svc = InvoiceService()
        invoices = svc.generate_for_group(april_group, 2026, 4)

        assert len(invoices) == 3
        assert all(inv.base_amount == Decimal("500000.00") for inv in invoices)
