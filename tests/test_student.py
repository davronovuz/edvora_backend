"""
Students API & Model Tests
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from rest_framework import status


@pytest.mark.django_db
class TestStudentModel:
    """Student model unit tests"""

    def test_full_name(self, create_student):
        student = create_student(first_name='Alisher', last_name='Karimov')
        assert student.full_name == 'Alisher Karimov'

    def test_is_active_true(self, create_student):
        student = create_student(status='active')
        assert student.is_active is True

    def test_is_active_false(self, create_student):
        student = create_student(status='inactive')
        assert student.is_active is False

    def test_has_debt_true(self, create_student):
        student = create_student(balance=Decimal('-50000'))
        assert student.has_debt is True

    def test_has_debt_false(self, create_student):
        student = create_student(balance=Decimal('100000'))
        assert student.has_debt is False

    def test_freeze(self, create_student):
        student = create_student()
        today = date.today()
        end = today + timedelta(days=30)
        student.freeze(start_date=today, end_date=end, reason='Kasal')
        student.refresh_from_db()

        assert student.status == 'frozen'
        assert student.freeze_start_date == today
        assert student.freeze_end_date == end
        assert student.freeze_reason == 'Kasal'

    def test_freeze_propagates_to_group_students(self, create_student, create_group):
        from apps.groups.models import GroupStudent
        student = create_student()
        group = create_group()
        gs = GroupStudent.objects.create(group=group, student=student, joined_date=date.today())
        assert gs.status == 'active'

        student.freeze(start_date=date.today())
        gs.refresh_from_db()
        assert gs.status == 'frozen'

    def test_unfreeze(self, create_student):
        student = create_student()
        student.freeze(start_date=date.today(), reason='Safar')
        student.unfreeze()
        student.refresh_from_db()

        assert student.status == 'active'
        assert student.freeze_start_date is None
        assert student.freeze_end_date is None
        assert student.freeze_reason is None

    def test_unfreeze_propagates_to_group_students(self, create_student, create_group):
        from apps.groups.models import GroupStudent
        student = create_student()
        group = create_group()
        GroupStudent.objects.create(group=group, student=student, joined_date=date.today())

        student.freeze(start_date=date.today())
        student.unfreeze()

        gs = GroupStudent.objects.get(group=group, student=student)
        assert gs.status == 'active'

    def test_is_frozen_within_range(self, create_student):
        student = create_student()
        today = date.today()
        student.freeze_start_date = today - timedelta(days=5)
        student.freeze_end_date = today + timedelta(days=5)
        student.save()
        assert student.is_frozen is True

    def test_is_frozen_outside_range(self, create_student):
        student = create_student()
        today = date.today()
        student.freeze_start_date = today - timedelta(days=30)
        student.freeze_end_date = today - timedelta(days=10)
        student.save()
        assert student.is_frozen is False

    def test_is_frozen_no_end_date(self, create_student):
        student = create_student()
        student.freeze_start_date = date.today() - timedelta(days=5)
        student.freeze_end_date = None
        student.save()
        assert student.is_frozen is True

    def test_is_frozen_no_dates(self, create_student):
        student = create_student()
        assert student.is_frozen is False

    def test_archive(self, create_student):
        student = create_student()
        student.archive(reason='Bitirdi')
        student.refresh_from_db()

        assert student.status == 'inactive'
        assert student.archive_reason == 'Bitirdi'
        assert student.archived_at is not None


@pytest.mark.django_db
class TestGroupStudentModel:
    """GroupStudent model unit tests"""

    def _create_gs(self, create_group, create_student, **gs_kwargs):
        from apps.groups.models import GroupStudent
        group = create_group()
        student = create_student()
        return GroupStudent.objects.create(group=group, student=student, joined_date=date.today(), **gs_kwargs)

    def test_monthly_price_default(self, create_group, create_student):
        """Group actual_price ishlatiladi"""
        gs = self._create_gs(create_group, create_student)
        assert gs.monthly_price == gs.group.actual_price

    def test_monthly_price_custom(self, create_group, create_student):
        gs = self._create_gs(create_group, create_student, custom_price=Decimal('300000'))
        assert gs.monthly_price == Decimal('300000')

    def test_monthly_price_custom_zero(self, create_group, create_student):
        """custom_price=0 (bepul) to'g'ri ishlashi kerak"""
        gs = self._create_gs(create_group, create_student, custom_price=Decimal('0'))
        assert gs.monthly_price == Decimal('0')

    def test_monthly_price_discount(self, create_group, create_student):
        gs = self._create_gs(create_group, create_student, discount_percent=Decimal('20'))
        expected = gs.group.actual_price * Decimal('0.80')
        assert gs.monthly_price == expected

    def test_monthly_price_exception_within_range(self, create_group, create_student):
        today = date.today()
        gs = self._create_gs(
            create_group, create_student,
            exception_sum=Decimal('100000'),
            exception_start_date=today - timedelta(days=5),
            exception_end_date=today + timedelta(days=5),
        )
        assert gs.monthly_price == Decimal('100000')

    def test_monthly_price_exception_expired(self, create_group, create_student):
        today = date.today()
        gs = self._create_gs(
            create_group, create_student,
            exception_sum=Decimal('100000'),
            exception_start_date=today - timedelta(days=30),
            exception_end_date=today - timedelta(days=10),
        )
        # Exception muddati o'tgan, group price ishlatiladi
        assert gs.monthly_price == gs.group.actual_price

    def test_monthly_price_exception_no_end_date(self, create_group, create_student):
        """End date yo'q = cheksiz istisno"""
        today = date.today()
        gs = self._create_gs(
            create_group, create_student,
            exception_sum=Decimal('150000'),
            exception_start_date=today - timedelta(days=5),
            exception_end_date=None,
        )
        assert gs.monthly_price == Decimal('150000')

    def test_is_debtor_true(self, create_group, create_student):
        gs = self._create_gs(create_group, create_student, balance=Decimal('-50000'))
        assert gs.is_debtor is True

    def test_is_debtor_false(self, create_group, create_student):
        gs = self._create_gs(create_group, create_student, balance=Decimal('0'))
        assert gs.is_debtor is False


