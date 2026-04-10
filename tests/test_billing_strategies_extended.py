"""
Edvora - Billing Strategies Extended Tests (Stage 3)

5 ta qolgan strategiya uchun testlar:
    - MonthlyProratedLessonsStrategy
    - PerAttendanceStrategy
    - PackageStrategy
    - HourlyStrategy
    - SubscriptionFreezeStrategy
"""

from datetime import date, time
from decimal import Decimal

import pytest

from apps.billing.models import BillingProfile, Invoice, InvoiceLine, StudentLeave
from apps.billing.registry import get_strategy
from apps.billing.strategies.base import InvoiceContext
from apps.billing.strategies.hourly import HourlyStrategy, lesson_duration_hours
from apps.billing.strategies.monthly_prorated_lessons import MonthlyProratedLessonsStrategy
from apps.billing.strategies.package import PackageStrategy
from apps.billing.strategies.per_attendance import PerAttendanceStrategy
from apps.billing.strategies.subscription_freeze import SubscriptionFreezeStrategy


pytestmark = pytest.mark.django_db


# =============================================================================
# Helpers
# =============================================================================

def make_profile(mode, **overrides):
    defaults = dict(name=f"Test {mode}", mode=mode)
    defaults.update(overrides)
    return BillingProfile.objects.create(**defaults)


@pytest.fixture
def april_group(create_course, create_teacher):
    """Du/Cho/Ju guruhi, narxi 500,000."""
    from apps.groups.models import Group
    return Group.objects.create(
        name="Aprel Group",
        course=create_course(price=Decimal("500000"), duration_months=6),
        teacher=create_teacher(),
        start_date=date(2026, 4, 1),
        end_date=date(2026, 9, 30),
        days=[0, 2, 4],
        start_time=time(9, 0),
        end_time=time(11, 0),
        max_students=15,
        status='active',
        price=Decimal("500000"),
    )


@pytest.fixture
def april_gs(april_group, create_student):
    from apps.groups.models import GroupStudent
    return GroupStudent.objects.create(
        group=april_group,
        student=create_student(),
        is_active=True,
        status='active',
    )


# =============================================================================
# MonthlyProratedLessonsStrategy
# =============================================================================

class TestMonthlyProratedLessons:
    def test_full_month(self, april_gs):
        profile = make_profile(BillingProfile.Mode.MONTHLY_PRORATED_LESSONS)
        strat = MonthlyProratedLessonsStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_gs,
            profile=profile,
            period_year=2026,
            period_month=4,
            enrollment_date=date(2026, 4, 1),
            base_price=Decimal("500000"),
            leaves=[],
        )
        inv = strat.generate(ctx)
        # 13/13 darslar
        assert inv.billable_lessons == 13
        assert inv.total_period_lessons == 13
        assert inv.base_amount == Decimal("500000.00")

    def test_mid_month_join(self, april_gs):
        """15-aprel: 7 dars qoldi 13 dan."""
        profile = make_profile(BillingProfile.Mode.MONTHLY_PRORATED_LESSONS)
        strat = MonthlyProratedLessonsStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_gs,
            profile=profile,
            period_year=2026,
            period_month=4,
            enrollment_date=date(2026, 4, 15),
            base_price=Decimal("500000"),
            leaves=[],
        )
        inv = strat.generate(ctx)
        assert inv.billable_lessons == 7
        # 7/13 × 500,000 = 269,230.77
        expected = (Decimal("500000") / Decimal("13") * Decimal("7")).quantize(Decimal("0.01"))
        assert inv.base_amount == expected

    def test_with_leave_lessons(self, april_gs):
        """6-10 aprel ta'tilda → Du(6), Cho(8), Ju(10) = 3 dars chegiriladi."""
        profile = make_profile(
            BillingProfile.Mode.MONTHLY_PRORATED_LESSONS,
            leave_policy=BillingProfile.LeavePolicy.PRORATE_LESSONS,
            min_leave_days=1,
        )
        leave = StudentLeave.objects.create(
            group_student=april_gs,
            start_date=date(2026, 4, 6),
            end_date=date(2026, 4, 10),
            reason="x",
            status=StudentLeave.Status.APPROVED,
        )
        strat = MonthlyProratedLessonsStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_gs,
            profile=profile,
            period_year=2026,
            period_month=4,
            enrollment_date=date(2026, 4, 1),
            base_price=Decimal("500000"),
            leaves=[leave],
        )
        inv = strat.generate(ctx)
        per_lesson = Decimal("500000") / Decimal("13")
        assert inv.leave_credit_amount == (per_lesson * 3).quantize(Decimal("0.01"))
        assert inv.billable_lessons == 10


