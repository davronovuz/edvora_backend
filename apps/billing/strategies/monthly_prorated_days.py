"""
Edvora - Monthly Prorated (by Days) Strategy

Kun bo'yicha pro-rate. Sen aytgan asosiy muammoni hal qiladi:
o'quvchi oyning o'rtasida qo'shilsa, faqat qolgan kunlar uchun to'laydi.

Misollar (oylik 500,000, aprel = 30 kun):
    1. To'liq oy: billable_days=30 → 500,000
    2. 15-apreldan: billable_days=16 (15..30) → (16/30)*500,000 = 266,666.67
    3. 5 kun ta'til (PRORATE_DAYS): billable_days=25 → 416,666.67
    4. 15-apreldan + 5 kun ta'til: billable_days=11 → 183,333.33
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


class MonthlyProratedDaysStrategy(BaseBillingStrategy):
    mode = BillingProfile.Mode.MONTHLY_PRORATED_DAYS

    def calculate(self, ctx: InvoiceContext) -> CalculationResult:
        period_start, period_end = month_bounds(ctx.period_year, ctx.period_month)
        total_days = days_in_range(period_start, period_end)

        # Effective start: enrollmentdan keyingi sana
        effective_start = max(period_start, ctx.enrollment_date)
        if effective_start > period_end:
            # O'quvchi bu oyda hali qo'shilmagan
            return CalculationResult(
                period_start=period_start,
                period_end=period_end,
                billable_days=0,
                total_period_days=total_days,
            )

        gross_billable_days = days_in_range(effective_start, period_end)
        base_price = Decimal(ctx.base_price or 0)
        per_day = base_price / Decimal(total_days) if total_days else Decimal("0")

        # Asosiy summa (enrollmentdan keyingi kunlar uchun)
        base_amount = per_day * Decimal(gross_billable_days)

        result = CalculationResult(
            period_start=period_start,
            period_end=period_end,
            base_amount=base_amount,
            billable_days=gross_billable_days,
            total_period_days=total_days,
        )

        # Asosiy qator
        if gross_billable_days == total_days:
            base_desc = f"{ctx.period_month:02d}/{ctx.period_year} to'liq oylik"
        else:
            base_desc = (
                f"{ctx.period_month:02d}/{ctx.period_year} pro-rate "
                f"({gross_billable_days}/{total_days} kun)"
            )
        result.lines.append(dict(
            kind=InvoiceLine.Kind.BASE,
            description=base_desc,
            amount=quantize(base_amount),
        ))

        # Ta'tilni qo'llash (faqat PRORATE_DAYS uchun)
        if self.profile.leave_policy == BillingProfile.LeavePolicy.PRORATE_DAYS:
            self._apply_leaves(ctx, result, effective_start, period_end, per_day)

        # billable_days = leavedan keyin ham qoladigan kunlar
        result.billable_days = gross_billable_days - self._total_leave_days(
            ctx, result, effective_start, period_end
        )
        if result.billable_days < 0:
            result.billable_days = 0

        return result

    # ---- internal helpers ----

    def _apply_leaves(self, ctx, result, eff_start, eff_end, per_day):
        for leave in ctx.leaves or []:
            if leave.status != StudentLeave.Status.APPROVED:
                continue
            days = overlap_days(eff_start, eff_end, leave.start_date, leave.end_date)
            if days < self.profile.min_leave_days:
                continue
            if self.profile.max_leave_days_per_month:
                days = min(days, self.profile.max_leave_days_per_month)
            credit = per_day * Decimal(days)
            result.leave_credit_amount += credit
            result.lines.append(dict(
                kind=InvoiceLine.Kind.LEAVE_CREDIT,
                description=f"Ta'til chegirmasi ({days} kun)",
                amount=quantize(credit),
                leave=leave,
            ))

    def _total_leave_days(self, ctx, result, eff_start, eff_end) -> int:
        if self.profile.leave_policy != BillingProfile.LeavePolicy.PRORATE_DAYS:
            return 0
        total = 0
        for leave in ctx.leaves or []:
            if leave.status != StudentLeave.Status.APPROVED:
                continue
            days = overlap_days(eff_start, eff_end, leave.start_date, leave.end_date)
            if days < self.profile.min_leave_days:
                continue
            if self.profile.max_leave_days_per_month:
                days = min(days, self.profile.max_leave_days_per_month)
            total += days
        return total
