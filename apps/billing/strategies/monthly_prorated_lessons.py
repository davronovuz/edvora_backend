"""
Edvora - Monthly Prorated (by Lessons) Strategy

Pro-rate, lekin kun emas — guruh jadvalidagi DARSLAR soni bo'yicha.
Adolatli: kun emas, haqiqiy darslar sanash.

Misol:
    Group.days = [0,2,4] (Du/Cho/Ju), monthly = 500,000.
    Aprel 2026 da jami 13 ta dars.
    O'quvchi 15-apreldan qo'shildi → 7 ta dars qoldi → (7/13) × 500,000.
    5 kunlik ta'tilga 2 dars to'g'ri kelsa → (5/13) × 500,000.
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


class MonthlyProratedLessonsStrategy(BaseBillingStrategy):
    mode = BillingProfile.Mode.MONTHLY_PRORATED_LESSONS

    def calculate(self, ctx: InvoiceContext) -> CalculationResult:
        period_start, period_end = month_bounds(ctx.period_year, ctx.period_month)
        total_days = days_in_range(period_start, period_end)

        group = ctx.group_student.group
        weekdays = group.days or []

        total_lessons = count_lesson_days(period_start, period_end, weekdays)

        effective_start = max(period_start, ctx.enrollment_date)
        if effective_start > period_end or total_lessons == 0:
            return CalculationResult(
                period_start=period_start,
                period_end=period_end,
                total_period_days=total_days,
                total_period_lessons=total_lessons,
            )

        gross_lessons = count_lesson_days(effective_start, period_end, weekdays)
        base_price = Decimal(ctx.base_price or 0)
        per_lesson = base_price / Decimal(total_lessons) if total_lessons else Decimal("0")
        base_amount = per_lesson * Decimal(gross_lessons)

        result = CalculationResult(
            period_start=period_start,
            period_end=period_end,
            base_amount=base_amount,
            billable_lessons=gross_lessons,
            total_period_lessons=total_lessons,
            billable_days=days_in_range(effective_start, period_end),
            total_period_days=total_days,
        )

        if gross_lessons == total_lessons:
            base_desc = f"{ctx.period_month:02d}/{ctx.period_year} to'liq oylik ({total_lessons} dars)"
        else:
            base_desc = (
                f"{ctx.period_month:02d}/{ctx.period_year} pro-rate "
                f"({gross_lessons}/{total_lessons} dars)"
            )
        result.lines.append(dict(
            kind=InvoiceLine.Kind.BASE,
            description=base_desc,
            amount=quantize(base_amount),
        ))

        # Ta'tilni qo'llash (PRORATE_LESSONS)
        if self.profile.leave_policy == BillingProfile.LeavePolicy.PRORATE_LESSONS:
            leave_lessons_total = 0
            for leave in ctx.leaves or []:
                if leave.status != StudentLeave.Status.APPROVED:
                    continue
                ls = max(leave.start_date, effective_start)
                le = min(leave.end_date, period_end)
                if ls > le:
                    continue
                gap_days = (le - ls).days + 1
                if gap_days < self.profile.min_leave_days:
                    continue
                lessons_in_leave = count_lesson_days(ls, le, weekdays)
                if lessons_in_leave == 0:
                    continue
                credit = per_lesson * Decimal(lessons_in_leave)
                result.leave_credit_amount += credit
                leave_lessons_total += lessons_in_leave
                result.lines.append(dict(
                    kind=InvoiceLine.Kind.LEAVE_CREDIT,
                    description=f"Ta'til chegirmasi ({lessons_in_leave} dars)",
                    amount=quantize(credit),
                    leave=leave,
                ))
            result.billable_lessons = max(gross_lessons - leave_lessons_total, 0)

        return result
