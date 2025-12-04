
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from core.permissions import RoleBasedPermission
from apps.students.models import Student
from apps.groups.models import GroupStudent
from .models import Payment, Invoice, Discount
from .serializers import (
    PaymentListSerializer,
    PaymentSerializer,
    PaymentCreateSerializer,
    InvoiceListSerializer,
    InvoiceSerializer,
    InvoiceCreateSerializer,
    DiscountSerializer,
    DebtorSerializer
)


class PaymentViewSet(viewsets.ModelViewSet):
    """
    To'lovlar CRUD
    """
    queryset = Payment.objects.select_related('student', 'group', 'received_by').all()
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['student', 'group', 'status', 'payment_method', 'payment_type']
    search_fields = ['student__first_name', 'student__last_name', 'receipt_number']
    ordering_fields = ['amount', 'created_at']
    ordering = ['-created_at']

    role_permissions = {
        'list': ['owner', 'admin', 'accountant', 'registrar'],
        'retrieve': ['owner', 'admin', 'accountant', 'registrar'],
        'create': ['owner', 'admin', 'accountant', 'registrar'],
        'update': ['owner', 'admin', 'accountant'],
        'partial_update': ['owner', 'admin', 'accountant'],
        'destroy': ['owner'],
        'refund': ['owner', 'admin'],
        'statistics': ['owner', 'admin', 'accountant'],
        'by_student': ['owner', 'admin', 'accountant'],
        'debtors': ['owner', 'admin', 'accountant'],
    }

    def get_serializer_class(self):
        if self.action == 'list':
            return PaymentListSerializer
        if self.action == 'create':
            return PaymentCreateSerializer
        return PaymentSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Sana filtri
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)

        return queryset

    @action(detail=True, methods=['post'])
    def refund(self, request, pk=None):
        """
        To'lovni qaytarish

        POST /api/v1/payments/{id}/refund/
        """
        payment = self.get_object()

        if payment.status != 'completed':
            return Response({
                'success': False,
                'error': {'code': 'INVALID_STATUS', 'message': "Faqat qabul qilingan to'lovni qaytarish mumkin"}
            }, status=status.HTTP_400_BAD_REQUEST)

        payment.status = 'refunded'
        payment.save()

        return Response({
            'success': True,
            'message': "To'lov qaytarildi",
            'data': PaymentSerializer(payment).data
        })

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        To'lovlar statistikasi

        GET /api/v1/payments/statistics/?period=month
        """
        period = request.query_params.get('period', 'month')

        today = timezone.now().date()

        if period == 'today':
            start_date = today
            end_date = today
        elif period == 'week':
            start_date = today - timedelta(days=7)
            end_date = today
        elif period == 'month':
            start_date = today.replace(day=1)
            end_date = today
        elif period == 'year':
            start_date = today.replace(month=1, day=1)
            end_date = today
        else:
            start_date = request.query_params.get('start_date', today.replace(day=1))
            end_date = request.query_params.get('end_date', today)

        payments = Payment.objects.filter(
            status='completed',
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )

        total = payments.aggregate(total=Sum('amount'))['total'] or 0
        count = payments.count()

        # Usul bo'yicha
        by_method = payments.values('payment_method').annotate(
            total=Sum('amount'),
            count=Count('id')
        )

        # Tur bo'yicha
        by_type = payments.values('payment_type').annotate(
            total=Sum('amount'),
            count=Count('id')
        )

        return Response({
            'success': True,
            'data': {
                'period': {
                    'start': str(start_date),
                    'end': str(end_date)
                },
                'total': total,
                'count': count,
                'average': round(total / count, 2) if count > 0 else 0,
                'by_method': list(by_method),
                'by_type': list(by_type)
            }
        })

    @action(detail=False, methods=['get'])
    def by_student(self, request):
        """
        O'quvchi to'lovlari

        GET /api/v1/payments/by_student/?student_id=uuid
        """
        student_id = request.query_params.get('student_id')

        if not student_id:
            return Response({
                'success': False,
                'error': {'code': 'MISSING_PARAM', 'message': 'student_id kerak'}
            }, status=status.HTTP_400_BAD_REQUEST)

        student = get_object_or_404(Student, id=student_id)
        payments = Payment.objects.filter(student=student).order_by('-created_at')

        # Statistika
        total_paid = payments.filter(status='completed').aggregate(
            total=Sum('amount')
        )['total'] or 0

        return Response({
            'success': True,
            'data': {
                'student': {
                    'id': str(student.id),
                    'name': student.full_name,
                    'balance': student.balance
                },
                'total_paid': total_paid,
                'payments': PaymentListSerializer(payments[:50], many=True).data
            }
        })

    @action(detail=False, methods=['get'])
    def debtors(self, request):
        """
        Qarzdorlar ro'yxati

        GET /api/v1/payments/debtors/
        """
        # Balans manfiy bo'lgan o'quvchilar
        students = Student.objects.filter(
            balance__lt=0,
            status='active'
        ).order_by('balance')

        data = []
        for student in students:
            groups = GroupStudent.objects.filter(
                student=student,
                is_active=True
            ).select_related('group')

            data.append({
                'student_id': str(student.id),
                'student_name': student.full_name,
                'student_phone': student.phone,
                'parent_phone': student.parent_phone,
                'balance': student.balance,
                'groups': [
                    {
                        'id': str(gs.group.id),
                        'name': gs.group.name,
                        'monthly_price': gs.monthly_price
                    }
                    for gs in groups
                ]
            })

        total_debt = students.aggregate(total=Sum('balance'))['total'] or 0

        return Response({
            'success': True,
            'data': {
                'total_debtors': students.count(),
                'total_debt': abs(total_debt),
                'debtors': data
            }
        })


class InvoiceViewSet(viewsets.ModelViewSet):
    """
    Invoicelar CRUD
    """
    queryset = Invoice.objects.select_related('student', 'group').all()
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['student', 'group', 'status', 'period_month', 'period_year']
    search_fields = ['student__first_name', 'student__last_name', 'invoice_number']
    ordering_fields = ['due_date', 'total', 'created_at']
    ordering = ['-created_at']

    role_permissions = {
        'list': ['owner', 'admin', 'accountant'],
        'retrieve': ['owner', 'admin', 'accountant'],
        'create': ['owner', 'admin', 'accountant'],
        'update': ['owner', 'admin', 'accountant'],
        'partial_update': ['owner', 'admin', 'accountant'],
        'destroy': ['owner'],
        'generate_monthly': ['owner', 'admin', 'accountant'],
    }

    def get_serializer_class(self):
        if self.action == 'list':
            return InvoiceListSerializer
        if self.action == 'create':
            return InvoiceCreateSerializer
        return InvoiceSerializer

    @action(detail=False, methods=['post'])
    def generate_monthly(self, request):
        """
        Oylik invoicelarni generatsiya qilish

        POST /api/v1/invoices/generate_monthly/
        {
            "month": 1,
            "year": 2024,
            "group_id": "uuid" (optional - bo'lmasa hamma guruhlar uchun)
        }
        """
        month = request.data.get('month')
        year = request.data.get('year')
        group_id = request.data.get('group_id')

        if not month or not year:
            return Response({
                'success': False,
                'error': {'code': 'MISSING_PARAM', 'message': 'month va year kerak'}
            }, status=status.HTTP_400_BAD_REQUEST)

        # Guruhlarni olish
        from apps.groups.models import Group, GroupStudent

        groups_query = Group.objects.filter(status='active')
        if group_id:
            groups_query = groups_query.filter(id=group_id)

        created_count = 0
        skipped_count = 0

        for group in groups_query:
            group_students = GroupStudent.objects.filter(
                group=group,
                is_active=True
            ).select_related('student')

            # Due date - keyingi oyning 10-sanasi
            due_date = timezone.datetime(year, month, 10).date()
            if month == 12:
                due_date = timezone.datetime(year + 1, 1, 10).date()
            else:
                due_date = timezone.datetime(year, month + 1, 10).date()

            for gs in group_students:
                # Allaqachon bor-yo'qligini tekshirish
                exists = Invoice.objects.filter(
                    student=gs.student,
                    group=group,
                    period_month=month,
                    period_year=year
                ).exists()

                if exists:
                    skipped_count += 1
                    continue

                # Chegirmani hisoblash
                discount_amount = Decimal('0')
                active_discounts = Discount.objects.filter(
                    student=gs.student,
                    is_active=True,
                    start_date__lte=timezone.now().date()
                ).filter(
                    Q(end_date__isnull=True) | Q(end_date__gte=timezone.now().date())
                ).filter(
                    Q(group__isnull=True) | Q(group=group)
                )

                for discount in active_discounts:
                    discount_amount += discount.calculate_discount(gs.monthly_price)

                # Invoice yaratish
                Invoice.objects.create(
                    student=gs.student,
                    group=group,
                    period_month=month,
                    period_year=year,
                    amount=gs.monthly_price,
                    discount=discount_amount,
                    due_date=due_date,
                    status='sent'
                )
                created_count += 1

        return Response({
            'success': True,
            'message': f"{created_count} ta invoice yaratildi, {skipped_count} ta o'tkazib yuborildi",
            'data': {
                'created': created_count,
                'skipped': skipped_count
            }
        })


class DiscountViewSet(viewsets.ModelViewSet):
    """
    Chegirmalar CRUD
    """
    queryset = Discount.objects.select_related('student', 'group').all()
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['student', 'group', 'discount_type', 'is_active']
    search_fields = ['student__first_name', 'student__last_name', 'name']
    ordering = ['-created_at']

    role_permissions = {
        'list': ['owner', 'admin', 'accountant'],
        'retrieve': ['owner', 'admin', 'accountant'],
        'create': ['owner', 'admin'],
        'update': ['owner', 'admin'],
        'partial_update': ['owner', 'admin'],
        'destroy': ['owner'],
    }

    serializer_class = DiscountSerializer