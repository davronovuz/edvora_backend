"""
Edvora - Billing Strategies Tests (Stage 2)

3 ta asosiy strategy uchun real ssenariylar bilan testlar:
    - MonthlyFlatStrategy
    - MonthlyProratedDaysStrategy (kunlik pro-rate, ta'til bilan)
    - PerLessonStrategy (guruh jadvali bo'yicha darslar)

Va: registry, factory, hisob-kitob to'g'riligi.
"""

from datetime import date, time
from decimal import Decimal

import pytest

from apps.billing.models import BillingProfile, Invoice, InvoiceLine, StudentLeave
from apps.billing.registry import (
    StrategyNotImplementedError,
    available_modes,
    get_strategy,
    register_strategy,
)
from apps.billing.strategies.base import (
    BaseBillingStrategy,
    InvoiceContext,
    count_lesson_days,
    days_in_range,
    month_bounds,
    overlap_days,
)
from apps.billing.strategies.monthly_flat import MonthlyFlatStrategy
from apps.billing.strategies.monthly_prorated_days import MonthlyProratedDaysStrategy
from apps.billing.strategies.per_lesson import PerLessonStrategy


pytestmark = pytest.mark.django_db


# =============================================================================
# Helpers
# =============================================================================

def make_profile(mode, **overrides):
    defaults = dict(
        name=f"Test {mode}",
        mode=mode,
    )
    defaults.update(overrides)
    return BillingProfile.objects.create(**defaults)


@pytest.fixture
def april_group(create_course, create_teacher):
    """Du/Cho/Ju guruhi, narxi 500,000."""
    from apps.groups.models import Group
    return Group.objects.create(
        name="Aprel Group",
        course=create_course(price=Decimal("500000")),
        teacher=create_teacher(),
        start_date=date(2026, 3, 1),
        days=[0, 2, 4],  # Du, Cho, Ju
        start_time=time(9, 0),
        end_time=time(11, 0),
        max_students=15,
        status='active',
        price=Decimal("500000"),
    )


@pytest.fixture
def april_group_student(april_group, create_student):
    from apps.groups.models import GroupStudent
    return GroupStudent.objects.create(
        group=april_group,
        student=create_student(),
        is_active=True,
        status='active',
    )


# =============================================================================
# Helper functions
# =============================================================================

class TestHelpers:
    def test_month_bounds(self):
        s, e = month_bounds(2026, 4)
        assert s == date(2026, 4, 1)
        assert e == date(2026, 4, 30)

        s, e = month_bounds(2026, 2)
        assert e == date(2026, 2, 28)

        s, e = month_bounds(2024, 2)  # leap year
        assert e == date(2024, 2, 29)

    def test_days_in_range(self):
        assert days_in_range(date(2026, 4, 1), date(2026, 4, 30)) == 30
        assert days_in_range(date(2026, 4, 15), date(2026, 4, 15)) == 1
        assert days_in_range(date(2026, 4, 20), date(2026, 4, 10)) == 0

    def test_overlap_days(self):
        # To'liq kesishish
        assert overlap_days(
            date(2026, 4, 1), date(2026, 4, 30),
            date(2026, 4, 5), date(2026, 4, 10),
        ) == 6
        # Kesishmaslik
        assert overlap_days(
            date(2026, 4, 1), date(2026, 4, 10),
            date(2026, 4, 15), date(2026, 4, 20),
        ) == 0
        # Qisman kesishish
        assert overlap_days(
            date(2026, 4, 1), date(2026, 4, 15),
            date(2026, 4, 10), date(2026, 4, 20),
        ) == 6  # 10..15

    def test_count_lesson_days(self):
        # Aprel 2026: Du/Cho/Ju (0, 2, 4)
        # 1-aprel = chorshanba (2), shuning uchun mos keladi
        count = count_lesson_days(date(2026, 4, 1), date(2026, 4, 30), [0, 2, 4])
        # Aprel 2026 da: Du = 6,13,20,27 (4 ta), Cho = 1,8,15,22,29 (5 ta), Ju = 3,10,17,24 (4 ta)
        assert count == 13

    def test_count_lesson_days_empty(self):
        assert count_lesson_days(date(2026, 4, 1), date(2026, 4, 30), []) == 0


