"""
Edvora - Billing Celery Tasks

Avtomatik billing operatsiyalari:
    1. generate_monthly_invoices — har oyning billing_day kunida invoice yaratish
    2. check_overdue_invoices — due_date + grace_period o'tganlarni overdue qilish
    3. apply_late_fees — overdue invoice'larga penya qo'shish
    4. send_due_date_reminders — to'lov muddati yaqinlashganlarni eslatish
"""

import logging
from datetime import date, timedelta
from decimal import Decimal

from celery import shared_task
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

logger = logging.getLogger(__name__)


# =============================================================================
# 1. OYLIK INVOICE GENERATSIYA
# =============================================================================

@shared_task(bind=True, max_retries=3)
def generate_monthly_invoices(self):
    """
    Barcha faol o'quvchilar uchun joriy oy invoice'larini yaratish.

    Billing profile'dagi billing_day asosida ishlaydi:
    - billing_day=1 → har oyning 1-kuni
    - billing_day=15 → har oyning 15-kuni

    Har kuni ishlaydi — faqat billing_day mos kelgandagina yaratadi.
    """
    from apps.billing.models import BillingProfile, Invoice
    from apps.billing.services.invoice_service import InvoiceService
    from apps.groups.models import GroupStudent

    today = timezone.now().date()
    day = today.day
    month = today.month
    year = today.year

    svc = InvoiceService()

    # Faol o'quvchilarni olish
    active_gs = GroupStudent.objects.filter(
        is_active=True,
        status=GroupStudent.Status.ACTIVE,
        group__status='active',
    ).select_related(
        'student', 'group', 'group__course',
        'group__branch', 'billing_profile',
        'group__billing_profile', 'group__course__billing_profile',
    )

    created = 0
    skipped = 0
    errors = 0

    for gs in active_gs:
        try:
            # Billing profile aniqlash
            profile = InvoiceService.resolve_profile(gs)
            if not profile:
                skipped += 1
                continue

            # billing_day tekshirish — faqat bugun billing kuni bo'lsa yaratadi
            if profile.billing_day != day:
                continue

            # Allaqachon yaratilganmi?
            exists = Invoice.objects.filter(
                group_student=gs,
                period_year=year,
                period_month=month,
            ).exclude(status=Invoice.Status.CANCELLED).exists()

            if exists:
                skipped += 1
                continue

            invoice = svc.generate(gs, year, month)
            if invoice:
                created += 1
            else:
                skipped += 1

        except Exception as e:
            logger.error(f"Invoice yaratishda xato: {gs} — {e}", exc_info=True)
            errors += 1

    logger.info(
        f"Oylik invoice generatsiya: {created} yaratildi, "
        f"{skipped} o'tkazib yuborildi, {errors} xato"
    )
    return {
        'created': created,
        'skipped': skipped,
        'errors': errors,
        'date': str(today),
    }


# =============================================================================
# 2. OVERDUE TEKSHIRISH
# =============================================================================

@shared_task(bind=True, max_retries=3)
def check_overdue_invoices(self):
    """
    due_date + grace_period o'tgan invoice'larni OVERDUE qilish.

    Har kuni ishlaydi.
    grace_period_days profile'dan olinadi. Agar profile yo'q — 3 kun default.
    """
    from apps.billing.models import Invoice

    today = timezone.now().date()

    # unpaid yoki partial bo'lgan, due_date o'tgan invoice'lar
    candidates = Invoice.objects.filter(
        status__in=[Invoice.Status.UNPAID, Invoice.Status.PARTIAL],
        due_date__lt=today,
    ).select_related('billing_profile')

    updated = 0
    for inv in candidates:
        grace = 3  # default
        if inv.billing_profile and inv.billing_profile.grace_period_days:
            grace = inv.billing_profile.grace_period_days

        overdue_date = inv.due_date + timedelta(days=grace)
        if today > overdue_date:
            inv.status = Invoice.Status.OVERDUE
            inv.save(update_fields=['status', 'updated_at'])
            updated += 1

    logger.info(f"Overdue tekshirish: {updated} ta invoice overdue qilindi")
    return {'overdue_marked': updated, 'date': str(today)}


# =============================================================================
# 3. PENYA (LATE FEE) QO'SHISH
# =============================================================================

