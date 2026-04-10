"""
Edvora - Per Lesson Strategy

Har dars uchun alohida narx (oylik emas).
Guruh jadvali (Group.days = [0,2,4]) asosida darslar soni hisoblanadi.

Misol:
    Group.days = [0,2,4] (Du/Cho/Ju), price_per_lesson = 50,000.
    Aprel 2026 da Du/Cho/Ju = 13 ta dars → 650,000.
    Agar 5 dars ta'tilga to'g'ri kelsa va PRORATE_LESSONS yoqilgan bo'lsa
    → 8 dars × 50,000 = 400,000.
"""

from decimal import Decimal

from apps.billing.models import BillingProfile, InvoiceLine, StudentLeave

from .base import (
    BaseBillingStrategy,
    CalculationResult,
    InvoiceContext,
    count_lesson_days,
    days_in_range,
    month_bounds,
    quantize,
)


class PerLessonStrategy(BaseBillingStrategy):
    mode = BillingProfile.Mode.PER_LESSON

    def calculate(self, ctx: InvoiceContext) -> CalculationResult:
        period_start, period_end = month_bounds(ctx.period_year, ctx.period_month)
        total_days = days_in_range(period_start, period_end)

        group = ctx.group_student.group
        weekdays = group.days or []

        # Effective start: enrollmentdan keyin
        effective_start = max(period_start, ctx.enrollment_date)
        if effective_start > period_end:
            return CalculationResult(
                period_start=period_start,
                period_end=period_end,
                total_period_days=total_days,
                total_period_lessons=count_lesson_days(period_start, period_end, weekdays),
            )

        total_lessons = count_lesson_days(period_start, period_end, weekdays)
        gross_lessons = count_lesson_days(effective_start, period_end, weekdays)

        # Dars narxini olish: avval profile, keyin group.actual_price (oylik emas, lekin fallback)
        price_per_lesson = (
            self.profile.price_per_lesson
            if self.profile.price_per_lesson is not None
            else None
        )
        if price_per_lesson is None:
            raise ValueError(
                "PerLessonStrategy uchun BillingProfile.price_per_lesson belgilanishi shart"
            )
        price_per_lesson = Decimal(price_per_lesson)

        # Ta'tilni qo'llash (PRORATE_LESSONS)
        leave_lessons = 0
        applied_leaves: list[tuple[StudentLeave, int]] = []
        if self.profile.leave_policy == BillingProfile.LeavePolicy.PRORATE_LESSONS:
            for leave in ctx.leaves or []:
                if leave.status != StudentLeave.Status.APPROVED:
                    continue
                # Ta'til oralig'ini effective davr bilan kesishtirish
                ls = max(leave.start_date, effective_start)
                le = min(leave.end_date, period_end)
                if ls > le:
                    continue
                days = (le - ls).days + 1
                if days < self.profile.min_leave_days:
                    continue
                lessons_in_leave = count_lesson_days(ls, le, weekdays)
                if lessons_in_leave > 0:
                    leave_lessons += lessons_in_leave
                    applied_leaves.append((leave, lessons_in_leave))

        billable_lessons = max(gross_lessons - leave_lessons, 0)
        base_amount = price_per_lesson * Decimal(gross_lessons)
        leave_credit = price_per_lesson * Decimal(leave_lessons)

        result = CalculationResult(
            period_start=period_start,
            period_end=period_end,
            base_amount=base_amount,
            leave_credit_amount=leave_credit,
            billable_lessons=billable_lessons,
            total_period_lessons=total_lessons,
            billable_days=days_in_range(effective_start, period_end),
            total_period_days=total_days,
        )

        if gross_lessons == total_lessons:
            base_desc = (
                f"{ctx.period_month:02d}/{ctx.period_year} "
                f"darslar ({gross_lessons} × {price_per_lesson:,.0f})"
            )
        else:
            base_desc = (
                f"{ctx.period_month:02d}/{ctx.period_year} "
                f"darslar ({gross_lessons}/{total_lessons} × {price_per_lesson:,.0f})"
            )
        result.lines.append(dict(
            kind=InvoiceLine.Kind.BASE,
            description=base_desc,
            amount=quantize(base_amount),
        ))

        for leave, lessons in applied_leaves:
            result.lines.append(dict(
                kind=InvoiceLine.Kind.LEAVE_CREDIT,
                description=f"Ta'til chegirmasi ({lessons} dars)",
                amount=quantize(price_per_lesson * Decimal(lessons)),
                leave=leave,
            ))

        return result
