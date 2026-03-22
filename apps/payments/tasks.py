"""
Edvora - Payment Celery Tasks
To'lov eslatmalari, invoice yaratish, muddati o'tganlarni belgilash
"""

import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_payment_reminders(self):
    """
    Qarzdor o'quvchilarga to'lov eslatmasi yuborish.
    Har kuni ertalab 09:00 da ishlaydi.
    """
    from apps.students.models import Student
    from apps.notifications.models import Notification

    debtors = Student.objects.filter(
        status='active',
        balance__lt=0,
    )

    count = 0
    for student in debtors:
        # Oxirgi 3 kunda eslatma yuborilganmi tekshirish
        recent = Notification.objects.filter(
            student=student,
            notification_type='payment_reminder',
            created_at__gte=timezone.now() - timedelta(days=3),
        ).exists()

        if not recent:
            Notification.objects.create(
                student=student,
                title="To'lov eslatmasi",
                message=f"Hurmatli {student.full_name}, sizning {abs(student.balance):,.0f} so'm qarzingiz bor. Iltimos, to'lovni amalga oshiring.",
                notification_type='payment_reminder',
                channel='in_app',
                priority='high',
            )
            count += 1

    logger.info(f"To'lov eslatmalari yuborildi: {count} ta o'quvchi")
    return {'reminders_sent': count}


@shared_task(bind=True, max_retries=3)
def generate_monthly_invoices(self):
    """
    Faol guruhlardagi o'quvchilar uchun oylik invoice yaratish.
    Har oyning 1-kuni ishlaydi.
    """
    from apps.groups.models import GroupStudent
    from apps.payments.models import Invoice
    from core.utils.helpers import generate_invoice_number

    now = timezone.now()
    month = now.month
    year = now.year

    active_enrollments = GroupStudent.objects.filter(
        is_active=True,
        status='active',
        group__status='active',
    ).select_related('group', 'student', 'group__course')

    created_count = 0
    skipped_count = 0

    for enrollment in active_enrollments:
        # Bu oy uchun invoice bormi?
        exists = Invoice.objects.filter(
            student=enrollment.student,
            group=enrollment.group,
            period_month=month,
            period_year=year,
        ).exists()

        if exists:
            skipped_count += 1
            continue

        amount = enrollment.monthly_price
        due_date = now.replace(day=10).date()  # Har oyning 10-kunigacha

        Invoice.objects.create(
            student=enrollment.student,
            group=enrollment.group,
            invoice_number=generate_invoice_number('INV'),
            period_month=month,
            period_year=year,
            amount=amount,
            discount=0,
            total=amount,
            due_date=due_date,
            status='sent',
        )
        created_count += 1

    logger.info(f"Oylik invoicelar: {created_count} yaratildi, {skipped_count} o'tkazib yuborildi")
    return {'created': created_count, 'skipped': skipped_count}


@shared_task(bind=True, max_retries=3)
def process_monthly_write_offs(self):
    """
    Oylik to'lovni avtomatik yechib olish.
    Har kuni ishlaydi - next_write_off_date <= bugun bo'lganlarni qayta ishlaydi.

    Logika:
    1. Faol GroupStudent lardan next_write_off_date <= bugun bo'lganlarni topish
    2. monthly_price ni GroupStudent.balance va Student.balance dan ayirish
    3. WriteOff log yaratish
    4. next_write_off_date ni keyingi oyga o'tkazish
    """
    from apps.groups.models import GroupStudent
    from apps.payments.models import WriteOff
    from dateutil.relativedelta import relativedelta

    today = timezone.now().date()
    month = today.month
    year = today.year

    enrollments = GroupStudent.objects.filter(
        is_active=True,
        status='active',
        group__status='active',
        next_write_off_date__lte=today,
    ).select_related('group', 'group__course', 'student')

    processed = 0
    skipped = 0
    errors = 0

    for gs in enrollments:
        try:
            # Bu oy uchun allaqachon yechib olinganmi?
            wo_month = gs.next_write_off_date.month
            wo_year = gs.next_write_off_date.year

            already_done = WriteOff.objects.filter(
                group_student=gs,
                period_month=wo_month,
                period_year=wo_year,
            ).exists()

            if already_done:
                # next_write_off_date ni yangilash
                gs.next_write_off_date = gs.next_write_off_date + relativedelta(months=1)
                gs.save(update_fields=['next_write_off_date'])
                skipped += 1
                continue

            amount = gs.monthly_price
            if amount <= 0:
                skipped += 1
                continue

            balance_before = gs.balance

            # GroupStudent balansdan yechish
            gs.balance -= amount
            gs.last_write_off_date = today
            gs.next_write_off_date = gs.next_write_off_date + relativedelta(months=1)
            gs.save(update_fields=['balance', 'last_write_off_date', 'next_write_off_date'])

            # Student balansdan ham yechish
            gs.student.balance -= amount
            gs.student.save(update_fields=['balance'])

            # WriteOff log
            WriteOff.objects.create(
                student=gs.student,
                group=gs.group,
                group_student=gs,
                amount=amount,
                period_month=wo_month,
                period_year=wo_year,
                balance_before=balance_before,
                balance_after=gs.balance,
            )

            processed += 1

        except Exception as e:
            logger.error(f"Write-off xato: {gs} - {e}")
            errors += 1

    logger.info(f"Write-off: {processed} qayta ishlandi, {skipped} o'tkazib yuborildi, {errors} xato")
    return {'processed': processed, 'skipped': skipped, 'errors': errors}


@shared_task(bind=True, max_retries=3)
def mark_overdue_invoices(self):
    """
    Muddati o'tgan invoicelarni overdue deb belgilash.
    Har kuni ishlaydi.
    """
    from apps.payments.models import Invoice

    today = timezone.now().date()

    updated = Invoice.objects.filter(
        status__in=['sent', 'partial'],
        due_date__lt=today,
    ).update(status='overdue')

    logger.info(f"Muddati o'tgan invoicelar: {updated} ta yangilandi")
    return {'overdue_marked': updated}
