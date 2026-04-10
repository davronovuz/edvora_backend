"""
Edvora - Monthly Flat Strategy

Eng oddiy: oyning qaysi kunida qo'shilsa ham to'liq oylik to'lov.
Ta'til hisobga olinmaydi.

Misol:
    O'quvchi 15-aprelda qo'shildi, oylik 500,000 → invoice 500,000.
"""

from decimal import Decimal

from apps.billing.models import BillingProfile, InvoiceLine

from .base import (
    BaseBillingStrategy,
    CalculationResult,
    InvoiceContext,
    days_in_range,
    month_bounds,
)


class MonthlyFlatStrategy(BaseBillingStrategy):
    mode = BillingProfile.Mode.MONTHLY_FLAT

    def calculate(self, ctx: InvoiceContext) -> CalculationResult:
        period_start, period_end = month_bounds(ctx.period_year, ctx.period_month)
        total_days = days_in_range(period_start, period_end)

        base = Decimal(ctx.base_price or 0)

        result = CalculationResult(
            period_start=period_start,
            period_end=period_end,
            base_amount=base,
            billable_days=total_days,
            total_period_days=total_days,
        )

        result.lines.append(dict(
            kind=InvoiceLine.Kind.BASE,
            description=f"{ctx.period_month:02d}/{ctx.period_year} oylik to'lov",
            amount=base,
        ))
        return result