# =============================================================================
# PerAttendanceStrategy
# =============================================================================

class TestPerAttendance:
    def test_no_attendance(self, april_gs):
        """Hech kelmagan = 0."""
        profile = make_profile(
            BillingProfile.Mode.PER_ATTENDANCE,
            price_per_lesson=Decimal("50000"),
        )
        strat = PerAttendanceStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_gs,
            profile=profile,
            period_year=2026,
            period_month=4,
            enrollment_date=date(2026, 4, 1),
            leaves=[],
        )
        inv = strat.generate(ctx)
        assert inv.base_amount == Decimal("0")
        assert inv.billable_lessons == 0

    def test_attended_lessons(self, april_gs):
        """3 darsga keldi (PRESENT/LATE) = 150,000."""
        from apps.attendance.models import Attendance
        Attendance.objects.create(
            group=april_gs.group,
            student=april_gs.student,
            date=date(2026, 4, 6),
            status='present',
        )
        Attendance.objects.create(
            group=april_gs.group,
            student=april_gs.student,
            date=date(2026, 4, 8),
            status='late',
        )
        Attendance.objects.create(
            group=april_gs.group,
            student=april_gs.student,
            date=date(2026, 4, 10),
            status='present',
        )
        # ABSENT — hisoblanmaydi
        Attendance.objects.create(
            group=april_gs.group,
            student=april_gs.student,
            date=date(2026, 4, 13),
            status='absent',
        )

        profile = make_profile(
            BillingProfile.Mode.PER_ATTENDANCE,
            price_per_lesson=Decimal("50000"),
        )
        strat = PerAttendanceStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_gs,
            profile=profile,
            period_year=2026,
            period_month=4,
            enrollment_date=date(2026, 4, 1),
            leaves=[],
        )
        inv = strat.generate(ctx)
        assert inv.billable_lessons == 3
        assert inv.base_amount == Decimal("150000.00")

    def test_charge_excused_setting(self, april_gs):
        """charge_excused=True bo'lsa, sababli kelmaganlar ham hisoblanadi."""
        from apps.attendance.models import Attendance
        Attendance.objects.create(
            group=april_gs.group, student=april_gs.student,
            date=date(2026, 4, 6), status='present',
        )
        Attendance.objects.create(
            group=april_gs.group, student=april_gs.student,
            date=date(2026, 4, 8), status='excused',
        )

        profile = make_profile(
            BillingProfile.Mode.PER_ATTENDANCE,
            price_per_lesson=Decimal("50000"),
            extra_settings={'charge_excused': True},
        )
        strat = PerAttendanceStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_gs,
            profile=profile,
            period_year=2026,
            period_month=4,
            enrollment_date=date(2026, 4, 1),
            leaves=[],
        )
        inv = strat.generate(ctx)
        assert inv.billable_lessons == 2
        assert inv.base_amount == Decimal("100000.00")

    def test_missing_price(self, april_gs):
        profile = make_profile(BillingProfile.Mode.PER_ATTENDANCE)
        strat = PerAttendanceStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_gs,
            profile=profile,
            period_year=2026, period_month=4,
            enrollment_date=date(2026, 4, 1),
            leaves=[],
        )
        with pytest.raises(ValueError):
            strat.generate(ctx)


# =============================================================================
# PackageStrategy
# =============================================================================

