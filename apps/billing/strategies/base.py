"""
Edvora - Base Billing Strategy

Strategy pattern: har bir billing mode uchun alohida klass.
Hammasi BaseBillingStrategy dan meros oladi va generate(ctx) ni implement qiladi.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, List

from django.db import transaction

from apps.billing.models import (
    BillingProfile,
    Invoice,
    InvoiceLine,
    StudentLeave,
)


@dataclass
class InvoiceContext:
    """
    Invoice generatsiya uchun barcha kirish ma'lumotlari.
    Strategy klasslari faqat shu konteks bilan ishlaydi —
    boshqa hech narsa qabul qilmaydi.
    """
    group_student: "object"  # apps.groups.models.GroupStudent
    profile: BillingProfile
    period_year: int
    period_month: int

    # Override-able defaults (test va maxsus hollar uchun)
    enrollment_date: Optional[date] = None
    leaves: Optional[List[StudentLeave]] = None
    base_price: Optional[Decimal] = None
    issue_date: Optional[date] = None
    note: Optional[str] = None

    def __post_init__(self):
        if self.enrollment_date is None:
            self.enrollment_date = self.group_student.joined_date
        if self.base_price is None:
            self.base_price = Decimal(self.group_student.monthly_price or 0)
        if self.leaves is None:
            self.leaves = list(
                StudentLeave.objects.filter(
                    group_student=self.group_student,
                    status=StudentLeave.Status.APPROVED,
                )
            )
        if self.issue_date is None:
            self.issue_date = date.today()


@dataclass
class CalculationResult:
    """
    Strategy ichki hisob-kitob natijasi.
    generate() shu asosida Invoice yaratadi.
    """
    period_start: date
    period_end: date
    base_amount: Decimal = Decimal("0")
    leave_credit_amount: Decimal = Decimal("0")
    extra_amount: Decimal = Decimal("0")
    billable_days: int = 0
    total_period_days: int = 0
    billable_lessons: int = 0
    total_period_lessons: int = 0
    lines: List[dict] = field(default_factory=list)


# =============================================================================
# Helpers
# =============================================================================

def month_bounds(year: int, month: int) -> tuple[date, date]:
    """Berilgan oyning birinchi va oxirgi sanalari."""
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def days_in_range(start: date, end: date) -> int:
    """Inklusiv kunlar soni."""
    if end < start:
        return 0
    return (end - start).days + 1


def overlap_days(a_start: date, a_end: date, b_start: date, b_end: date) -> int:
    """Ikki [start,end] oraliqning kesishish kunlari soni."""
    start = max(a_start, b_start)
    end = min(a_end, b_end)
    return days_in_range(start, end)


def count_lesson_days(start: date, end: date, weekdays: list[int]) -> int:
    """
    Berilgan oraliqdagi guruh dars kunlari soni.
    weekdays: Group.days, masalan [0,2,4] (Monday=0).
    """
    if end < start or not weekdays:
        return 0
    weekday_set = set(weekdays)
    count = 0
    cur = start
    while cur <= end:
        if cur.weekday() in weekday_set:
            count += 1
        cur += timedelta(days=1)
    return count


def quantize(amount: Decimal) -> Decimal:
    return Decimal(amount).quantize(Decimal("0.01"))


# =============================================================================
# Base Strategy
# =============================================================================

class BaseBillingStrategy:
    """
    Barcha billing strategiyalari uchun abstract base.

    Sub-class lar `calculate(ctx)` ni implement qilishi shart;
    `generate(ctx)` esa hammasi uchun umumiy — Invoice + InvoiceLines yaratadi.
    """

    mode: str = ""  # BillingProfile.Mode qiymati

    def __init__(self, profile: BillingProfile):
        self.profile = profile

    # ---- subclasses must implement ----
    def calculate(self, ctx: InvoiceContext) -> CalculationResult:
        raise NotImplementedError

    # ---- shared ----
    def generate(self, ctx: InvoiceContext) -> Invoice:
        """
        Invoice ni atomik yaratadi (Invoice + qatorlar bir tranzaksiyada).
        """
        if ctx.profile is None:
            ctx.profile = self.profile

        result = self.calculate(ctx)

        with transaction.atomic():
            invoice = Invoice(
                student=ctx.group_student.student,
                group=ctx.group_student.group,
                group_student=ctx.group_student,
                billing_profile=self.profile,
                period_year=ctx.period_year,
                period_month=ctx.period_month,
                period_start=result.period_start,
                period_end=result.period_end,
                base_amount=quantize(result.base_amount),
                leave_credit_amount=quantize(result.leave_credit_amount),
                extra_amount=quantize(result.extra_amount),
                billable_days=result.billable_days,
                total_period_days=result.total_period_days,
                billable_lessons=result.billable_lessons,
                total_period_lessons=result.total_period_lessons,
                issue_date=ctx.issue_date,
                due_date=ctx.issue_date + timedelta(days=self.profile.due_days),
                status=Invoice.Status.UNPAID,
                note=ctx.note or "",
            )
            invoice.save()

            # Audit qatorlarini yozish
            for line in result.lines:
                InvoiceLine.objects.create(invoice=invoice, **line)

            # Status ni dastlabki holatga keltirish
            invoice.recompute_status()

        return invoice
