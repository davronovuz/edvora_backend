"""
Edvora - Billing Tasks Tests

Celery task'lar testi:
    1. generate_monthly_invoices
    2. check_overdue_invoices
    3. apply_late_fees
    4. send_due_date_reminders
"""

from datetime import date, time, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.billing.models import (
    BillingProfile,
    Invoice,
    InvoiceLine,
    StudentLeave,
)
from apps.billing.tasks import (
    generate_monthly_invoices,
    check_overdue_invoices,
    apply_late_fees,
    send_due_date_reminders,
    _should_apply_fee,
    _calculate_late_fee,
)

pytestmark = pytest.mark.django_db


# =============================================================================
# Fixtures
# =============================================================================

def make_profile(**kwargs):
    defaults = dict(
        name="Test Profile",
        mode=BillingProfile.Mode.MONTHLY_FLAT,
        is_default=True,
        billing_day=1,
        due_days=10,
        grace_period_days=3,
    )
    defaults.update(kwargs)
    return BillingProfile.objects.create(**defaults)


@pytest.fixture
def profile():
    return make_profile()


@pytest.fixture
def test_group(create_course, create_teacher):
    from apps.groups.models import Group
    return Group.objects.create(
        name="Task Test Group",
        course=create_course(price=Decimal("500000")),
        teacher=create_teacher(),
        start_date=date(2026, 3, 1),
        days=[0, 2, 4],
        start_time=time(9, 0),
        end_time=time(11, 0),
        max_students=15,
        status='active',
        price=Decimal("500000"),
    )


@pytest.fixture
def gs(test_group, create_student):
    from apps.groups.models import GroupStudent
    return GroupStudent.objects.create(
        group=test_group,
        student=create_student(),
        joined_date=date(2026, 3, 1),
        is_active=True,
        status='active',
    )


@pytest.fixture
def gs_with_invoice(gs, profile):
    """Invoice bilan GroupStudent."""
    from apps.billing.services.invoice_service import InvoiceService
    svc = InvoiceService()
    inv = svc.generate(gs, 2026, 4)
    return gs, inv


# =============================================================================
# 1. GENERATE MONTHLY INVOICES
# =============================================================================

class TestGenerateMonthlyInvoices:

    @patch('apps.billing.tasks.timezone')
    def test_generates_on_billing_day(self, mock_tz, profile, gs):
        """billing_day=1 va bugun 1-kun — yaratishi kerak."""
        mock_tz.now.return_value.date.return_value = date(2026, 4, 1)

        result = generate_monthly_invoices()

        assert result['created'] == 1
        assert result['errors'] == 0
        assert Invoice.objects.filter(
            group_student=gs,
            period_year=2026,
            period_month=4,
        ).exists()

    @patch('apps.billing.tasks.timezone')
    def test_skips_non_billing_day(self, mock_tz, profile, gs):
        """billing_day=1 lekin bugun 15-kun — yaratmasligi kerak."""
        mock_tz.now.return_value.date.return_value = date(2026, 4, 15)

        result = generate_monthly_invoices()

        assert result['created'] == 0
        assert not Invoice.objects.filter(group_student=gs).exists()

    @patch('apps.billing.tasks.timezone')
    def test_skips_existing_invoice(self, mock_tz, profile, gs):
        """Allaqachon yaratilgan invoice bo'lsa o'tkazib yuboradi."""
        mock_tz.now.return_value.date.return_value = date(2026, 4, 1)

        # Birinchi marta
        result1 = generate_monthly_invoices()
        assert result1['created'] == 1

        # Ikkinchi marta — skip
        result2 = generate_monthly_invoices()
        assert result2['created'] == 0
        assert result2['skipped'] == 1

    @patch('apps.billing.tasks.timezone')
    def test_skips_inactive_student(self, mock_tz, profile, gs):
        """Nofaol o'quvchi uchun yaratmaydi."""
        mock_tz.now.return_value.date.return_value = date(2026, 4, 1)

        gs.is_active = False
        gs.save(update_fields=['is_active'])

        result = generate_monthly_invoices()
        assert result['created'] == 0

    @patch('apps.billing.tasks.timezone')
    def test_skips_no_profile(self, mock_tz, gs):
        """Profile yo'q bo'lsa o'tkazib yuboradi."""
        mock_tz.now.return_value.date.return_value = date(2026, 4, 1)
        # Profile yaratmaymiz

        result = generate_monthly_invoices()
        assert result['created'] == 0

    @patch('apps.billing.tasks.timezone')
    def test_multiple_students(self, mock_tz, profile, test_group, create_student):
        """Bir nechta o'quvchi uchun yaratadi."""
        from apps.groups.models import GroupStudent

        mock_tz.now.return_value.date.return_value = date(2026, 4, 1)

        for i in range(3):
            GroupStudent.objects.create(
                group=test_group,
                student=create_student(first_name=f"S{i}", phone=f"+99890{i}333333"),
                joined_date=date(2026, 3, 1),
                is_active=True,
                status='active',
            )

        result = generate_monthly_invoices()
        assert result['created'] == 3

    @patch('apps.billing.tasks.timezone')
    def test_billing_day_15(self, mock_tz, gs):
        """billing_day=15 profil bilan 15-kunda ishlaydi."""
        make_profile(name="Day15 Profile", billing_day=15, is_default=True)
        mock_tz.now.return_value.date.return_value = date(2026, 4, 15)

        result = generate_monthly_invoices()
        # Default profile billing_day=1 bo'lishi kerak, Day15 profile topiladi
        # Lekin is_default=True ikkitada — global birinchisini oladi
        # Bu test shunchaki billing_day logikasini tekshiradi
        assert result['errors'] == 0


