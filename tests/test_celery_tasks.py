"""
Edvora - Celery Tasks Tests
To'lov eslatmalari, invoice yaratish, statistika hisoblash, maosh hisoblash
"""

import pytest
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from apps.payments.models import Payment, Invoice
from apps.payments.tasks import send_payment_reminders, generate_monthly_invoices, mark_overdue_invoices
from apps.analytics.tasks import calculate_daily_stats
from apps.finance.tasks import calculate_monthly_salaries
from apps.groups.models import GroupStudent
from apps.notifications.models import Notification
from apps.finance.models import Salary


pytestmark = pytest.mark.django_db


class TestPaymentReminderTask:
    """To'lov eslatma task testi"""

    def test_send_reminders_to_debtors(self, create_student):
        """Qarzdor o'quvchilarga eslatma yuborish"""
        student = create_student(balance=Decimal('-300000'))

        result = send_payment_reminders()
        assert result['reminders_sent'] == 1

        notification = Notification.objects.filter(
            student=student, notification_type='payment_reminder'
        ).first()
        assert notification is not None
        assert '300,000' in notification.message

    def test_no_reminder_to_non_debtors(self, create_student):
        """Qarzi bo'lmagan o'quvchilarga eslatma yuborilmasligi"""
        create_student(balance=Decimal('100000'))

        result = send_payment_reminders()
        assert result['reminders_sent'] == 0

    def test_no_duplicate_reminders(self, create_student):
        """3 kun ichida ikkinchi eslatma yuborilmasligi"""
        student = create_student(balance=Decimal('-300000'))

        send_payment_reminders()
        result = send_payment_reminders()  # Ikkinchi marta
        assert result['reminders_sent'] == 0


class TestMonthlyInvoiceTask:
    """Oylik invoice yaratish task testi"""

    def test_generate_invoices(self, create_group, create_student):
        """Faol o'quvchilar uchun invoice yaratish"""
        group = create_group()
        student = create_student()
        GroupStudent.objects.create(group=group, student=student)

        result = generate_monthly_invoices()
        assert result['created'] == 1

        invoice = Invoice.objects.filter(student=student).first()
        assert invoice is not None
        assert invoice.status == 'sent'

    def test_no_duplicate_invoices(self, create_group, create_student):
        """Bir oy uchun ikki marta invoice yaratilmasligi"""
        group = create_group()
        student = create_student()
        GroupStudent.objects.create(group=group, student=student)

        generate_monthly_invoices()
        result = generate_monthly_invoices()  # Ikkinchi marta
        assert result['created'] == 0
        assert result['skipped'] == 1


class TestMarkOverdueInvoicesTask:
    """Muddati o'tgan invoicelarni belgilash"""

    def test_mark_overdue(self, create_student, create_group):
        """Muddati o'tgan invoiceni overdue qilish"""
        student = create_student()
        group = create_group()

        from core.utils.helpers import generate_invoice_number
        Invoice.objects.create(
            student=student,
            group=group,
            invoice_number=generate_invoice_number('INV'),
            period_month=1, period_year=2024,
            amount=500000, total=500000,
            due_date=timezone.now().date() - timedelta(days=5),
            status='sent',
        )

        result = mark_overdue_invoices()
        assert result['overdue_marked'] == 1


class TestDailyStatsTask:
    """Kunlik statistika hisoblash"""

    def test_calculate_daily(self, create_student):
        """Kunlik statistikani hisoblash"""
        create_student()

        result = calculate_daily_stats()
        assert result['date'] == str(timezone.now().date())

        from apps.analytics.models import DailyStats
        stats = DailyStats.objects.filter(date=timezone.now().date()).first()
        assert stats is not None
        assert stats.total_students >= 1


class TestSalaryCalculationTask:
    """Maosh hisoblash task testi"""

    def test_calculate_fixed_salary(self, create_teacher, create_group):
        """Fixed maosh hisoblash"""
        teacher = create_teacher(
            salary_type='fixed',
            salary_amount=Decimal('5000000'),
        )
        create_group(teacher=teacher)

        result = calculate_monthly_salaries()
        assert result['created'] == 1

        salary = Salary.objects.filter(teacher=teacher).first()
        assert salary is not None
        assert salary.base_salary == Decimal('5000000')
        assert salary.status == 'calculated'

    def test_no_duplicate_salaries(self, create_teacher, create_group):
        """Bir oy uchun ikki marta maosh hisoblanmasligi"""
        teacher = create_teacher(
            salary_type='fixed',
            salary_amount=Decimal('5000000'),
        )
        create_group(teacher=teacher)

        calculate_monthly_salaries()
        result = calculate_monthly_salaries()
        assert result['created'] == 0
        assert result['skipped'] == 1