@pytest.mark.django_db
class TestStudentsAPI:
    """Students endpoint tests"""

    def test_list_students_empty(self, authenticated_client):
        """Bo'sh o'quvchilar ro'yxati"""
        url = '/api/v1/students/'
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_list_students(self, authenticated_client, create_student):
        """O'quvchilar ro'yxati"""
        create_student(phone='+998901111111')
        create_student(phone='+998902222222')
        create_student(phone='+998903333333')

        url = '/api/v1/students/'
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']) == 3

    def test_create_student(self, authenticated_client):
        """Yangi o'quvchi yaratish"""
        url = '/api/v1/students/'
        data = {
            'first_name': 'Alisher',
            'last_name': 'Karimov',
            'phone': '+998901234567',
            'status': 'active',
            'source': 'instagram'
        }

        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['first_name'] == 'Alisher'

    def test_create_student_with_passport(self, authenticated_client):
        """Passportli o'quvchi yaratish"""
        url = '/api/v1/students/'
        data = {
            'first_name': 'Sardor',
            'last_name': 'Toshmatov',
            'phone': '+998901234599',
            'passport_series': 'AB1234567',
            'status': 'active',
        }
        response = authenticated_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_student_without_phone(self, authenticated_client):
        """Telefonsiz o'quvchi - xato"""
        url = '/api/v1/students/'
        data = {
            'first_name': 'Test',
            'last_name': 'Student',
        }
        response = authenticated_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_student_detail(self, authenticated_client, create_student):
        """O'quvchi detali"""
        student = create_student()
        url = f'/api/v1/students/{student.id}/'
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert str(response.data['id']) == str(student.id)

    def test_student_detail_includes_freeze_fields(self, authenticated_client, create_student):
        """Detail da freeze fieldlar bor"""
        student = create_student()
        url = f'/api/v1/students/{student.id}/'
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'is_frozen' in response.data
        assert 'freeze_start_date' in response.data
        assert 'freeze_end_date' in response.data
        assert 'freeze_reason' in response.data

    def test_student_detail_includes_archive_fields(self, authenticated_client, create_student):
        """Detail da archive fieldlar bor"""
        student = create_student()
        url = f'/api/v1/students/{student.id}/'
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'archive_reason' in response.data
        assert 'archived_at' in response.data

    def test_update_student(self, authenticated_client, create_student):
        """O'quvchini yangilash"""
        student = create_student(first_name='Old')
        url = f'/api/v1/students/{student.id}/'
        data = {'first_name': 'New'}
        response = authenticated_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['first_name'] == 'New'

    def test_balance_not_writable_via_api(self, authenticated_client, create_student):
        """Balance API orqali o'zgartirib bo'lmaydi"""
        student = create_student(balance=Decimal('0'))
        url = f'/api/v1/students/{student.id}/'
        data = {'balance': '999999'}
        authenticated_client.patch(url, data, format='json')
        student.refresh_from_db()
        assert student.balance == Decimal('0')

    def test_delete_student(self, authenticated_client, create_student):
        """O'quvchini o'chirish"""
        student = create_student()
        url = f'/api/v1/students/{student.id}/'
        response = authenticated_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_student_statistics(self, authenticated_client, create_student):
        """O'quvchilar statistikasi"""
        create_student(phone='+998901111111', status='active')
        create_student(phone='+998902222222', status='active')
        create_student(phone='+998903333333', status='inactive')

        url = '/api/v1/students/statistics/'
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['total'] == 3
        assert response.data['data']['active'] == 2

    # === Qarzdorlar va freeze endpointlari ===

    def test_debtors_list(self, authenticated_client, create_student):
        """Qarzdorlar ro'yxati"""
        create_student(phone='+998901111111', balance=Decimal('-100000'))
        create_student(phone='+998902222222', balance=Decimal('-50000'))
        create_student(phone='+998903333333', balance=Decimal('500000'))

        url = '/api/v1/students/debtors/'
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']) == 2

    def test_freeze_student(self, authenticated_client, create_student):
        """O'quvchini muzlatish"""
        student = create_student()

        url = f'/api/v1/students/{student.id}/freeze/'
        data = {
            'start_date': '2026-03-22',
            'end_date': '2026-04-22',
            'reason': 'Safarga ketdi',
        }
        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True

        student.refresh_from_db()
        assert student.status == 'frozen'
        assert student.freeze_reason == 'Safarga ketdi'

    def test_freeze_already_frozen(self, authenticated_client, create_student):
        """Allaqachon muzlatilgan o'quvchini muzlatish xato"""
        student = create_student(status='frozen')

        url = f'/api/v1/students/{student.id}/freeze/'
        data = {'start_date': '2026-03-22'}
        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_freeze_without_start_date(self, authenticated_client, create_student):
        """Boshlanish sanasisiz muzlatish xato"""
        student = create_student()

        url = f'/api/v1/students/{student.id}/freeze/'
        response = authenticated_client.post(url, {}, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unfreeze_student(self, authenticated_client, create_student):
        """Muzlatishni bekor qilish"""
        from datetime import date
        student = create_student()
        student.freeze(start_date=date.today(), reason='Test')

        url = f'/api/v1/students/{student.id}/unfreeze/'
        response = authenticated_client.post(url, format='json')

        assert response.status_code == status.HTTP_200_OK
        student.refresh_from_db()
        assert student.status == 'active'
        assert student.freeze_start_date is None

    def test_unfreeze_not_frozen(self, authenticated_client, create_student):
        """Muzlatilmagan o'quvchini unfreeze qilish xato"""
        student = create_student()

        url = f'/api/v1/students/{student.id}/unfreeze/'
        response = authenticated_client.post(url, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_archive_student(self, authenticated_client, create_student):
        """O'quvchini arxivga olish"""
        student = create_student()

        url = f'/api/v1/students/{student.id}/archive/'
        data = {'reason': 'Bitirdi'}
        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        student.refresh_from_db()
        assert student.status == 'inactive'
        assert student.archive_reason == 'Bitirdi'
        assert student.archived_at is not None
