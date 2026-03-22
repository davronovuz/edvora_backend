"""
Edvora - Celery Configuration
"""

import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')

app = Celery('edvora')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Beat Schedule - avtomatik ishlaydigan tasklar
app.conf.beat_schedule = {
    # Har kuni ertalab 09:00 da to'lov eslatmalari
    'send-payment-reminders': {
        'task': 'apps.payments.tasks.send_payment_reminders',
        'schedule': crontab(hour=9, minute=0),
    },
    # Har kuni kechqurun 23:00 da kunlik statistika
    'calculate-daily-stats': {
        'task': 'apps.analytics.tasks.calculate_daily_stats',
        'schedule': crontab(hour=23, minute=0),
    },
    # Har oyning 1-kuni oylik statistika
    'calculate-monthly-stats': {
        'task': 'apps.analytics.tasks.calculate_monthly_stats',
        'schedule': crontab(day_of_month=1, hour=1, minute=0),
    },
    # Har oyning 1-kuni oylik invoicelar yaratish
    'generate-monthly-invoices': {
        'task': 'apps.payments.tasks.generate_monthly_invoices',
        'schedule': crontab(day_of_month=1, hour=8, minute=0),
    },
    # Har oyning 25-kuni maoshlarni hisoblash
    'calculate-salaries': {
        'task': 'apps.finance.tasks.calculate_monthly_salaries',
        'schedule': crontab(day_of_month=25, hour=10, minute=0),
    },
    # Har kuni oylik write-off (to'lovni yechib olish)
    'process-monthly-write-offs': {
        'task': 'apps.payments.tasks.process_monthly_write_offs',
        'schedule': crontab(hour=7, minute=0),
    },
    # Har kuni qarzdorlarga SMS eslatma
    'send-debt-reminder-sms': {
        'task': 'apps.notifications.tasks.send_debt_reminder_sms',
        'schedule': crontab(hour=10, minute=0),
    },
    # Har kuni tug'ilgan kun tabrigi
    'send-birthday-sms': {
        'task': 'apps.notifications.tasks.send_birthday_sms',
        'schedule': crontab(hour=9, minute=30),
    },
    # Har 15 daqiqada eslatmalarni tekshirish
    'process-reminders': {
        'task': 'apps.notifications.tasks.process_reminders',
        'schedule': crontab(minute='*/15'),
    },
    # Har kuni muddati o'tgan invoicelarni belgilash
    'mark-overdue-invoices': {
        'task': 'apps.payments.tasks.mark_overdue_invoices',
        'schedule': crontab(hour=0, minute=30),
    },
}