class TestPackage:
    def test_create_first_invoice(self, april_gs):
        """Birinchi invoice yaratiladi: butun kurs narxi."""
        profile = make_profile(BillingProfile.Mode.PACKAGE)
        strat = PackageStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_gs,
            profile=profile,
            period_year=2026,
            period_month=4,
            enrollment_date=date(2026, 4, 1),
            base_price=Decimal("3000000"),
            leaves=[],
        )
        inv = strat.generate(ctx)
        assert inv is not None
        assert inv.base_amount == Decimal("3000000.00")
        assert inv.total_amount == Decimal("3000000.00")
        # Period: kurs boshidan oxirigacha
        assert inv.period_start == date(2026, 4, 1)
        assert inv.period_end == date(2026, 9, 30)

    def test_second_call_returns_none(self, april_gs):
        """Ikkinchi marta chaqirilsa None — duplicate yaratmaydi."""
        profile = make_profile(BillingProfile.Mode.PACKAGE)
        strat = PackageStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_gs,
            profile=profile,
            period_year=2026, period_month=4,
            enrollment_date=date(2026, 4, 1),
            base_price=Decimal("3000000"),
            leaves=[],
        )
        first = strat.generate(ctx)
        assert first is not None

        ctx2 = InvoiceContext(
            group_student=april_gs,
            profile=profile,
            period_year=2026, period_month=5,
            enrollment_date=date(2026, 4, 1),
            base_price=Decimal("3000000"),
            leaves=[],
        )
        second = strat.generate(ctx2)
        assert second is None

    def test_uses_course_price_fallback(self, april_gs):
        profile = make_profile(BillingProfile.Mode.PACKAGE)
        strat = PackageStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_gs,
            profile=profile,
            period_year=2026, period_month=4,
            enrollment_date=date(2026, 4, 1),
            base_price=Decimal("0"),  # bo'sh
            leaves=[],
        )
        inv = strat.generate(ctx)
        # course.price = 500,000 (fixture default)
        assert inv.base_amount == Decimal("500000.00")


# =============================================================================
# HourlyStrategy
# =============================================================================

class TestHourly:
    def test_lesson_duration_helper(self):
        assert lesson_duration_hours(time(9, 0), time(11, 0)) == Decimal("2")
        assert lesson_duration_hours(time(9, 0), time(10, 30)) == Decimal("1.5")
        assert lesson_duration_hours(time(14, 15), time(15, 45)) == Decimal("1.5")

    def test_full_month(self, april_gs):
        """13 dars × 2 soat × 100,000 = 2,600,000"""
        profile = make_profile(
            BillingProfile.Mode.HOURLY,
            price_per_hour=Decimal("100000"),
        )
        strat = HourlyStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_gs,
            profile=profile,
            period_year=2026, period_month=4,
            enrollment_date=date(2026, 4, 1),
            leaves=[],
        )
        inv = strat.generate(ctx)
        assert inv.billable_lessons == 13
        assert inv.base_amount == Decimal("2600000.00")

    def test_mid_month_join(self, april_gs):
        """15-aprel: 7 dars × 2 soat × 100,000 = 1,400,000"""
        profile = make_profile(
            BillingProfile.Mode.HOURLY,
            price_per_hour=Decimal("100000"),
        )
        strat = HourlyStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_gs,
            profile=profile,
            period_year=2026, period_month=4,
            enrollment_date=date(2026, 4, 15),
            leaves=[],
        )
        inv = strat.generate(ctx)
        assert inv.billable_lessons == 7
        assert inv.base_amount == Decimal("1400000.00")

    def test_missing_price(self, april_gs):
        profile = make_profile(BillingProfile.Mode.HOURLY)
        strat = HourlyStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_gs,
            profile=profile,
            period_year=2026, period_month=4,
            enrollment_date=date(2026, 4, 1),
            leaves=[],
        )
        with pytest.raises(ValueError):
            strat.generate(ctx)


# =============================================================================
# SubscriptionFreezeStrategy
# =============================================================================

