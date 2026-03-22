"""
Payments API Tests
"""

import pytest
from rest_framework import status
from decimal import Decimal
from tests.factories import StudentFactory, GroupFactory
from apps.payments.models import Payment


@pytest.mark.django_db
class TestPaymentsAPI:
    """Payments endpoint tests"""

    def test_create_payment(self, authenticated_client):
        """To'lov yaratish"""
        student = StudentFactory.create(balance=0)

        url = '/api/v1/payments/'
        data = {
            'student': str(student.id),
            'amount': 500000,
            'payment_method': 'cash',
            'payment_type': 'tuition'
        }

        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED

        # Balans yangilanganini tekshirish
        student.refresh_from_db()
        assert student.balance == Decimal('500000')

    def test_payment_refund(self, authenticated_client):
        """To'lovni qaytarish"""
        student = StudentFactory.create(balance=500000)

        # To'lov yaratish
        payment = Payment.objects.create(
            student=student,
            amount=500000,
            payment_method='cash',
            payment_type='tuition',
            status='completed',
            receipt_number='PAY-TEST-001'
        )

        url = f'/api/v1/payments/{payment.id}/refund/'
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_200_OK

        payment.refresh_from_db()
        assert payment.status == 'refunded'

    def test_debtors_list(self, authenticated_client):
        """Qarzdorlar ro'yxati"""
        # Qarzdor o'quvchilar
        StudentFactory.create(balance=-500000, status='active')
        StudentFactory.create(balance=-300000, status='active')

        # Qarzsiz o'quvchi
        StudentFactory.create(balance=100000, status='active')

        url = '/api/v1/payments/debtors/'
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['total_debtors'] == 2

    def test_payment_statistics(self, authenticated_client):
        """To'lovlar statistikasi"""
        student = StudentFactory.create()

        Payment.objects.create(
            student=student,
            amount=500000,
            payment_method='cash',
            payment_type='tuition',
            status='completed',
            receipt_number='PAY-TEST-002'
        )
        Payment.objects.create(
            student=student,
            amount=300000,
            payment_method='card',
            payment_type='tuition',
            status='completed',
            receipt_number='PAY-TEST-003'
        )

        url = '/api/v1/payments/statistics/'
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['total'] == 800000
        assert response.data['data']['count'] == 2
        