@shared_task(bind=True, max_retries=3)
def apply_late_fees(self):
    """
    Overdue invoice'larga penya qo'shish.

    BillingProfile sozlamalari asosida:
    - late_fee_enabled: yoqilganmi?
    - late_fee_type: percent yoki fixed
    - late_fee_value: foiz yoki summa
    - late_fee_frequency: once, daily, weekly

    Har kuni ishlaydi.
    """
    from apps.billing.models import BillingProfile, Invoice, InvoiceLine

    today = timezone.now().date()

    overdue_invoices = Invoice.objects.filter(
        status=Invoice.Status.OVERDUE,
    ).select_related('billing_profile')

    applied = 0
    skipped = 0

    for inv in overdue_invoices:
        profile = inv.billing_profile
        if not profile or not profile.late_fee_enabled:
            skipped += 1
            continue

        # Chastota tekshirish
        if not _should_apply_fee(inv, profile, today):
            continue

        # Penya hisoblash
        fee = _calculate_late_fee(inv, profile)
        if fee <= 0:
            continue

        with transaction.atomic():
            # InvoiceLine yaratish
            days_overdue = (today - inv.due_date).days
            InvoiceLine.objects.create(
                invoice=inv,
                kind=InvoiceLine.Kind.LATE_FEE,
                description=f"Penya — {days_overdue} kun kechikish ({today})",
                amount=fee,
            )

            # Invoice late_fee_amount yangilash
            inv.late_fee_amount = (inv.late_fee_amount or Decimal('0')) + fee
            inv.save(update_fields=['late_fee_amount', 'updated_at'])
            # total_amount save() da avtomatik hisoblanadi

        applied += 1

    logger.info(f"Late fee: {applied} ta invoice'ga penya qo'shildi, {skipped} o'tkazildi")
    return {'applied': applied, 'skipped': skipped, 'date': str(today)}


def _should_apply_fee(invoice, profile, today):
    """Chastota bo'yicha penya qo'shish kerakmi."""
    from apps.billing.models import InvoiceLine

    freq = profile.late_fee_frequency

    # Oxirgi penya qachon qo'shilgan?
    last_fee = InvoiceLine.objects.filter(
        invoice=invoice,
        kind=InvoiceLine.Kind.LATE_FEE,
    ).order_by('-created_at').first()

    if freq == 'once':
        # Faqat bir marta — agar allaqachon bor bo'lsa, o'tkazib yubor
        return last_fee is None

    if freq == 'daily':
        if last_fee is None:
            return True
        return last_fee.created_at.date() < today

    if freq == 'weekly':
        if last_fee is None:
            return True
        return (today - last_fee.created_at.date()).days >= 7

    return False


def _calculate_late_fee(invoice, profile):
    """Penya summasini hisoblash."""
    if profile.late_fee_type == 'percent':
        # base_amount dan foiz (total emas, compound bo'lmasligi uchun)
        return (invoice.base_amount * profile.late_fee_value / Decimal('100')).quantize(Decimal('0.01'))
    else:
        # Fixed summa
        return profile.late_fee_value


# =============================================================================
# 4. TO'LOV MUDDATI ESLATMASI
# =============================================================================

@shared_task(bind=True, max_retries=3)
def send_due_date_reminders(self):
    """
    To'lov muddati yaqinlashgan (3 kun qolgan) invoice egalariga eslatma.

    Har kuni ishlaydi.
    """
    from apps.billing.models import Invoice
    from apps.notifications.models import Notification

    today = timezone.now().date()
    reminder_date = today + timedelta(days=3)

    # 3 kun ichida due bo'ladigan, hali to'lanmagan invoice'lar
    upcoming = Invoice.objects.filter(
        status__in=[Invoice.Status.UNPAID, Invoice.Status.PARTIAL],
        due_date=reminder_date,
    ).select_related('student', 'group')

    sent = 0
    for inv in upcoming:
        # Oxirgi 2 kunda eslatma yuborilganmi?
        recent = Notification.objects.filter(
            student=inv.student,
            notification_type='payment_reminder',
            created_at__gte=timezone.now() - timedelta(days=2),
        ).exists()

        if recent:
            continue

        remaining = inv.remaining
        Notification.objects.create(
            student=inv.student,
            title="To'lov muddati yaqinlashmoqda",
            message=(
                f"Hurmatli {inv.student.full_name}, "
                f"{inv.group.name} guruhi uchun {remaining:,.0f} so'm "
                f"to'lov muddati {inv.due_date.strftime('%d.%m.%Y')}. "
                f"Iltimos, o'z vaqtida to'lang."
            ),
            notification_type='payment_reminder',
            channel='in_app',
            priority='high',
        )
        sent += 1

    logger.info(f"Due date eslatmalari: {sent} ta yuborildi")
    return {'reminders_sent': sent, 'date': str(today)}
