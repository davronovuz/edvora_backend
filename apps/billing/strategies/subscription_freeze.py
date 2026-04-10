"""
Edvora - Subscription Freeze Strategy

Oylik obuna + muzlatish (Gym/fitness modeli).
Asosan oylik flat, lekin "frozen" davrlar pro-rate qilinadi.

GroupStudent.status == FROZEN bo'lsa va shu davrda butun oy bo'lsa → 0.
Yoki: ta'tillar (StudentLeave with kind=freeze) bo'yicha kunlar chegiriladi.

Hozircha sodda implementatsiya:
    - Agar group_student.status == FROZEN bo'lsa, butun oy 0
    - Aks holda flat oylik
    - StudentLeave APPROVED bo'lsa, kunlar pro-rate qilinadi (freeze sifatida)

Profile sozlamasi:
    extra_settings = {'freeze_min_days': 7}  — minimal muzlatish davri
"""

from decimal import Decimal

from apps.billing.models import BillingProfile, InvoiceLine, StudentLeave

from .base import (
    BaseBillingStrategy,
    CalculationResult,
    InvoiceContext,
    days_in_range,
    month_bounds,
    overlap_days,
    quantize,
)


class SubscriptionFreezeStrategy(BaseBillingStrategy):
    mode = BillingProfile.Mode.SUBSCRIPTION_FREEZE

    def calculate(self, ctx: InvoiceContext) -> CalculationResult:
        period_start, period_end = month_bounds(ctx.period_year, ctx.period_month)
        total_days = days_in_range(period_start, period_end)

        gs = ctx.group_student

        # Agar butun davr uchun FROZEN bo'lsa, 0
        if getattr(gs, 'status', None) == 'frozen':
            result = CalculationResult(
                period_start=period_start,
                period_end=period_end,
                base_amount=Decimal("0"),
                billable_days=0,
                total_period_days=total_days,
            )
            result.lines.append(dict(
                kind=InvoiceLine.Kind.BASE,
                description=f"{ctx.period_month:02d}/{ctx.period_year} obuna (muzlatilgan)",
                amount=Decimal("0"),
            ))
            return result

        effective_start = max(period_start, ctx.enrollment_date)
        if effective_start > period_end:
            return CalculationResult(
                period_start=period_start,
                period_end=period_end,
                total_period_days=total_days,
            )

        base_price = Decimal(ctx.base_price or 0)
        per_day = base_price / Decimal(total_days) if total_days else Decimal("0")

        gross_billable_days = days_in_range(effective_start, period_end)
        base_amount = per_day * Decimal(gross_billable_days)

        result = CalculationResult(
            period_start=period_start,
            period_end=period_end,
            base_amount=base_amount,
            billable_days=gross_billable_days,
            total_period_days=total_days,
        )

        if gross_billable_days == total_days:
            base_desc = f"{ctx.period_month:02d}/{ctx.period_year} obuna (to'liq oy)"
        else:
            base_desc = (
                f"{ctx.period_month:02d}/{ctx.period_year} obuna "
                f"({gross_billable_days}/{total_days} kun)"
            )
        result.lines.append(dict(
            kind=InvoiceLine.Kind.BASE,
            description=base_desc,
            amount=quantize(base_amount),
        ))

        # Freeze davrlari (StudentLeave APPROVED)
        freeze_min_days = self.profile.extra_settings.get('freeze_min_days', 1)
        total_freeze_days = 0
        for leave in ctx.leaves or []:
            if leave.status != StudentLeave.Status.APPROVED:
                continue
            days = overlap_days(effective_start, period_end, leave.start_date, leave.end_date)
            if days < freeze_min_days:
                continue
            credit = per_day * Decimal(days)
            result.leave_credit_amount += credit
            total_freeze_days += days
            result.lines.append(dict(
                kind=InvoiceLine.Kind.LEAVE_CREDIT,
                description=f"Muzlatish ({days} kun)",
                amount=quantize(credit),
                leave=leave,
            ))

        result.billable_days = max(gross_billable_days - total_freeze_days, 0)
        return result
