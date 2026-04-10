"""
Edvora - Billing Models Tests (Stage 1)

apps/billing/models.py uchun unit testlar:
    - BillingProfile yaratish, validatsiya
    - StudentLeave yaratish, validatsiya, days_count
    - Discount yaratish, validatsiya, calculate(), is_usable
    - Invoice yaratish, raqam generatsiya, total hisoblash, recompute_status
    - InvoiceLine yaratish
    - Constraint: bitta o'quvchi-davr uchun bitta invoice
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone

from apps.billing.models import (
    BillingProfile,
    Discount,
    Invoice,
    InvoiceLine,
    StudentLeave,
)


pytestmark = pytest.mark.django_db


# =============================================================================
# Helpers
# =============================================================================

def make_profile(**kwargs):
    defaults = dict(
        name="Test Oylik Flat",
        mode=BillingProfile.Mode.MONTHLY_FLAT,
    )
    defaults.update(kwargs)
    return BillingProfile.objects.create(**defaults)


@pytest.fixture
def billing_profile():
    return make_profile()


@pytest.fixture
def group_student(create_student, create_group):
    from apps.groups.models import GroupStudent
    student = create_student()
    group = create_group()
    return GroupStudent.objects.create(group=group, student=student)


# =============================================================================
# BillingProfile
# =============================================================================

class TestBillingProfile:
    def test_create_minimal(self):
        profile = BillingProfile.objects.create(
            name="Oddiy oylik",
            mode=BillingProfile.Mode.MONTHLY_FLAT,
        )
        assert profile.pk is not None
        assert profile.is_active is True
        assert profile.billing_day == 1
        assert profile.due_days == 10
        assert profile.leave_policy == BillingProfile.LeavePolicy.PRORATE_DAYS
        assert profile.allow_partial_payment is True

    def test_str(self):
        profile = BillingProfile.objects.create(
            name="Test", mode=BillingProfile.Mode.PER_LESSON
        )
        s = str(profile)
        assert "Test" in s
        assert "Global" in s

    def test_clean_invalid_billing_day(self):
        profile = BillingProfile(
            name="Bad day",
            mode=BillingProfile.Mode.MONTHLY_FLAT,
            billing_day=0,
        )
        with pytest.raises(ValidationError):
            profile.clean()

        profile.billing_day = 30
        with pytest.raises(ValidationError):
            profile.clean()

    def test_clean_late_fee_zero(self):
        profile = BillingProfile(
            name="Bad fee",
            mode=BillingProfile.Mode.MONTHLY_FLAT,
            late_fee_enabled=True,
            late_fee_value=Decimal("0"),
        )
        with pytest.raises(ValidationError):
            profile.clean()

    def test_unique_per_branch(self):
        from apps.branches.models import Branch
        branch = Branch.objects.create(name="Filial-1", address="X")
        BillingProfile.objects.create(
            branch=branch,
            name="Same name",
            mode=BillingProfile.Mode.MONTHLY_FLAT,
        )
        with pytest.raises(IntegrityError):
            BillingProfile.objects.create(
                branch=branch,
                name="Same name",
                mode=BillingProfile.Mode.PER_LESSON,
            )


# =============================================================================
# StudentLeave
# =============================================================================

class TestStudentLeave:
    def test_create(self, group_student):
        leave = StudentLeave.objects.create(
            group_student=group_student,
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 10),
            reason="Sayohat",
        )
        assert leave.pk is not None
        assert leave.status == StudentLeave.Status.PENDING

    def test_days_count(self, group_student):
        leave = StudentLeave(
            group_student=group_student,
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 10),
            reason="x",
        )
        assert leave.days_count == 10

    def test_days_count_single_day(self, group_student):
        leave = StudentLeave(
            group_student=group_student,
            start_date=date(2026, 4, 5),
            end_date=date(2026, 4, 5),
            reason="x",
        )
        assert leave.days_count == 1

    def test_clean_invalid_dates(self, group_student):
        leave = StudentLeave(
            group_student=group_student,
            start_date=date(2026, 4, 10),
            end_date=date(2026, 4, 5),
            reason="x",
        )
        with pytest.raises(ValidationError):
            leave.clean()


# =============================================================================
# Discount
# =============================================================================

class TestDiscount:
    def test_create_percent(self):
        d = Discount.objects.create(
            kind=Discount.Kind.STUDENT_PERCENT,
            name="Aliga 20%",
            value_type=Discount.ValueType.PERCENT,
            value=Decimal("20"),
            start_date=date(2026, 1, 1),
        )
        assert d.pk is not None
        assert d.is_usable is True

    def test_calculate_percent(self):
        d = Discount(
            kind=Discount.Kind.STUDENT_PERCENT,
            name="20%",
            value_type=Discount.ValueType.PERCENT,
            value=Decimal("20"),
            start_date=date(2026, 1, 1),
        )
        assert d.calculate(Decimal("500000")) == Decimal("100000.00")

    def test_calculate_fixed(self):
        d = Discount(
            kind=Discount.Kind.STUDENT_FIXED,
            name="Fix 50,000",
            value_type=Discount.ValueType.FIXED,
            value=Decimal("50000"),
            start_date=date(2026, 1, 1),
        )
        assert d.calculate(Decimal("500000")) == Decimal("50000.00")

    def test_calculate_fixed_capped_at_base(self):
        d = Discount(
            kind=Discount.Kind.STUDENT_FIXED,
            name="Big fix",
            value_type=Discount.ValueType.FIXED,
            value=Decimal("999999"),
            start_date=date(2026, 1, 1),
        )
        assert d.calculate(Decimal("100000")) == Decimal("100000.00")

    def test_calculate_percent_with_max_amount(self):
        d = Discount(
            kind=Discount.Kind.STUDENT_PERCENT,
            name="50% max 30k",
            value_type=Discount.ValueType.PERCENT,
            value=Decimal("50"),
            max_amount=Decimal("30000"),
            start_date=date(2026, 1, 1),
        )
        # 50% of 100,000 = 50,000 — but capped at 30,000
        assert d.calculate(Decimal("100000")) == Decimal("30000.00")

    def test_clean_percent_over_100(self):
        d = Discount(
            kind=Discount.Kind.STUDENT_PERCENT,
            name="Bad",
            value_type=Discount.ValueType.PERCENT,
            value=Decimal("150"),
            start_date=date(2026, 1, 1),
        )
        with pytest.raises(ValidationError):
            d.clean()

    def test_clean_negative_value(self):
        d = Discount(
            kind=Discount.Kind.STUDENT_FIXED,
            name="Bad",
            value_type=Discount.ValueType.FIXED,
            value=Decimal("-10"),
            start_date=date(2026, 1, 1),
        )
        with pytest.raises(ValidationError):
            d.clean()

    def test_clean_invalid_dates(self):
        d = Discount(
            kind=Discount.Kind.STUDENT_PERCENT,
            name="Bad",
            value_type=Discount.ValueType.PERCENT,
            value=Decimal("10"),
            start_date=date(2026, 4, 10),
            end_date=date(2026, 4, 5),
        )
        with pytest.raises(ValidationError):
            d.clean()

    def test_is_expired(self):
        past = date.today() - timedelta(days=10)
        d = Discount(
            kind=Discount.Kind.PROMO_CODE,
            name="Old",
            value_type=Discount.ValueType.PERCENT,
            value=Decimal("10"),
            start_date=past - timedelta(days=10),
            end_date=past,
        )
        assert d.is_expired is True
        assert d.is_usable is False

    def test_is_exhausted(self):
        d = Discount(
            kind=Discount.Kind.PROMO_CODE,
            name="Limited",
            value_type=Discount.ValueType.PERCENT,
            value=Decimal("10"),
            start_date=date(2026, 1, 1),
            max_uses=5,
            uses_count=5,
        )
        assert d.is_exhausted is True
        assert d.is_usable is False


# =============================================================================
# Invoice
# =============================================================================

class TestInvoice:
    def _make_invoice(self, billing_profile, group_student, **kwargs):
        defaults = dict(
            student=group_student.student,
            group=group_student.group,
            group_student=group_student,
            billing_profile=billing_profile,
            period_month=4,
            period_year=2026,
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 30),
            base_amount=Decimal("500000"),
            due_date=date(2026, 4, 10),
            billable_days=30,
            total_period_days=30,
        )
        defaults.update(kwargs)
        return Invoice.objects.create(**defaults)

    def test_create_and_total(self, billing_profile, group_student):
        inv = self._make_invoice(billing_profile, group_student)
        assert inv.pk is not None
        assert inv.total_amount == Decimal("500000.00")
        assert inv.remaining == Decimal("500000.00")
        assert inv.is_paid is False

    def test_number_generated(self, billing_profile, group_student):
        inv = self._make_invoice(billing_profile, group_student)
        assert inv.number.startswith("INV-202604-")
        assert inv.number.endswith("00001")

    def test_number_increments(self, billing_profile, group_student, create_student):
        from apps.groups.models import GroupStudent
        inv1 = self._make_invoice(billing_profile, group_student)

        # Bir xil guruhda boshqa o'quvchi (unique constraint sababli)
        gs2 = GroupStudent.objects.create(
            group=group_student.group,
            student=create_student(first_name="Vali", phone="+998901112233"),
        )
        inv2 = self._make_invoice(billing_profile, gs2)
        assert inv1.number != inv2.number
        assert inv2.number.endswith("00002")

    def test_total_with_discount_and_late_fee(self, billing_profile, group_student):
        inv = self._make_invoice(
            billing_profile, group_student,
            base_amount=Decimal("500000"),
            discount_amount=Decimal("100000"),
            leave_credit_amount=Decimal("50000"),
            late_fee_amount=Decimal("20000"),
            extra_amount=Decimal("0"),
        )
        # 500000 - 100000 - 50000 + 20000 = 370000
        assert inv.total_amount == Decimal("370000.00")

    def test_total_never_negative(self, billing_profile, group_student):
        inv = self._make_invoice(
            billing_profile, group_student,
            base_amount=Decimal("100000"),
            discount_amount=Decimal("999999"),
        )
        assert inv.total_amount == Decimal("0")

    def test_unique_per_period(self, billing_profile, group_student):
        """Non-cancelled invoicelar uchun unique constraint."""
        self._make_invoice(billing_profile, group_student)
        with pytest.raises(IntegrityError):
            self._make_invoice(billing_profile, group_student)

    def test_unique_per_period_allows_cancelled(self, billing_profile, group_student):
        """Cancelled invoice bo'lsa yangi yaratish mumkin."""
        inv1 = self._make_invoice(billing_profile, group_student)
        inv1.status = Invoice.Status.CANCELLED
        inv1.save()
        # Endi yangi yaratish imkoni bor
        inv2 = self._make_invoice(billing_profile, group_student)
        assert inv2.pk != inv1.pk

    def test_recompute_status_unpaid(self, billing_profile, group_student):
        inv = self._make_invoice(
            billing_profile, group_student,
            due_date=date.today() + timedelta(days=5),
        )
        inv.recompute_status()
        assert inv.status == Invoice.Status.UNPAID

    def test_recompute_status_partial(self, billing_profile, group_student):
        inv = self._make_invoice(billing_profile, group_student)
        inv.paid_amount = Decimal("200000")
        inv.recompute_status()
        assert inv.status == Invoice.Status.PARTIAL

    def test_recompute_status_paid(self, billing_profile, group_student):
        inv = self._make_invoice(billing_profile, group_student)
        inv.paid_amount = Decimal("500000")
        inv.recompute_status()
        assert inv.status == Invoice.Status.PAID
        assert inv.paid_at is not None

    def test_recompute_status_overdue(self, billing_profile, group_student):
        inv = self._make_invoice(
            billing_profile, group_student,
            due_date=date.today() - timedelta(days=5),
        )
        inv.recompute_status()
        assert inv.status == Invoice.Status.OVERDUE

    def test_is_overdue_property(self, billing_profile, group_student):
        inv = self._make_invoice(
            billing_profile, group_student,
            due_date=date.today() - timedelta(days=1),
        )
        assert inv.is_overdue is True


# =============================================================================
# InvoiceLine
# =============================================================================

class TestInvoiceLine:
    def test_create_lines(self, billing_profile, group_student):
        inv = Invoice.objects.create(
            student=group_student.student,
            group=group_student.group,
            group_student=group_student,
            billing_profile=billing_profile,
            period_month=4,
            period_year=2026,
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 30),
            base_amount=Decimal("500000"),
            discount_amount=Decimal("75000"),
            due_date=date(2026, 4, 10),
        )

        InvoiceLine.objects.create(
            invoice=inv,
            kind=InvoiceLine.Kind.BASE,
            description="Aprel 2026 oylik",
            amount=Decimal("500000"),
        )
        InvoiceLine.objects.create(
            invoice=inv,
            kind=InvoiceLine.Kind.DISCOUNT,
            description="Aka-uka chegirmasi 15%",
            amount=Decimal("75000"),
        )

        assert inv.lines.count() == 2
        assert inv.total_amount == Decimal("425000.00")
