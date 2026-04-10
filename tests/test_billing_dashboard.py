"""
Edvora - Billing Dashboard & Analytics Tests (Stage 7)

Dashboard KPI, billing_chart, billing_debtors, billing_summary endpoint'lari.
"""

from datetime import date, time
from decimal import Decimal

import pytest
from rest_framework import status as http_status

from apps.billing.models import BillingProfile, Invoice
from apps.billing.services.invoice_service import InvoiceService


pytestmark = pytest.mark.django_db


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def profile():
    return BillingProfile.objects.create(
        name="Dashboard Profile",
        mode=BillingProfile.Mode.MONTHLY_FLAT,
        is_default=True,
        billing_day=1,
        due_days=10,
    )


@pytest.fixture
def test_group(create_course, create_teacher):
    from apps.groups.models import Group
    return Group.objects.create(
        name="Dashboard Group",
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
def invoice(profile, gs):
    svc = InvoiceService()
    return svc.generate(gs, 2026, 4)


# =============================================================================
# Dashboard Summary — billing bo'lim
# =============================================================================

class TestDashboardBilling:
    def test_summary_includes_billing(self, authenticated_client, invoice):
        resp = authenticated_client.get('/api/v1/analytics/dashboard/summary/')
        assert resp.status_code == http_status.HTTP_200_OK
        data = resp.data['data']
        assert 'billing' in data
        billing = data['billing']
        assert 'expected' in billing
        assert 'collected' in billing
        assert 'debt' in billing
        assert 'collection_rate' in billing
        assert 'overdue_count' in billing


# =============================================================================
# Billing Chart (12 oy)
# =============================================================================

class TestBillingChart:
    def test_chart_returns_12_months(self, authenticated_client, invoice):
        resp = authenticated_client.get('/api/v1/analytics/dashboard/billing_chart/')
        assert resp.status_code == http_status.HTTP_200_OK
        data = resp.data['data']
        assert len(data['labels']) == 12
        assert len(data['datasets']) == 3
        # Dataset nomlari
        labels = [d['label'] for d in data['datasets']]
        assert 'Kutilayotgan' in labels
        assert "Yig'ilgan" in labels
        assert 'Qarz' in labels

    def test_chart_data_matches_invoice(self, authenticated_client, invoice):
        resp = authenticated_client.get('/api/v1/analytics/dashboard/billing_chart/')
        data = resp.data['data']

        # Invoice 04/2026 da bo'lishi kerak
        expected_ds = next(d for d in data['datasets'] if d['label'] == 'Kutilayotgan')
        # Oxirgi elementda (yoki tegishli oyda) qiymat > 0 bo'lishi kerak
        assert any(v > 0 for v in expected_ds['data'])


# =============================================================================
# Billing Debtors
# =============================================================================

class TestBillingDebtors:
    def test_debtors_list(self, authenticated_client, invoice):
        """Unpaid invoice bo'lsa qarzdor sifatida chiqadi."""
        resp = authenticated_client.get('/api/v1/analytics/dashboard/billing_debtors/')
        assert resp.status_code == http_status.HTTP_200_OK
        data = resp.data['data']
        assert data['total_debtors'] == 1
        assert data['total_debt'] > 0
        assert len(data['debtors']) == 1
        assert 'by_range' in data

    def test_no_debtors_when_paid(self, authenticated_client, invoice):
        """To'langan invoice'da qarzdor yo'q."""
        invoice.paid_amount = invoice.total_amount
        invoice.status = Invoice.Status.PAID
        invoice.save(update_fields=['paid_amount', 'status'])

        resp = authenticated_client.get('/api/v1/analytics/dashboard/billing_debtors/')
        data = resp.data['data']
        assert data['total_debtors'] == 0

    def test_debtors_range_distribution(self, authenticated_client, invoice):
        """Qarz diapazon taqsimoti."""
        resp = authenticated_client.get('/api/v1/analytics/dashboard/billing_debtors/')
        data = resp.data['data']
        ranges = data['by_range']
        assert len(ranges) == 4
        total_in_ranges = sum(r['count'] for r in ranges)
        assert total_in_ranges == data['total_debtors']


# =============================================================================
# Billing Summary (oylik batafsil)
# =============================================================================

class TestBillingSummary:
    def test_summary_by_period(self, authenticated_client, invoice):
        resp = authenticated_client.get(
            '/api/v1/analytics/dashboard/billing_summary/?year=2026&month=4'
        )
        assert resp.status_code == http_status.HTTP_200_OK
        data = resp.data['data']
        assert data['period'] == '2026-04'
        assert Decimal(data['expected']) == invoice.total_amount
        assert Decimal(data['collected']) == Decimal('0')
        assert Decimal(data['debt']) == invoice.total_amount
        assert 'by_status' in data
        assert 'by_group' in data

    def test_summary_collection_rate(self, authenticated_client, invoice):
        """Qisman to'lov — collection_rate to'g'ri hisoblanadi."""
        invoice.paid_amount = Decimal("250000")
        invoice.status = Invoice.Status.PARTIAL
        invoice.save(update_fields=['paid_amount', 'status'])

        resp = authenticated_client.get(
            '/api/v1/analytics/dashboard/billing_summary/?year=2026&month=4'
        )
        data = resp.data['data']
        assert data['collection_rate'] == 50.0

    def test_summary_empty_period(self, authenticated_client, profile):
        """Invoice yo'q oy uchun 0 qiymatlar."""
        resp = authenticated_client.get(
            '/api/v1/analytics/dashboard/billing_summary/?year=2025&month=1'
        )
        assert resp.status_code == http_status.HTTP_200_OK
        data = resp.data['data']
        assert Decimal(data['expected']) == 0
        assert data['collection_rate'] == 0

    def test_summary_by_group(self, authenticated_client, profile, test_group, create_student):
        """Guruh bo'yicha qarz taqsimoti."""
        from apps.groups.models import GroupStudent
        svc = InvoiceService()

        for i in range(2):
            gs = GroupStudent.objects.create(
                group=test_group,
                student=create_student(first_name=f"D{i}", phone=f"+99891{i}444444"),
                joined_date=date(2026, 3, 1),
                is_active=True,
                status='active',
            )
            svc.generate(gs, 2026, 4)

        resp = authenticated_client.get(
            '/api/v1/analytics/dashboard/billing_summary/?year=2026&month=4'
        )
        data = resp.data['data']
        assert len(data['by_group']) >= 1
        assert data['by_group'][0]['student_count'] == 2

    def test_summary_includes_discount_info(self, authenticated_client, invoice):
        """Chegirma, ta'til, penya ko'rsatiladi."""
        resp = authenticated_client.get(
            '/api/v1/analytics/dashboard/billing_summary/?year=2026&month=4'
        )
        data = resp.data['data']
        assert 'discount_total' in data
        assert 'leave_credit_total' in data
        assert 'late_fee_total' in data
        assert 'base_total' in data

    def test_cancelled_excluded(self, authenticated_client, invoice):
        """Cancelled invoice statistikaga kirmaydi."""
        invoice.status = Invoice.Status.CANCELLED
        invoice.save(update_fields=['status'])

        resp = authenticated_client.get(
            '/api/v1/analytics/dashboard/billing_summary/?year=2026&month=4'
        )
        data = resp.data['data']
        assert Decimal(data['expected']) == 0