class TestSubscriptionFreeze:
    def test_full_month(self, april_gs):
        profile = make_profile(BillingProfile.Mode.SUBSCRIPTION_FREEZE)
        strat = SubscriptionFreezeStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_gs,
            profile=profile,
            period_year=2026, period_month=4,
            enrollment_date=date(2026, 4, 1),
            base_price=Decimal("500000"),
            leaves=[],
        )
        inv = strat.generate(ctx)
        assert inv.base_amount == Decimal("500000.00")
        assert inv.total_amount == Decimal("500000.00")

    def test_fully_frozen_month(self, april_gs):
        """GroupStudent.status = frozen → 0 to'lov."""
        april_gs.status = 'frozen'
        april_gs.save()

        profile = make_profile(BillingProfile.Mode.SUBSCRIPTION_FREEZE)
        strat = SubscriptionFreezeStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_gs,
            profile=profile,
            period_year=2026, period_month=4,
            enrollment_date=date(2026, 4, 1),
            base_price=Decimal("500000"),
            leaves=[],
        )
        inv = strat.generate(ctx)
        assert inv.base_amount == Decimal("0")
        assert inv.total_amount == Decimal("0")
        assert inv.billable_days == 0

    def test_partial_freeze_via_leave(self, april_gs):
        """10 kunlik freeze (StudentLeave) → 20 kun bo'yicha"""
        profile = make_profile(BillingProfile.Mode.SUBSCRIPTION_FREEZE)
        leave = StudentLeave.objects.create(
            group_student=april_gs,
            start_date=date(2026, 4, 10),
            end_date=date(2026, 4, 19),  # 10 kun
            reason="freeze",
            status=StudentLeave.Status.APPROVED,
        )
        strat = SubscriptionFreezeStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_gs,
            profile=profile,
            period_year=2026, period_month=4,
            enrollment_date=date(2026, 4, 1),
            base_price=Decimal("500000"),
            leaves=[leave],
        )
        inv = strat.generate(ctx)
        per_day = Decimal("500000") / Decimal("30")
        # base = 30 kun, freeze credit = 10 kun
        assert inv.leave_credit_amount == (per_day * 10).quantize(Decimal("0.01"))
        assert inv.billable_days == 20

    def test_freeze_min_days(self, april_gs):
        """freeze_min_days=7 — 5 kunlik freeze hisobga olinmaydi."""
        profile = make_profile(
            BillingProfile.Mode.SUBSCRIPTION_FREEZE,
            extra_settings={'freeze_min_days': 7},
        )
        leave = StudentLeave.objects.create(
            group_student=april_gs,
            start_date=date(2026, 4, 10),
            end_date=date(2026, 4, 14),  # 5 kun
            reason="x",
            status=StudentLeave.Status.APPROVED,
        )
        strat = SubscriptionFreezeStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_gs,
            profile=profile,
            period_year=2026, period_month=4,
            enrollment_date=date(2026, 4, 1),
            base_price=Decimal("500000"),
            leaves=[leave],
        )
        inv = strat.generate(ctx)
        assert inv.leave_credit_amount == Decimal("0")
        assert inv.total_amount == Decimal("500000.00")


# =============================================================================
# Registry — yangi modellar
# =============================================================================

class TestRegistryNewModes:
    def test_all_modes_resolvable(self):
        """8 ta mode hammasi factory orqali topiladi."""
        for mode in [
            BillingProfile.Mode.MONTHLY_FLAT,
            BillingProfile.Mode.MONTHLY_PRORATED_DAYS,
            BillingProfile.Mode.MONTHLY_PRORATED_LESSONS,
            BillingProfile.Mode.PER_LESSON,
            BillingProfile.Mode.PER_ATTENDANCE,
            BillingProfile.Mode.PACKAGE,
            BillingProfile.Mode.HOURLY,
            BillingProfile.Mode.SUBSCRIPTION_FREEZE,
        ]:
            profile = BillingProfile(name=f"P-{mode}", mode=mode)
            strat = get_strategy(profile)
            assert strat is not None
            assert strat.profile is profile