# =============================================================================
# Registry
# =============================================================================

class TestRegistry:
    def test_get_strategy_flat(self):
        profile = make_profile(BillingProfile.Mode.MONTHLY_FLAT)
        strat = get_strategy(profile)
        assert isinstance(strat, MonthlyFlatStrategy)

    def test_get_strategy_prorated(self):
        profile = make_profile(BillingProfile.Mode.MONTHLY_PRORATED_DAYS)
        assert isinstance(get_strategy(profile), MonthlyProratedDaysStrategy)

    def test_get_strategy_per_lesson(self):
        profile = make_profile(
            BillingProfile.Mode.PER_LESSON,
            price_per_lesson=Decimal("50000"),
        )
        assert isinstance(get_strategy(profile), PerLessonStrategy)

    def test_unimplemented_mode(self):
        # Sun'iy mode (registryda yo'q)
        profile = BillingProfile(name="bad", mode="non_existent_mode")
        with pytest.raises(StrategyNotImplementedError):
            get_strategy(profile)

    def test_available_modes(self):
        modes = available_modes()
        assert BillingProfile.Mode.MONTHLY_FLAT in modes
        assert BillingProfile.Mode.MONTHLY_PRORATED_DAYS in modes
        assert BillingProfile.Mode.PER_LESSON in modes

    def test_register_custom_strategy(self):
        class DummyStrategy(BaseBillingStrategy):
            def calculate(self, ctx):
                from apps.billing.strategies.base import CalculationResult, month_bounds
                ps, pe = month_bounds(ctx.period_year, ctx.period_month)
                return CalculationResult(period_start=ps, period_end=pe)

        register_strategy("dummy_test", DummyStrategy)
        profile = BillingProfile(
            name="dummy", mode="dummy_test",
        )
        # Don't save (mode not in choices), just instantiate strategy via dict
        from apps.billing.registry import _STRATEGIES
        assert _STRATEGIES["dummy_test"] is DummyStrategy
        # Cleanup
        del _STRATEGIES["dummy_test"]

    def test_register_invalid_class(self):
        with pytest.raises(TypeError):
            register_strategy("bad", str)


# =============================================================================
# MonthlyFlatStrategy
# =============================================================================

class TestMonthlyFlat:
    def test_full_month(self, april_group_student):
        profile = make_profile(BillingProfile.Mode.MONTHLY_FLAT)
        strat = MonthlyFlatStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_group_student,
            profile=profile,
            period_year=2026,
            period_month=4,
            enrollment_date=date(2026, 4, 1),
            base_price=Decimal("500000"),
            leaves=[],
        )
        invoice = strat.generate(ctx)

        assert invoice.base_amount == Decimal("500000.00")
        assert invoice.total_amount == Decimal("500000.00")
        assert invoice.billable_days == 30
        assert invoice.lines.count() == 1

    def test_mid_month_join_still_full(self, april_group_student):
        """Flat: 15-aprelda qo'shilsa ham to'liq summa."""
        profile = make_profile(BillingProfile.Mode.MONTHLY_FLAT)
        strat = MonthlyFlatStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_group_student,
            profile=profile,
            period_year=2026,
            period_month=4,
            enrollment_date=date(2026, 4, 15),
            base_price=Decimal("500000"),
            leaves=[],
        )
        invoice = strat.generate(ctx)
        assert invoice.total_amount == Decimal("500000.00")

    def test_february_28(self, april_group_student):
        profile = make_profile(BillingProfile.Mode.MONTHLY_FLAT)
        strat = MonthlyFlatStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_group_student,
            profile=profile,
            period_year=2026,
            period_month=2,
            enrollment_date=date(2026, 2, 1),
            base_price=Decimal("500000"),
            leaves=[],
        )
        invoice = strat.generate(ctx)
        assert invoice.billable_days == 28
        assert invoice.total_amount == Decimal("500000.00")


# =============================================================================
# MonthlyProratedDaysStrategy
# =============================================================================

