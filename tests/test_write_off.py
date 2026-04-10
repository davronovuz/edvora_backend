"""
Write-Off (Oylik yechib olish) Tests
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from django.utils import timezone


@pytest.mark.django_db
class TestWriteOffTask:
    """process_monthly_write_offs task tests"""

    def _setup_enrollment(self, create_group, create_student, next_wo_date=None, **gs_kwargs):
        """GroupStudent yaratish helper"""
        from apps.groups.models import GroupStudent

        group = create_group()
        student = create_student()

        if next_wo_date is None:
            next_wo_date = date.today()

        defaults = {
            'group': group,
            'student': student,
            'next_write_off_date': next_wo_date,
        }
        defaults.update(gs_kwargs)
        defaults.setdefault('joined_date', date.today())
        gs = GroupStudent.objects.create(**defaults)
        return gs

    def test_basic_write_off(self, create_group, create_student):
        """Oddiy write-off ishlashi"""
        from apps.payments.tasks import process_monthly_write_offs
        from apps.payments.models import WriteOff

        gs = self._setup_enrollment(create_group, create_student)
        initial_price = gs.monthly_price

        result = process_monthly_write_offs()

        gs.refresh_from_db()
        gs.student.refresh_from_db()

        assert result['processed'] == 1
        assert gs.balance == -initial_price
        assert gs.student.balance == -initial_price
        assert gs.last_write_off_date == date.today()
        assert gs.next_write_off_date == date.today() + relativedelta(months=1)

        # WriteOff log yaratilganmi?
        wo = WriteOff.objects.get(group_student=gs)
        assert wo.amount == initial_price
        assert wo.balance_before == Decimal('0')
        assert wo.balance_after == -initial_price

    def test_write_off_skips_future_date(self, create_group, create_student):
        """next_write_off_date kelajakda bo'lsa o'tkazib yuborish"""
        from apps.payments.tasks import process_monthly_write_offs

        future = date.today() + timedelta(days=15)
        self._setup_enrollment(create_group, create_student, next_wo_date=future)

        result = process_monthly_write_offs()
        assert result['processed'] == 0

    def test_write_off_skips_frozen(self, create_group, create_student):
        """Muzlatilgan o'quvchini o'tkazib yuborish"""
        from apps.payments.tasks import process_monthly_write_offs
        from apps.groups.models import GroupStudent

        gs = self._setup_enrollment(create_group, create_student)
        gs.status = GroupStudent.Status.FROZEN
        gs.save()

        result = process_monthly_write_offs()
        assert result['processed'] == 0

    def test_write_off_skips_inactive(self, create_group, create_student):
        """is_active=False o'tkazib yuborish"""
        from apps.payments.tasks import process_monthly_write_offs

        gs = self._setup_enrollment(create_group, create_student)
        gs.is_active = False
        gs.save()

        result = process_monthly_write_offs()
        assert result['processed'] == 0

    def test_write_off_with_custom_price(self, create_group, create_student):
        """Maxsus narx bilan write-off"""
        from apps.payments.tasks import process_monthly_write_offs

        gs = self._setup_enrollment(
            create_group, create_student,
            custom_price=Decimal('300000'),
        )

        result = process_monthly_write_offs()

        gs.refresh_from_db()
        assert result['processed'] == 1
        assert gs.balance == Decimal('-300000')

    def test_write_off_no_duplicate(self, create_group, create_student):
        """Bir oyda ikki marta yechib olinmasligi"""
        from apps.payments.tasks import process_monthly_write_offs

        gs = self._setup_enrollment(create_group, create_student)

        # Birinchi marta
        result1 = process_monthly_write_offs()
        assert result1['processed'] == 1

        # next_write_off_date kelajakka o'tgan, ikkinchi marta ishlamaydi
        result2 = process_monthly_write_offs()
        assert result2['processed'] == 0

    def test_write_off_updates_student_balance(self, create_group, create_student):
        """Student balans ham yangilanishi"""
        from apps.payments.tasks import process_monthly_write_offs

        gs = self._setup_enrollment(create_group, create_student)
        student = gs.student

        # Student ga oldindan to'lov qo'shish
        student.balance = Decimal('1000000')
        student.save()

        price = gs.monthly_price
        process_monthly_write_offs()

        student.refresh_from_db()
        assert student.balance == Decimal('1000000') - price


@pytest.mark.django_db
class TestWriteOffModel:
    """WriteOff model tests"""

    def test_write_off_unique_per_month(self, create_group, create_student):
        """Bir oyda bir GroupStudent uchun faqat bitta WriteOff"""
        from apps.groups.models import GroupStudent
        from apps.payments.models import WriteOff
        from django.db import IntegrityError

        group = create_group()
        student = create_student()
        gs = GroupStudent.objects.create(group=group, student=student, joined_date=date.today())

        WriteOff.objects.create(
            student=student, group=group, group_student=gs,
            amount=Decimal('500000'), period_month=3, period_year=2026,
            balance_before=Decimal('0'), balance_after=Decimal('-500000'),
        )

        with pytest.raises(IntegrityError):
            WriteOff.objects.create(
                student=student, group=group, group_student=gs,
                amount=Decimal('500000'), period_month=3, period_year=2026,
                balance_before=Decimal('-500000'), balance_after=Decimal('-1000000'),
            )

    def test_write_off_str(self, create_group, create_student):
        from apps.groups.models import GroupStudent
        from apps.payments.models import WriteOff

        group = create_group()
        student = create_student()
        gs = GroupStudent.objects.create(group=group, student=student, joined_date=date.today())

        wo = WriteOff.objects.create(
            student=student, group=group, group_student=gs,
            amount=Decimal('500000'), period_month=3, period_year=2026,
            balance_before=Decimal('0'), balance_after=Decimal('-500000'),
        )
        assert student.full_name in str(wo)
        assert '3/2026' in str(wo)
