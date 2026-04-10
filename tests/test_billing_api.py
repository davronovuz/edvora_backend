"""
Edvora - Billing API Tests (Stage 5)

API endpointlar, FK iyerarxiya, Payment bug fix.
"""

from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from rest_framework import status as http_status

from apps.billing.models import (
    BillingProfile,
    Discount,
    Invoice,
    InvoiceLine,
    StudentLeave,
)
from apps.billing.services.invoice_service import InvoiceService


pytestmark = pytest.mark.django_db


# =============================================================================
# Fixtures
# =============================================================================

def make_profile(**kwargs):
    defaults = dict(name="Test Profile", mode=BillingProfile.Mode.MONTHLY_FLAT, is_default=True)
    defaults.update(kwargs)
    return BillingProfile.objects.create(**defaults)


@pytest.fixture
def profile():
    return make_profile()


@pytest.fixture
def test_group(create_course, create_teacher):
    from apps.groups.models import Group
    return Group.objects.create(
        name="API Test Group",
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
        joined_date=date(2026, 4, 1),
        is_active=True,
        status='active',
    )


# =============================================================================
# Profile FK Iyerarxiya
# =============================================================================

class TestProfileHierarchy:
    def test_global_default(self, gs, profile):
        resolved = InvoiceService.resolve_profile(gs)
        assert resolved.pk == profile.pk

    def test_branch_overrides_global(self, gs, profile):
        from apps.branches.models import Branch
        branch = Branch.objects.create(name="Filial", address="X")
        gs.group.branch = branch
        gs.group.save()

        branch_profile = BillingProfile.objects.create(
            name="Branch", mode=BillingProfile.Mode.MONTHLY_PRORATED_DAYS,
            branch=branch, is_default=True,
        )
        resolved = InvoiceService.resolve_profile(gs)
        assert resolved.pk == branch_profile.pk

    def test_course_overrides_branch(self, gs, profile):
        from apps.branches.models import Branch
        branch = Branch.objects.create(name="F", address="X")
        gs.group.branch = branch
        gs.group.save()

        BillingProfile.objects.create(
            name="Branch", mode=BillingProfile.Mode.MONTHLY_FLAT,
            branch=branch, is_default=True,
        )
        course_profile = BillingProfile.objects.create(
            name="Course", mode=BillingProfile.Mode.PER_LESSON,
            price_per_lesson=Decimal("50000"),
        )
        gs.group.course.billing_profile = course_profile
        gs.group.course.save()

        resolved = InvoiceService.resolve_profile(gs)
        assert resolved.pk == course_profile.pk

    def test_group_overrides_course(self, gs, profile):
        course_profile = BillingProfile.objects.create(
            name="Course", mode=BillingProfile.Mode.MONTHLY_FLAT,
        )
        gs.group.course.billing_profile = course_profile
        gs.group.course.save()

        group_profile = BillingProfile.objects.create(
            name="Group", mode=BillingProfile.Mode.PER_LESSON,
            price_per_lesson=Decimal("50000"),
        )
        gs.group.billing_profile = group_profile
        gs.group.save()

        resolved = InvoiceService.resolve_profile(gs)
        assert resolved.pk == group_profile.pk

    def test_individual_overrides_all(self, gs, profile):
        group_profile = BillingProfile.objects.create(
            name="Group", mode=BillingProfile.Mode.MONTHLY_FLAT,
        )
        gs.group.billing_profile = group_profile
        gs.group.save()

        individual_profile = BillingProfile.objects.create(
            name="Individual", mode=BillingProfile.Mode.HOURLY,
            price_per_hour=Decimal("100000"),
        )
        gs.billing_profile = individual_profile
        gs.save()

        resolved = InvoiceService.resolve_profile(gs)
        assert resolved.pk == individual_profile.pk


# =============================================================================
# joined_date fix
# =============================================================================

class TestJoinedDateFix:
    def test_joined_date_not_auto(self, test_group, create_student):
        """joined_date ni qo'lda kiritish mumkin (retroaktiv)."""
        from apps.groups.models import GroupStudent
        gs = GroupStudent.objects.create(
            group=test_group,
            student=create_student(first_name="Past", phone="+998991112233"),
            joined_date=date(2025, 9, 1),  # O'tgan yil
            is_active=True,
        )
        assert gs.joined_date == date(2025, 9, 1)


# =============================================================================
# Payment.save() UUID bug fix
# =============================================================================

class TestPaymentSaveFix:
    def test_new_payment_updates_balance(self, gs):
        from apps.payments.models import Payment
        initial_balance = gs.student.balance

        Payment.objects.create(
            student=gs.student,
            amount=Decimal("500000"),
            payment_method='cash',
            payment_type='tuition',
            status='completed',
        )

        gs.student.refresh_from_db()
        assert gs.student.balance == initial_balance + Decimal("500000")

    def test_refund_decreases_balance(self, gs):
        from apps.payments.models import Payment
        p = Payment.objects.create(
            student=gs.student,
            amount=Decimal("500000"),
            payment_method='cash',
            payment_type='tuition',
            status='completed',
        )
        gs.student.refresh_from_db()
        after_payment = gs.student.balance

        p.status = 'refunded'
        p.save()

        gs.student.refresh_from_db()
        assert gs.student.balance == after_payment - Decimal("500000")


# =============================================================================
# Billing API endpoints
# =============================================================================

