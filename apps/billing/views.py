"""
Edvora - Billing Views
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from django.utils import timezone

from core.permissions import RoleBasedPermission

from .models import (
    BillingProfile,
    Discount,
    Invoice,
    InvoiceLine,
    StudentLeave,
)
from .serializers import (
    BillingProfileListSerializer,
    BillingProfileSerializer,
    BillingProfileCreateSerializer,
    StudentLeaveSerializer,
    DiscountListSerializer,
    DiscountSerializer,
    InvoiceListSerializer,
    InvoiceDetailSerializer,
    InvoiceGenerateSerializer,
    InvoiceGenerateGroupSerializer,
    PaymentAllocateSerializer,
)
from .services.invoice_service import InvoiceService
from .services.payment_allocator import PaymentAllocator


class BillingProfileViewSet(viewsets.ModelViewSet):
    """
    Billing profillari CRUD.
    """
    queryset = BillingProfile.objects.all()
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['mode', 'is_default', 'is_active', 'branch']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'mode']

    def get_serializer_class(self):
        if self.action == 'list':
            return BillingProfileListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return BillingProfileCreateSerializer
        return BillingProfileSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == 'list':
            qs = qs.annotate(invoices_count=Count('invoices'))
        return qs

    @action(detail=False, methods=['get'])
    def modes(self, request):
        """Barcha mavjud billing mode'larni ro'yxatlash."""
        from .registry import available_modes
        modes = []
        for mode_value in available_modes():
            label = dict(BillingProfile.Mode.choices).get(mode_value, mode_value)
            modes.append({'value': mode_value, 'label': label})
        return Response(modes)


class StudentLeaveViewSet(viewsets.ModelViewSet):
    """
    Ta'tillar CRUD + approve/reject.
    """
    queryset = StudentLeave.objects.select_related(
        'group_student__student',
        'group_student__group',
    ).all()
    serializer_class = StudentLeaveSerializer
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'group_student']
    search_fields = ['reason']
    ordering_fields = ['start_date', 'created_at']

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        leave = self.get_object()
        if leave.status != StudentLeave.Status.PENDING:
            return Response(
                {'detail': "Faqat PENDING ta'tilni tasdiqlash mumkin"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        leave.status = StudentLeave.Status.APPROVED
        leave.approved_by = request.user
        leave.approved_at = timezone.now()
        leave.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])
        return Response(StudentLeaveSerializer(leave).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        leave = self.get_object()
        if leave.status != StudentLeave.Status.PENDING:
            return Response(
                {'detail': "Faqat PENDING ta'tilni rad etish mumkin"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        leave.status = StudentLeave.Status.REJECTED
        leave.save(update_fields=['status', 'updated_at'])
        return Response(StudentLeaveSerializer(leave).data)


class DiscountViewSet(viewsets.ModelViewSet):
    """
    Chegirmalar CRUD.
    """
    queryset = Discount.objects.select_related(
        'student', 'group', 'course', 'branch',
    ).all()
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['kind', 'is_active', 'student', 'group', 'value_type']
    search_fields = ['name', 'code']
    ordering_fields = ['priority', 'created_at', 'name']

    def get_serializer_class(self):
        if self.action == 'list':
            return DiscountListSerializer
        return DiscountSerializer


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Invoicelar — faqat o'qish + maxsus action'lar.
    Invoice yaratish `generate` action orqali bo'ladi.
    """
    queryset = Invoice.objects.select_related(
        'student', 'group', 'billing_profile',
    ).all()
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'student', 'group', 'period_year', 'period_month']
    search_fields = ['number', 'student__first_name', 'student__last_name', 'group__name']
    ordering_fields = ['period_year', 'period_month', 'due_date', 'total_amount', 'created_at']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return InvoiceDetailSerializer
        return InvoiceListSerializer

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Bitta o'quvchi uchun invoice generatsiya."""
        ser = InvoiceGenerateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        from apps.groups.models import GroupStudent
        gs = get_object_or_404(GroupStudent, pk=ser.validated_data['group_student_id'])

        svc = InvoiceService()
        invoice = svc.generate(
            gs,
            ser.validated_data['year'],
            ser.validated_data['month'],
            promo_code=ser.validated_data.get('promo_code'),
            force=ser.validated_data.get('force', False),
        )

        if invoice is None:
            # Sabab: profil topilmadi yoki allaqachon mavjud
            existing = Invoice.objects.filter(
                group_student=gs,
                period_year=ser.validated_data['year'],
                period_month=ser.validated_data['month'],
            ).exclude(status=Invoice.Status.CANCELLED).exists()

            if existing:
                return Response(
                    {'detail': "Bu davr uchun invoice allaqachon mavjud"},
                    status=status.HTTP_409_CONFLICT,
                )
            return Response(
                {'detail': "Billing profil topilmadi. Avval default profil yarating (Profillar tabida)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            InvoiceDetailSerializer(invoice).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['post'], url_path='generate-group')
    def generate_group(self, request):
        """Butun guruh uchun batch invoice generatsiya."""
        ser = InvoiceGenerateGroupSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        from apps.groups.models import Group
        group = get_object_or_404(Group, pk=ser.validated_data['group_id'])

        svc = InvoiceService()
        invoices = svc.generate_for_group(
            group,
            ser.validated_data['year'],
            ser.validated_data['month'],
        )

        return Response({
            'generated_count': len(invoices),
            'invoices': InvoiceListSerializer(invoices, many=True).data,
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='allocate-payment')
    def allocate_payment(self, request):
        """To'lovni invoice'larga FIFO taqsimlash."""
        ser = PaymentAllocateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        from apps.payments.models import Payment
        from apps.groups.models import GroupStudent

        payment = get_object_or_404(Payment, pk=ser.validated_data['payment_id'])

        gs = None
        if ser.validated_data.get('group_student_id'):
            gs = get_object_or_404(GroupStudent, pk=ser.validated_data['group_student_id'])

        allocator = PaymentAllocator()
        result = allocator.allocate(payment, group_student=gs)

        return Response({
            'allocated': [
                {'invoice': inv.number, 'amount': str(amount)}
                for inv, amount in result.allocated
            ],
            'remaining': str(result.remaining),
            'paid_invoices': [inv.number for inv in result.paid_invoices],
            'partial_invoices': [inv.number for inv in result.partial_invoices],
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Invoiceni bekor qilish."""
        invoice = self.get_object()
        if invoice.status == Invoice.Status.PAID:
            return Response(
                {'detail': "To'langan invoiceni bekor qilib bo'lmaydi"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        invoice.status = Invoice.Status.CANCELLED
        invoice.save(update_fields=['status', 'updated_at'])
        return Response(InvoiceDetailSerializer(invoice).data)

    @action(detail=False, methods=['get'])
    def debtors(self, request):
        """Qarzdorlar ro'yxati."""
        from django.db.models import Sum, F

        overdue = (
            Invoice.objects
            .filter(status__in=[Invoice.Status.UNPAID, Invoice.Status.PARTIAL, Invoice.Status.OVERDUE])
            .values('student__id', 'student__first_name', 'student__last_name')
            .annotate(
                total_debt=Sum(F('total_amount') - F('paid_amount')),
                invoice_count=Count('id'),
            )
            .filter(total_debt__gt=0)
            .order_by('-total_debt')[:50]
        )

        return Response(list(overdue))

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Oylik qisqacha statistika."""
        year = int(request.query_params.get('year', timezone.now().year))
        month = int(request.query_params.get('month', timezone.now().month))

        from django.db.models import Sum

        qs = Invoice.objects.filter(period_year=year, period_month=month)

        total_expected = qs.exclude(
            status=Invoice.Status.CANCELLED
        ).aggregate(s=Sum('total_amount'))['s'] or 0

        total_collected = qs.exclude(
            status=Invoice.Status.CANCELLED
        ).aggregate(s=Sum('paid_amount'))['s'] or 0

        total_discount = qs.exclude(
            status=Invoice.Status.CANCELLED
        ).aggregate(s=Sum('discount_amount'))['s'] or 0

        overdue_count = qs.filter(status=Invoice.Status.OVERDUE).count()
        paid_count = qs.filter(status=Invoice.Status.PAID).count()
        total_count = qs.exclude(status=Invoice.Status.CANCELLED).count()

        return Response({
            'period': f"{year}-{month:02d}",
            'total_expected': str(total_expected),
            'total_collected': str(total_collected),
            'total_discount': str(total_discount),
            'total_debt': str(total_expected - total_collected),
            'overdue_count': overdue_count,
            'paid_count': paid_count,
            'total_count': total_count,
        })
