"""
Edvora - Hourly Strategy

Soat hisobida to'lov. Individual / repetitor / tutoring uchun.

Hisoblash:
    1 dars davomiyligi = group.end_time - group.start_time (soatda)
    Oylik soatlar = davomiyligi × oydagi dars kunlari
    Summa = soat × profile.price_per_hour

Misol:
    Group: 09:00-11:00 (2 soat), Du/Cho/Ju, 13 dars/oy.
    price_per_hour = 100,000.
    Oylik = 13 × 2 = 26 soat × 100,000 = 2,600,000.
"""

from datetime import datetime, timedelta
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


def lesson_duration_hours(start_time, end_time) -> Decimal:
    """Bir darsning soat birlikdagi davomiyligi."""
    if not start_time or not end_time:
        return Decimal("0")
    today = datetime(2000, 1, 1)
    start_dt = today.replace(hour=start_time.hour, minute=start_time.minute)
    end_dt = today.replace(hour=end_time.hour, minute=end_time.minute)
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)
    delta = end_dt - start_dt
    return Decimal(delta.total_seconds()) / Decimal("3600")


class HourlyStrategy(BaseBillingStrategy):
    mode = BillingProfile.Mode.HOURLY

    def calculate(self, ctx: InvoiceContext) -> CalculationResult:
        period_start, period_end = month_bounds(ctx.period_year, ctx.period_month)
        total_days = days_in_range(period_start, period_end)

        group = ctx.group_student.group
        weekdays = group.days or []

        price_per_hour = self.profile.price_per_hour
        if price_per_hour is None:
            raise ValueError(
                "HourlyStrategy uchun BillingProfile.price_per_hour belgilanishi shart"
            )
        price_per_hour = Decimal(price_per_hour)

        duration = lesson_duration_hours(group.start_time, group.end_time)
        if duration == 0:
            raise ValueError("Guruh start_time/end_time noto'g'ri belgilangan")

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

        total_hours = duration * Decimal(gross_lessons)
        base_amount = price_per_hour * total_hours

        result = CalculationResult(
            period_start=period_start,
            period_end=period_end,
            base_amount=base_amount,
            billable_lessons=gross_lessons,
            total_period_lessons=total_lessons,
            billable_days=days_in_range(effective_start, period_end),
            total_period_days=total_days,
        )
        result.lines.append(dict(
            kind=InvoiceLine.Kind.BASE,
            description=(
                f"{ctx.period_month:02d}/{ctx.period_year} "
                f"{gross_lessons} dars × {duration:.1f} soat × {price_per_hour:,.0f}"
            ),
            amount=quantize(base_amount),
            meta={
                'lessons': gross_lessons,
                'duration_per_lesson': str(duration),
                'total_hours': str(total_hours),
            },
        ))
        return result