class TestMonthlyProratedDays:
    def _build(self, **kwargs):
        return make_profile(
            BillingProfile.Mode.MONTHLY_PRORATED_DAYS,
            leave_policy=kwargs.pop('leave_policy', BillingProfile.LeavePolicy.PRORATE_DAYS),
            min_leave_days=kwargs.pop('min_leave_days', 1),
            **kwargs,
        )

    def test_full_month(self, april_group_student):
        profile = self._build()
        strat = MonthlyProratedDaysStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_group_student,
            profile=profile,
            period_year=2026,
            period_month=4,
            enrollment_date=date(2026, 4, 1),
            base_price=Decimal("500000"),
            leaves=[],
        )
        inv = strat.generate(ctx)
        assert inv.base_amount == Decimal("500000.00")
        assert inv.total_amount == Decimal("500000.00")
        assert inv.billable_days == 30

    def test_mid_month_join_15(self, april_group_student):
        """15-apreldan: 16 kun (15..30), 500,000 * 16/30 = 266,666.67"""
        profile = self._build()
        strat = MonthlyProratedDaysStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_group_student,
            profile=profile,
            period_year=2026,
            period_month=4,
            enrollment_date=date(2026, 4, 15),
            base_price=Decimal("500000"),
            leaves=[],
        )
        inv = strat.generate(ctx)
        expected = (Decimal("500000") / Decimal("30")) * Decimal("16")
        assert inv.base_amount == expected.quantize(Decimal("0.01"))
        assert inv.billable_days == 16

    def test_mid_month_join_last_day(self, april_group_student):
        """30-apreldan: faqat 1 kun = 16,666.67"""
        profile = self._build()
        strat = MonthlyProratedDaysStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_group_student,
            profile=profile,
            period_year=2026,
            period_month=4,
            enrollment_date=date(2026, 4, 30),
            base_price=Decimal("500000"),
            leaves=[],
        )
        inv = strat.generate(ctx)
        assert inv.billable_days == 1
        expected = (Decimal("500000") / Decimal("30"))
        assert inv.base_amount == expected.quantize(Decimal("0.01"))

    def test_enrollment_after_period(self, april_group_student):
        """May'da qo'shilsa, aprel uchun 0 to'lash kerak."""
        profile = self._build()
        strat = MonthlyProratedDaysStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_group_student,
            profile=profile,
            period_year=2026,
            period_month=4,
            enrollment_date=date(2026, 5, 1),
            base_price=Decimal("500000"),
            leaves=[],
        )
        inv = strat.generate(ctx)
        assert inv.billable_days == 0
        assert inv.base_amount == Decimal("0.00")
        assert inv.total_amount == Decimal("0.00")

    def test_full_month_with_leave(self, april_group_student):
        """30 kun, 5 kun ta'til → 25 kun bo'yicha."""
        profile = self._build()
        leave = StudentLeave.objects.create(
            group_student=april_group_student,
            start_date=date(2026, 4, 10),
            end_date=date(2026, 4, 14),  # 5 kun
            reason="x",
            status=StudentLeave.Status.APPROVED,
        )
        strat = MonthlyProratedDaysStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_group_student,
            profile=profile,
            period_year=2026,
            period_month=4,
            enrollment_date=date(2026, 4, 1),
            base_price=Decimal("500000"),
            leaves=[leave],
        )
        inv = strat.generate(ctx)
        per_day = Decimal("500000") / Decimal("30")
        assert inv.base_amount == (per_day * Decimal("30")).quantize(Decimal("0.01"))
        assert inv.leave_credit_amount == (per_day * Decimal("5")).quantize(Decimal("0.01"))
        # total = base - leave_credit
        expected_total = (per_day * Decimal("25")).quantize(Decimal("0.01"))
        assert inv.total_amount == expected_total
        assert inv.billable_days == 25

    def test_min_leave_days_filter(self, april_group_student):
        """min_leave_days=3 bo'lsa, 2 kunlik ta'til hisobga olinmaydi."""
        profile = self._build(min_leave_days=3)
        leave = StudentLeave.objects.create(
            group_student=april_group_student,
            start_date=date(2026, 4, 10),
            end_date=date(2026, 4, 11),  # 2 kun
            reason="x",
            status=StudentLeave.Status.APPROVED,
        )
        strat = MonthlyProratedDaysStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_group_student,
            profile=profile,
            period_year=2026,
            period_month=4,
            enrollment_date=date(2026, 4, 1),
            base_price=Decimal("500000"),
            leaves=[leave],
        )
        inv = strat.generate(ctx)
        assert inv.leave_credit_amount == Decimal("0")
        assert inv.total_amount == Decimal("500000.00")

    def test_leave_policy_none(self, april_group_student):
        """leave_policy=NONE bo'lsa ta'til umuman hisoblanmaydi."""
        profile = self._build(leave_policy=BillingProfile.LeavePolicy.NONE)
        leave = StudentLeave.objects.create(
            group_student=april_group_student,
            start_date=date(2026, 4, 10),
            end_date=date(2026, 4, 14),
            reason="x",
            status=StudentLeave.Status.APPROVED,
        )
        strat = MonthlyProratedDaysStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_group_student,
            profile=profile,
            period_year=2026,
            period_month=4,
            enrollment_date=date(2026, 4, 1),
            base_price=Decimal("500000"),
            leaves=[leave],
        )
        inv = strat.generate(ctx)
        assert inv.leave_credit_amount == Decimal("0")
        assert inv.total_amount == Decimal("500000.00")

    def test_pending_leave_ignored(self, april_group_student):
        """Faqat APPROVED ta'til hisobga olinadi."""
        profile = self._build()
        StudentLeave.objects.create(
            group_student=april_group_student,
            start_date=date(2026, 4, 10),
            end_date=date(2026, 4, 14),
            reason="x",
            status=StudentLeave.Status.PENDING,
        )
        strat = MonthlyProratedDaysStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_group_student,
            profile=profile,
            period_year=2026,
            period_month=4,
            enrollment_date=date(2026, 4, 1),
            base_price=Decimal("500000"),
            leaves=None,  # default fetch
        )
        inv = strat.generate(ctx)
        assert inv.leave_credit_amount == Decimal("0")
        assert inv.total_amount == Decimal("500000.00")

    def test_join_15_with_leave(self, april_group_student):
        """15-aprelda qo'shilgan + 5 kun ta'til (16..20) → 11 kun"""
        profile = self._build()
        leave = StudentLeave.objects.create(
            group_student=april_group_student,
            start_date=date(2026, 4, 16),
            end_date=date(2026, 4, 20),  # 5 kun
            reason="x",
            status=StudentLeave.Status.APPROVED,
        )
        strat = MonthlyProratedDaysStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_group_student,
            profile=profile,
            period_year=2026,
            period_month=4,
            enrollment_date=date(2026, 4, 15),
            base_price=Decimal("500000"),
            leaves=[leave],
        )
        inv = strat.generate(ctx)
        per_day = Decimal("500000") / Decimal("30")
        # Base: 16 kun (15..30)
        assert inv.base_amount == (per_day * Decimal("16")).quantize(Decimal("0.01"))
        # Leave: 5 kun
        assert inv.leave_credit_amount == (per_day * Decimal("5")).quantize(Decimal("0.01"))
        # Net: 11 kun
        assert inv.billable_days == 11
        # base va leave alohida yaxlitlanadi, shuning uchun: base - credit
        expected = (per_day * Decimal("16")).quantize(Decimal("0.01")) \
                   - (per_day * Decimal("5")).quantize(Decimal("0.01"))
        assert inv.total_amount == expected