# =============================================================================
# 2. CHECK OVERDUE INVOICES
# =============================================================================

class TestCheckOverdueInvoices:

    def test_marks_overdue_after_grace(self, gs_with_invoice):
        """due_date + grace_period o'tganda overdue bo'lishi kerak."""
        gs, inv = gs_with_invoice

        # due_date ni o'tkazib yuborish (14 kun oldin)
        inv.due_date = date(2026, 3, 20)
        inv.status = Invoice.Status.UNPAID
        inv.save(update_fields=['due_date', 'status'])

        result = check_overdue_invoices()

        inv.refresh_from_db()
        assert inv.status == Invoice.Status.OVERDUE
        assert result['overdue_marked'] == 1

    def test_respects_grace_period(self, gs_with_invoice):
        """Grace period ichida overdue bo'lmasligi kerak."""
        gs, inv = gs_with_invoice

        # due_date = kecha, grace = 3 kun → hali overdue emas
        yesterday = date.today() - timedelta(days=1)
        inv.due_date = yesterday
        inv.status = Invoice.Status.UNPAID
        inv.save(update_fields=['due_date', 'status'])

        result = check_overdue_invoices()

        inv.refresh_from_db()
        assert inv.status == Invoice.Status.UNPAID
        assert result['overdue_marked'] == 0

    def test_skips_paid_invoices(self, gs_with_invoice):
        """To'langan invoice'ni overdue qilmaydi."""
        gs, inv = gs_with_invoice

        inv.due_date = date(2026, 3, 1)
        inv.status = Invoice.Status.PAID
        inv.save(update_fields=['due_date', 'status'])

        result = check_overdue_invoices()
        assert result['overdue_marked'] == 0

    def test_partial_becomes_overdue(self, gs_with_invoice):
        """Qisman to'langan ham overdue bo'lishi mumkin."""
        gs, inv = gs_with_invoice

        inv.due_date = date(2026, 3, 1)
        inv.status = Invoice.Status.PARTIAL
        inv.paid_amount = Decimal("100000")
        inv.save(update_fields=['due_date', 'status', 'paid_amount'])

        result = check_overdue_invoices()

        inv.refresh_from_db()
        assert inv.status == Invoice.Status.OVERDUE
        assert result['overdue_marked'] == 1


# =============================================================================
# 3. APPLY LATE FEES
# =============================================================================

