"""
Edvora - Notification Celery Tasks
Avtomatik SMS yuborish
"""

import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_debt_reminder_sms(self):
    """
    Qarzdor o'quvchilarga SMS eslatma yuborish.
    Har kuni ertalab ishlaydi.
    """
    from apps.notifications.models import AutoSMS, Notification, NotificationLog
    from apps.students.models import Student
    from core.utils.sms import sms_service
    from datetime import timedelta

    try:
        auto_sms = AutoSMS.objects.get(trigger='debt_reminder', is_active=True)
    except AutoSMS.DoesNotExist:
        logger.info("Qarz eslatmasi Auto-SMS faol emas yoki mavjud emas")
        return {'sent': 0, 'reason': 'trigger not active'}

    debtors = Student.objects.filter(
        status='active',
        balance__lt=0,
        phone__isnull=False,
    ).exclude(phone='')

    # Oxirgi 3 kunda SMS yuborilganlarni chiqarib tashlash
    recent_sms_students = NotificationLog.objects.filter(
        notification__notification_type='payment_reminder',
        channel='sms',
        status='sent',
        created_at__gte=timezone.now() - timedelta(days=3),
    ).values_list('notification__student_id', flat=True)

    debtors = debtors.exclude(id__in=recent_sms_students)

    sent = 0
    for student in debtors:
        message = auto_sms.render_message({
            'student_name': student.full_name,
            'amount': f"{abs(student.balance):,.0f}",
        })

        notification = Notification.objects.create(
            student=student,
            title="Qarz eslatmasi",
            message=message,
            notification_type='payment_reminder',
            channel='sms',
        )

        result = sms_service.send_sms(student.phone, message)

        NotificationLog.objects.create(
            notification=notification,
            channel='sms',
            status='sent' if result['success'] else 'failed',
            external_id=result.get('message_id'),
            error_message=result.get('error'),
        )

        if result['success']:
            notification.is_sent = True
            notification.sent_at = timezone.now()
            notification.save(update_fields=['is_sent', 'sent_at'])
            sent += 1

    logger.info(f"Qarz eslatma SMS: {sent} ta yuborildi")
    return {'sent': sent}


@shared_task(bind=True, max_retries=3)
def send_birthday_sms(self):
    """
    Tug'ilgan kun tabrigini SMS bilan yuborish.
    Har kuni ertalab ishlaydi.
    """
    from apps.notifications.models import AutoSMS, Notification, NotificationLog
    from apps.students.models import Student
    from core.utils.sms import sms_service

    try:
        auto_sms = AutoSMS.objects.get(trigger='birthday', is_active=True)
    except AutoSMS.DoesNotExist:
        return {'sent': 0, 'reason': 'trigger not active'}

    today = timezone.now().date()

    birthday_students = Student.objects.filter(
        status='active',
        birth_date__month=today.month,
        birth_date__day=today.day,
        phone__isnull=False,
    ).exclude(phone='')

    sent = 0
    for student in birthday_students:
        message = auto_sms.render_message({
            'student_name': student.full_name,
        })

        notification = Notification.objects.create(
            student=student,
            title="Tug'ilgan kun tabrigi",
            message=message,
            notification_type='marketing',
            channel='sms',
        )

        result = sms_service.send_sms(student.phone, message)

        NotificationLog.objects.create(
            notification=notification,
            channel='sms',
            status='sent' if result['success'] else 'failed',
            external_id=result.get('message_id'),
            error_message=result.get('error'),
        )

        if result['success']:
            notification.is_sent = True
            notification.sent_at = timezone.now()
            notification.save(update_fields=['is_sent', 'sent_at'])
            sent += 1

    logger.info(f"Tug'ilgan kun SMS: {sent} ta yuborildi")
    return {'sent': sent}


@shared_task(bind=True, max_retries=3)
def process_reminders(self):
    """
    Vaqti kelgan eslatmalarni notification sifatida yuborish.
    Har 15 daqiqada ishlaydi.
    """
    from apps.notifications.models import Reminder, Notification

    now = timezone.now()

    due_reminders = Reminder.objects.filter(
        is_completed=False,
        is_notified=False,
        remind_at__lte=now,
    ).select_related('created_by')

    notified = 0
    for reminder in due_reminders:
        Notification.objects.create(
            user=reminder.created_by,
            title=f"Eslatma: {reminder.title}",
            message=reminder.description or reminder.title,
            notification_type='system',
            channel='in_app',
            priority=reminder.priority,
        )
        reminder.is_notified = True
        reminder.save(update_fields=['is_notified'])
        notified += 1

    logger.info(f"Eslatmalar: {notified} ta notification yuborildi")
    return {'notified': notified}


def send_event_sms(trigger_name, student, context):
    """
    Hodisa bo'lganda SMS yuborish (sinxron helper).
    to'lov qabul qilinganda, guruhga qo'shilganda va h.k. ishlatiladi.
    """
    from apps.notifications.models import AutoSMS, Notification, NotificationLog
    from core.utils.sms import sms_service

    try:
        auto_sms = AutoSMS.objects.get(trigger=trigger_name, is_active=True)
    except AutoSMS.DoesNotExist:
        return None

    if not student.phone:
        return None

    message = auto_sms.render_message(context)

    notification = Notification.objects.create(
        student=student,
        title=auto_sms.name,
        message=message,
        notification_type='system',
        channel='sms',
    )

    result = sms_service.send_sms(student.phone, message)

    NotificationLog.objects.create(
        notification=notification,
        channel='sms',
        status='sent' if result['success'] else 'failed',
        external_id=result.get('message_id'),
        error_message=result.get('error'),
    )

    if result['success']:
        notification.is_sent = True
        notification.sent_at = timezone.now()
        notification.save(update_fields=['is_sent', 'sent_at'])

    return result