# =============================================================================
# PerLessonStrategy
# =============================================================================

class TestPerLesson:
    def _build(self, **kwargs):
        return make_profile(
            BillingProfile.Mode.PER_LESSON,
            price_per_lesson=Decimal("50000"),
            leave_policy=kwargs.pop('leave_policy', BillingProfile.LeavePolicy.PRORATE_LESSONS),
            min_leave_days=kwargs.pop('min_leave_days', 1),
            **kwargs,
        )

    def test_full_month(self, april_group_student):
        """Aprel 2026 da Du/Cho/Ju = 13 dars × 50,000 = 650,000."""
        profile = self._build()
        strat = PerLessonStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_group_student,
            profile=profile,
            period_year=2026,
            period_month=4,
            enrollment_date=date(2026, 4, 1),
            leaves=[],
        )
        inv = strat.generate(ctx)
        assert inv.total_period_lessons == 13
        assert inv.billable_lessons == 13
        assert inv.base_amount == Decimal("650000.00")
        assert inv.total_amount == Decimal("650000.00")

    def test_mid_month_join(self, april_group_student):
        """15-apreldan: qolgan dars kunlari hisoblanadi."""
        profile = self._build()
        strat = PerLessonStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_group_student,
            profile=profile,
            period_year=2026,
            period_month=4,
            enrollment_date=date(2026, 4, 15),
            leaves=[],
        )
        inv = strat.generate(ctx)
        # Aprel 15..30, Du/Cho/Ju: 15(Cho), 17(Ju), 20(Du), 22(Cho), 24(Ju), 27(Du), 29(Cho) = 7
        assert inv.total_period_lessons == 13
        assert inv.billable_lessons == 7
        assert inv.base_amount == Decimal("350000.00")  # 7 × 50,000

    def test_with_leave(self, april_group_student):
        """5 kunlik ta'tilga 2 ta dars to'g'ri kelsa, ular chegiriladi."""
        profile = self._build()
        # 6-Du, 8-Cho ikkalasi ta'tilga to'g'ri keladi (6..10)
        leave = StudentLeave.objects.create(
            group_student=april_group_student,
            start_date=date(2026, 4, 6),
            end_date=date(2026, 4, 10),
            reason="x",
            status=StudentLeave.Status.APPROVED,
        )
        strat = PerLessonStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_group_student,
            profile=profile,
            period_year=2026,
            period_month=4,
            enrollment_date=date(2026, 4, 1),
            leaves=[leave],
        )
        inv = strat.generate(ctx)
        # Aprel 6 = Du, 8 = Cho, 10 = Ju → 3 ta dars
        assert inv.leave_credit_amount == Decimal("150000.00")
        assert inv.billable_lessons == 10  # 13 - 3
        assert inv.total_amount == Decimal("500000.00")  # 10 × 50,000

    def test_missing_price_raises(self, april_group_student):
        profile = make_profile(
            BillingProfile.Mode.PER_LESSON,
            price_per_lesson=None,
        )
        strat = PerLessonStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_group_student,
            profile=profile,
            period_year=2026,
            period_month=4,
            enrollment_date=date(2026, 4, 1),
            leaves=[],
        )
        with pytest.raises(ValueError):
            strat.generate(ctx)