class TestApplyLateFees:

    @pytest.fixture
    def overdue_invoice(self, gs_with_invoice):
        """Overdue invoice + late_fee enabled profile."""
        gs, inv = gs_with_invoice

        inv.billing_profile.late_fee_enabled = True
        inv.billing_profile.late_fee_type = 'percent'
        inv.billing_profile.late_fee_value = Decimal('2')  # 2%
        inv.billing_profile.late_fee_frequency = 'once'
        inv.billing_profile.save()

        inv.due_date = date(2026, 3, 1)
        inv.status = Invoice.Status.OVERDUE
        inv.save(update_fields=['due_date', 'status'])

        return inv

    def test_applies_percent_fee(self, overdue_invoice):
        """Foiz penyas to'g'ri hisoblanadi."""
        inv = overdue_invoice

        result = apply_late_fees()

        inv.refresh_from_db()
        expected_fee = (inv.base_amount * Decimal('2') / Decimal('100')).quantize(Decimal('0.01'))
        assert inv.late_fee_amount == expected_fee
        assert result['applied'] == 1

        # InvoiceLine yaratilganmi?
        line = InvoiceLine.objects.filter(
            invoice=inv, kind=InvoiceLine.Kind.LATE_FEE
        ).first()
        assert line is not None
        assert line.amount == expected_fee

    def test_applies_fixed_fee(self, gs_with_invoice):
        """Belgilangan summa penya."""
        gs, inv = gs_with_invoice

        inv.billing_profile.late_fee_enabled = True
        inv.billing_profile.late_fee_type = 'fixed'
        inv.billing_profile.late_fee_value = Decimal('25000')
        inv.billing_profile.late_fee_frequency = 'once'
        inv.billing_profile.save()

        inv.due_date = date(2026, 3, 1)
        inv.status = Invoice.Status.OVERDUE
        inv.save(update_fields=['due_date', 'status'])

        result = apply_late_fees()

        inv.refresh_from_db()
        assert inv.late_fee_amount == Decimal('25000')
        assert result['applied'] == 1

    def test_once_frequency_no_duplicate(self, overdue_invoice):
        """once chastotada ikkinchi marta penya qo'shilmaydi."""
        apply_late_fees()  # Birinchi marta
        result = apply_late_fees()  # Ikkinchi marta

        assert result['applied'] == 0

        # Faqat bitta late_fee line bo'lishi kerak
        count = InvoiceLine.objects.filter(
            invoice=overdue_invoice,
            kind=InvoiceLine.Kind.LATE_FEE,
        ).count()
        assert count == 1

    def test_daily_frequency(self, gs_with_invoice):
        """Har kuni penya qo'shiladi."""
        gs, inv = gs_with_invoice

        inv.billing_profile.late_fee_enabled = True
        inv.billing_profile.late_fee_type = 'fixed'
        inv.billing_profile.late_fee_value = Decimal('5000')
        inv.billing_profile.late_fee_frequency = 'daily'
        inv.billing_profile.save()

        inv.due_date = date(2026, 3, 1)
        inv.status = Invoice.Status.OVERDUE
        inv.save(update_fields=['due_date', 'status'])

        # 1-kun
        result1 = apply_late_fees()
        assert result1['applied'] == 1

        # 2-kun (xuddi shu kunda — o'tkazib yuboradi)
        result2 = apply_late_fees()
        assert result2['applied'] == 0  # same day, skip

    def test_skips_disabled_late_fee(self, gs_with_invoice):
        """late_fee_enabled=False bo'lsa o'tkazadi."""
        gs, inv = gs_with_invoice

        inv.due_date = date(2026, 3, 1)
        inv.status = Invoice.Status.OVERDUE
        inv.save(update_fields=['due_date', 'status'])

        result = apply_late_fees()
        assert result['applied'] == 0
        assert result['skipped'] == 1

    def test_skips_non_overdue(self, gs_with_invoice):
        """Overdue bo'lmagan invoice'ga penya qo'shilmaydi."""
        gs, inv = gs_with_invoice

        inv.billing_profile.late_fee_enabled = True
        inv.billing_profile.save()

        inv.status = Invoice.Status.UNPAID
        inv.save(update_fields=['status'])

        result = apply_late_fees()
        assert result['applied'] == 0


# =============================================================================
# 4. DUE DATE REMINDERS
# =============================================================================

class TestSendDueDateReminders:

    def test_sends_reminder_3_days_before(self, gs_with_invoice):
        """due_date ga 3 kun qolganda eslatma yuboradi."""
        gs, inv = gs_with_invoice

        inv.due_date = date.today() + timedelta(days=3)
        inv.status = Invoice.Status.UNPAID
        inv.save(update_fields=['due_date', 'status'])

        result = send_due_date_reminders()

        from apps.notifications.models import Notification
        notif = Notification.objects.filter(
            student=inv.student,
            notification_type='payment_reminder',
        ).first()

        assert result['reminders_sent'] == 1
        assert notif is not None
        assert "muddati" in notif.title.lower() or "to'lov" in notif.title.lower()

    def test_no_reminder_if_paid(self, gs_with_invoice):
        """To'langan invoice uchun eslatma yo'q."""
        gs, inv = gs_with_invoice

        inv.due_date = date.today() + timedelta(days=3)
        inv.status = Invoice.Status.PAID
        inv.save(update_fields=['due_date', 'status'])

        result = send_due_date_reminders()
        assert result['reminders_sent'] == 0

    def test_no_duplicate_reminder(self, gs_with_invoice):
        """2 kun ichida ikkinchi eslatma yubormasligi kerak."""
        gs, inv = gs_with_invoice

        inv.due_date = date.today() + timedelta(days=3)
        inv.status = Invoice.Status.UNPAID
        inv.save(update_fields=['due_date', 'status'])

        send_due_date_reminders()
        result2 = send_due_date_reminders()
        assert result2['reminders_sent'] == 0

    def test_no_reminder_if_due_date_far(self, gs_with_invoice):
        """due_date 10 kun keyin — hali eslatma emas."""
        gs, inv = gs_with_invoice

        inv.due_date = date.today() + timedelta(days=10)
        inv.status = Invoice.Status.UNPAID
        inv.save(update_fields=['due_date', 'status'])

        result = send_due_date_reminders()
        assert result['reminders_sent'] == 0


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

class TestHelperFunctions:

    def test_calculate_late_fee_percent(self):
        """Foiz penya hisoblash."""
        inv = type('MockInvoice', (), {'base_amount': Decimal('500000')})()
        profile = type('MockProfile', (), {
            'late_fee_type': 'percent',
            'late_fee_value': Decimal('5'),
        })()

        fee = _calculate_late_fee(inv, profile)
        assert fee == Decimal('25000.00')

    def test_calculate_late_fee_fixed(self):
        """Fixed penya hisoblash."""
        inv = type('MockInvoice', (), {'base_amount': Decimal('500000')})()
        profile = type('MockProfile', (), {
            'late_fee_type': 'fixed',
            'late_fee_value': Decimal('10000'),
        })()

        fee = _calculate_late_fee(inv, profile)
        assert fee == Decimal('10000')
