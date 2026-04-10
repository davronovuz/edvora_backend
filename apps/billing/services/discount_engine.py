"""
Edvora - Discount Engine

Invoice yaratilgandan keyin chegirmalarni qo'llaydi.
Hammasi transparent: har bir chegirma InvoiceLine sifatida yoziladi.

Oqim:
    1. Barcha mos chegirmalarni yig'adi (student, group, course, branch + auto-detect)
    2. Stackable qoidasi bo'yicha saralaydi
    3. Har birini Invoice'ga qo'llaydi

Auto-detect turlari:
    - SIBLING: parent_phone bo'yicha boshqa faol o'quvchilarni topish
    - MULTI_COURSE: bitta o'quvchi nechta faol guruhda o'qishi
    - LOYALTY: necha oydan beri o'qiyotgani
    - FIRST_MONTH: birinchi oylik invoice ekanligini tekshirish
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from django.db.models import Q
from django.utils import timezone

from apps.billing.models import Discount, Invoice, InvoiceLine


class DiscountEngine:
    """
    Invoice ga tegishli barcha chegirmalarni qo'llaydi.
    """

    def apply(
        self,
        invoice: Invoice,
        promo_code: Optional[str] = None,
    ) -> list[InvoiceLine]:
        """
        Invoice'ga barcha mos chegirmalarni qo'llaydi.
        Qaytaradi: yaratilgan InvoiceLine'lar ro'yxati.
        """
        gs = invoice.group_student
        student = invoice.student
        group = invoice.group
        today = timezone.now().date()

        # 1. Barcha potensial chegirmalarni to'playdi
        candidates = self._collect_candidates(student, group, today, promo_code)

        # 2. Mos kelmaganlarni filtrdan o'tkazadi
        eligible = self._filter_eligible(candidates, invoice, gs)

        # 3. Stackable qoidasi
        final = self._resolve_stacking(eligible)

        # 4. Qo'llash
        return self._apply_discounts(invoice, final)

    # ---- 1. To'plash ----

    def _collect_candidates(self, student, group, today, promo_code):
        """Barcha potensial chegirmalarni DB dan oladi."""
        q = Q(is_active=True)
        q &= Q(start_date__lte=today)
        q &= Q(Q(end_date__isnull=True) | Q(end_date__gte=today))

        # Maqsad filteri (OR — har qanday biri mos kelsa)
        target_q = Q(student=student) | Q(group=group)
        if group.course_id:
            target_q |= Q(course_id=group.course_id)
        if group.branch_id:
            target_q |= Q(branch_id=group.branch_id)
        # Global (hech qaysi target belgilanmagan)
        target_q |= Q(
            student__isnull=True,
            group__isnull=True,
            course__isnull=True,
            branch__isnull=True,
        )

        q &= target_q

        # Promo kod
        if promo_code:
            # Promo kodni alohida oladi, keyin boshqalar bilan birlashtiradi
            promo_q = Q(code=promo_code, is_active=True)
            return list(
                Discount.objects.filter(q)
                | Discount.objects.filter(promo_q)
            )

        return list(Discount.objects.filter(q).exclude(kind=Discount.Kind.PROMO_CODE))

    # ---- 2. Filtr ----

    def _filter_eligible(self, candidates, invoice, gs):
        """Shartlarga mos kelmaganlarni chiqarib tashlaydi."""
        result = []
        for d in candidates:
            if not d.is_usable:
                continue
            # FIRST_MONTH: birinchi invoice ekanligini tekshirish
            if d.applies_to_first_month_only or d.kind == Discount.Kind.FIRST_MONTH:
                prior = Invoice.objects.filter(
                    group_student=gs,
                ).exclude(pk=invoice.pk).exists()
                if prior:
                    continue

            # LOYALTY: min_months tekshirish
            if d.kind == Discount.Kind.LOYALTY and d.min_months:
                months_enrolled = self._months_enrolled(gs)
                if months_enrolled < d.min_months:
                    continue

            # Max uses
            if d.max_uses is not None and d.uses_count >= d.max_uses:
                continue

            result.append(d)
        return result

    # ---- 3. Stacking ----

    def _resolve_stacking(self, eligible):
        """
        Stackable bo'lmaganlar orasidan eng yuqori priority tanlaydi.
        Stackable bo'lganlar hammasi qo'llanadi.
        """
        if not eligible:
            return []

        stackable = [d for d in eligible if d.stackable]
        non_stackable = [d for d in eligible if not d.stackable]

        result = list(stackable)

        if non_stackable:
            # Eng yuqori priority
            non_stackable.sort(key=lambda d: d.priority, reverse=True)
            result.append(non_stackable[0])

        return result

    # ---- 4. Qo'llash ----

    def _apply_discounts(self, invoice, discounts) -> list[InvoiceLine]:
        """Har bir chegirmani Invoice'ga yozadi va summalarni yangilaydi."""
        lines = []
        total_discount = Decimal("0")
        base = invoice.base_amount

        for d in discounts:
            amount = d.calculate(base)
            if amount <= 0:
                continue

            line = InvoiceLine.objects.create(
                invoice=invoice,
                kind=InvoiceLine.Kind.DISCOUNT,
                description=str(d),
                amount=amount,
                discount=d,
            )
            lines.append(line)
            total_discount += amount

            # uses_count increment
            d.uses_count += 1
            d.save(update_fields=['uses_count', 'updated_at'])

        # Invoice summalarini yangilash
        if total_discount > 0:
            invoice.discount_amount = total_discount
            invoice.save(update_fields=['discount_amount', 'total_amount', 'updated_at'])
            invoice.recompute_status()

        return lines

    # ---- Helpers ----

    @staticmethod
    def _months_enrolled(gs) -> int:
        """GroupStudent necha oydan beri o'qiyotgani."""
        joined = gs.joined_date
        if not joined:
            return 0
        today = date.today()
        return (today.year - joined.year) * 12 + (today.month - joined.month)

    @staticmethod
    def detect_siblings(student) -> list:
        """
        Parent_phone bo'yicha boshqa faol o'quvchilarni topish.
        Qaytaradi: [Student, ...] (o'zidan boshqa)
        """
        from apps.students.models import Student
        if not student.parent_phone:
            return []
        return list(
            Student.objects.filter(
                parent_phone=student.parent_phone,
                status='active',
            ).exclude(pk=student.pk)
        )

    @staticmethod
    def count_active_groups(student) -> int:
        """O'quvchi nechta faol guruhda o'qiyotgani."""
        from apps.groups.models import GroupStudent
        return GroupStudent.objects.filter(
            student=student,
            is_active=True,
            status='active',
        ).count()
