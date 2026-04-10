"""
Edvora - Per Attendance Strategy

Faqat haqiqatda QATNASHGAN darslar uchun to'lov.
Apps/attendance modulidan ma'lumot oladi: PRESENT va LATE = qatnashgan,
ABSENT = kelmagan, EXCUSED = sababli (default chegiriladi).

Misol:
    price_per_lesson = 50,000.
    Aprel 2026: 13 dars rejada, o'quvchi 10 tasiga keldi (PRESENT/LATE).
    Invoice = 10 × 50,000 = 500,000.

EXCUSED (sababli kelmaganlarni) hisoblash siyosati:
    profile.extra_settings['charge_excused'] = True/False (default False).
"""

from decimal import Decimal

from apps.billing.models import BillingProfile, InvoiceLine

from .base import (
    BaseBillingStrategy,
    CalculationResult,
    InvoiceContext,
    count_lesson_days,
    days_in_range,
    month_bounds,
    quantize,
)


class PerAttendanceStrategy(BaseBillingStrategy):
    mode = BillingProfile.Mode.PER_ATTENDANCE

    # Qatnashgan deb hisoblanadigan statuslar
    BILLABLE_STATUSES = ('present', 'late')

    def calculate(self, ctx: InvoiceContext) -> CalculationResult:
        period_start, period_end = month_bounds(ctx.period_year, ctx.period_month)
        total_days = days_in_range(period_start, period_end)

        group = ctx.group_student.group
        student = ctx.group_student.student
        weekdays = group.days or []
        total_lessons = count_lesson_days(period_start, period_end, weekdays)

        price_per_lesson = self.profile.price_per_lesson
        if price_per_lesson is None:
            raise ValueError(
                "PerAttendanceStrategy uchun BillingProfile.price_per_lesson belgilanishi shart"
            )
        price_per_lesson = Decimal(price_per_lesson)

        # Effective start
        effective_start = max(period_start, ctx.enrollment_date)
        if effective_start > period_end:
            return CalculationResult(
                period_start=period_start,
                period_end=period_end,
                total_period_days=total_days,
                total_period_lessons=total_lessons,
            )

        # Attendance ma'lumotini olish
        from apps.attendance.models import Attendance

        billable_statuses = list(self.BILLABLE_STATUSES)
        if self.profile.extra_settings.get('charge_excused'):
            billable_statuses.append('excused')

        attended_count = Attendance.objects.filter(
            group=group,
            student=student,
            date__gte=effective_start,
            date__lte=period_end,
            status__in=billable_statuses,
        ).count()

        base_amount = price_per_lesson * Decimal(attended_count)

        result = CalculationResult(
            period_start=period_start,
            period_end=period_end,
            base_amount=base_amount,
            billable_lessons=attended_count,
            total_period_lessons=total_lessons,
            billable_days=days_in_range(effective_start, period_end),
            total_period_days=total_days,
        )

        result.lines.append(dict(
            kind=InvoiceLine.Kind.BASE,
            description=(
                f"{ctx.period_month:02d}/{ctx.period_year} qatnashgan darslar "
                f"({attended_count} × {price_per_lesson:,.0f})"
            ),
            amount=quantize(base_amount),
        ))

        return result
