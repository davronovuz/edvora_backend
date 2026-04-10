"""
Edvora - Package Strategy

Butun kurs uchun bir martalik to'lov (oylik emas).
Masalan: 6 oylik kurs = 3,000,000. Yoki "kelishilgan summa".

Bu strategy faqat BIR MARTA invoice yaratadi (birinchi marta chaqirilganda).
Keyingi safar bo'sh natija qaytaradi (allaqachon bor).

Period: kurs boshlangan oydan oxirigacha.
Summa manbai (priority bo'yicha):
    1. ctx.base_price (override)
    2. group_student.custom_price
    3. course.price (kurs umumiy narxi)
"""

from decimal import Decimal

from apps.billing.models import BillingProfile, Invoice, InvoiceLine

from .base import (
    BaseBillingStrategy,
    CalculationResult,
    InvoiceContext,
    days_in_range,
    month_bounds,
    quantize,
)


class PackageStrategy(BaseBillingStrategy):
    mode = BillingProfile.Mode.PACKAGE

    def calculate(self, ctx: InvoiceContext) -> CalculationResult:
        period_start, period_end = month_bounds(ctx.period_year, ctx.period_month)

        # Bu group_student uchun PACKAGE invoice borligini tekshirish
        already_invoiced = Invoice.objects.filter(
            group_student=ctx.group_student,
            billing_profile__mode=BillingProfile.Mode.PACKAGE,
        ).exists()

        if already_invoiced:
            # Bo'sh natija — Invoice yaratilmasin
            return CalculationResult(
                period_start=period_start,
                period_end=period_end,
                total_period_days=days_in_range(period_start, period_end),
            )

        # Narx aniqlash
        group = ctx.group_student.group
        course = group.course

        if ctx.base_price and ctx.base_price > 0:
            amount = Decimal(ctx.base_price)
        elif ctx.group_student.custom_price:
            amount = Decimal(ctx.group_student.custom_price)
        else:
            amount = Decimal(course.price or 0)

        # Davr: kurs boshidan tugashigacha (yoki guruh start/end)
        pkg_start = group.start_date or period_start
        pkg_end = group.end_date or period_end

        result = CalculationResult(
            period_start=pkg_start,
            period_end=pkg_end,
            base_amount=amount,
            billable_days=days_in_range(pkg_start, pkg_end),
            total_period_days=days_in_range(pkg_start, pkg_end),
        )
        result.lines.append(dict(
            kind=InvoiceLine.Kind.BASE,
            description=f"{course.name} — to'liq paket",
            amount=quantize(amount),
        ))
        return result

    def generate(self, ctx: InvoiceContext):
        """
        Override: agar package allaqachon yaratilgan bo'lsa, None qaytar.
        """
        result = self.calculate(ctx)
        if result.base_amount == 0 and not result.lines:
            # Allaqachon mavjud
            return None
        return super().generate(ctx)