class TestBillingProfileAPI:
    def test_list(self, authenticated_client):
        make_profile(name="P1")
        make_profile(name="P2")
        response = authenticated_client.get('/api/v1/billing/profiles/')
        assert response.status_code == http_status.HTTP_200_OK
        assert len(response.data['data']) == 2

    def test_create(self, authenticated_client):
        data = {
            'name': 'New Profile',
            'mode': 'monthly_flat',
            'billing_day': 1,
            'due_days': 10,
        }
        response = authenticated_client.post('/api/v1/billing/profiles/', data, format='json')
        assert response.status_code == http_status.HTTP_201_CREATED
        assert response.data['name'] == 'New Profile'

    def test_modes_endpoint(self, authenticated_client):
        response = authenticated_client.get('/api/v1/billing/profiles/modes/')
        assert response.status_code == http_status.HTTP_200_OK
        assert len(response.data) == 8


class TestStudentLeaveAPI:
    def test_create_and_approve(self, authenticated_client, gs):
        # Yaratish
        data = {
            'group_student': str(gs.pk),
            'start_date': '2026-04-10',
            'end_date': '2026-04-14',
            'reason': 'Sayohat',
        }
        resp = authenticated_client.post('/api/v1/billing/leaves/', data, format='json')
        assert resp.status_code == http_status.HTTP_201_CREATED
        leave_id = resp.data['id']
        assert resp.data['status'] == 'pending'

        # Tasdiqlash
        resp2 = authenticated_client.post(f'/api/v1/billing/leaves/{leave_id}/approve/')
        assert resp2.status_code == http_status.HTTP_200_OK
        assert resp2.data['status'] == 'approved'

    def test_reject(self, authenticated_client, gs):
        leave = StudentLeave.objects.create(
            group_student=gs,
            start_date=date(2026, 4, 10),
            end_date=date(2026, 4, 14),
            reason="x",
        )
        resp = authenticated_client.post(f'/api/v1/billing/leaves/{leave.pk}/reject/')
        assert resp.status_code == http_status.HTTP_200_OK
        assert resp.data['status'] == 'rejected'


class TestDiscountAPI:
    def test_list(self, authenticated_client):
        Discount.objects.create(
            kind=Discount.Kind.STUDENT_PERCENT,
            name="Test 10%",
            value_type=Discount.ValueType.PERCENT,
            value=Decimal("10"),
            start_date=date(2026, 1, 1),
        )
        resp = authenticated_client.get('/api/v1/billing/discounts/')
        assert resp.status_code == http_status.HTTP_200_OK
        assert len(resp.data['data']) == 1

    def test_create(self, authenticated_client):
        data = {
            'kind': 'student_percent',
            'name': 'Yangi',
            'value_type': 'percent',
            'value': '15',
            'start_date': '2026-01-01',
        }
        resp = authenticated_client.post('/api/v1/billing/discounts/', data, format='json')
        assert resp.status_code == http_status.HTTP_201_CREATED


class TestInvoiceAPI:
    def test_generate(self, authenticated_client, profile, gs):
        data = {
            'group_student_id': str(gs.pk),
            'year': 2026,
            'month': 4,
        }
        resp = authenticated_client.post('/api/v1/billing/invoices/generate/', data, format='json')
        assert resp.status_code == http_status.HTTP_201_CREATED
        assert resp.data['base_amount'] == '500000.00'
        assert resp.data['status'] == 'unpaid'
        assert 'lines' in resp.data

    def test_generate_duplicate(self, authenticated_client, profile, gs):
        data = {'group_student_id': str(gs.pk), 'year': 2026, 'month': 4}
        authenticated_client.post('/api/v1/billing/invoices/generate/', data, format='json')
        resp2 = authenticated_client.post('/api/v1/billing/invoices/generate/', data, format='json')
        assert resp2.status_code == http_status.HTTP_409_CONFLICT

    def test_generate_group(self, authenticated_client, profile, test_group, create_student):
        from apps.groups.models import GroupStudent
        for i in range(3):
            GroupStudent.objects.create(
                group=test_group,
                student=create_student(first_name=f"S{i}", phone=f"+99890{i}222222"),
                joined_date=date(2026, 4, 1),
                is_active=True, status='active',
            )
        data = {'group_id': str(test_group.pk), 'year': 2026, 'month': 4}
        resp = authenticated_client.post(
            '/api/v1/billing/invoices/generate-group/', data, format='json'
        )
        assert resp.status_code == http_status.HTTP_201_CREATED
        assert resp.data['generated_count'] == 3

    def test_list_and_filter(self, authenticated_client, profile, gs):
        svc = InvoiceService()
        svc.generate(gs, 2026, 4)
        svc.generate(gs, 2026, 5)

        resp = authenticated_client.get('/api/v1/billing/invoices/')
        assert resp.status_code == http_status.HTTP_200_OK
        assert len(resp.data['data']) == 2

        resp2 = authenticated_client.get('/api/v1/billing/invoices/?period_month=4')
        assert len(resp2.data['data']) == 1

    def test_cancel(self, authenticated_client, profile, gs):
        svc = InvoiceService()
        inv = svc.generate(gs, 2026, 4)
        resp = authenticated_client.post(f'/api/v1/billing/invoices/{inv.pk}/cancel/')
        assert resp.status_code == http_status.HTTP_200_OK
        assert resp.data['status'] == 'cancelled'

    def test_debtors(self, authenticated_client, profile, gs):
        svc = InvoiceService()
        svc.generate(gs, 2026, 4)
        resp = authenticated_client.get('/api/v1/billing/invoices/debtors/')
        assert resp.status_code == http_status.HTTP_200_OK
        assert len(resp.data) == 1

    def test_summary(self, authenticated_client, profile, gs):
        svc = InvoiceService()
        svc.generate(gs, 2026, 4)
        resp = authenticated_client.get('/api/v1/billing/invoices/summary/?year=2026&month=4')
        assert resp.status_code == http_status.HTTP_200_OK
        assert resp.data['total_expected'] == '500000.00'
        assert resp.data['total_collected'] == '0'