# =============================================================================
# Integration: Invoice yaratilgandan keyingi holat
# =============================================================================

class TestInvoiceAfterGeneration:
    def test_invoice_lines_created(self, april_group_student):
        profile = make_profile(BillingProfile.Mode.MONTHLY_FLAT)
        strat = MonthlyFlatStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_group_student,
            profile=profile,
            period_year=2026,
            period_month=4,
            enrollment_date=date(2026, 4, 1),
            base_price=Decimal("500000"),
            leaves=[],
        )
        inv = strat.generate(ctx)
        lines = list(inv.lines.all())
        assert len(lines) == 1
        assert lines[0].kind == InvoiceLine.Kind.BASE
        assert lines[0].amount == Decimal("500000.00")

    def test_invoice_status_unpaid_after_generation(self, april_group_student):
        from datetime import timedelta
        profile = make_profile(BillingProfile.Mode.MONTHLY_FLAT, due_days=10)
        strat = MonthlyFlatStrategy(profile)
        ctx = InvoiceContext(
            group_student=april_group_student,
            profile=profile,
            period_year=2026,
            period_month=4,
            enrollment_date=date(2026, 4, 1),
            base_price=Decimal("500000"),
            leaves=[],
            issue_date=date.today(),
        )
        inv = strat.generate(ctx)
        assert inv.status == Invoice.Status.UNPAID
        assert inv.due_date == date.today() + timedelta(days=10)
