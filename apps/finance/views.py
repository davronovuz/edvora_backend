"""
Edvora - Finance Views
"""

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
from apps.teachers.models import Teacher
from apps.groups.models import Group, GroupStudent
from apps.attendance.models import Attendance
from apps.payments.models import Payment
from .models import ExpenseCategory, Expense, Transaction, Salary
from .serializers import (
    ExpenseCategorySerializer,
    ExpenseListSerializer,
    ExpenseSerializer,
    ExpenseCreateSerializer,
    TransactionSerializer,
    SalaryListSerializer,
    SalarySerializer,
    SalaryCalculateSerializer,
    FinanceSummarySerializer
)


class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    """
    Xarajat kategoriyalari CRUD
    """
    queryset = ExpenseCategory.objects.all()
    serializer_class = ExpenseCategorySerializer
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [SearchFilter]
    search_fields = ['name']

    role_permissions = {
        'list': ['owner', 'admin', 'accountant'],
        'retrieve': ['owner', 'admin', 'accountant'],
        'create': ['owner', 'admin'],
        'update': ['owner', 'admin'],
        'partial_update': ['owner', 'admin'],
        'destroy': ['owner'],
    }


class ExpenseViewSet(viewsets.ModelViewSet):
    """
    Xarajatlar CRUD
    """
    queryset = Expense.objects.select_related('category', 'created_by', 'approved_by').all()
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'status', 'is_recurring']
    search_fields = ['title', 'description']
    ordering_fields = ['amount', 'expense_date', 'created_at']
    ordering = ['-expense_date']

    role_permissions = {
        'list': ['owner', 'admin', 'accountant'],
        'retrieve': ['owner', 'admin', 'accountant'],
        'create': ['owner', 'admin', 'accountant'],
        'update': ['owner', 'admin'],
        'partial_update': ['owner', 'admin'],
        'destroy': ['owner'],
        'approve': ['owner', 'admin'],
        'statistics': ['owner', 'admin', 'accountant'],
    }

    def get_serializer_class(self):
        if self.action == 'list':
            return ExpenseListSerializer
        if self.action == 'create':
            return ExpenseCreateSerializer
        return ExpenseSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if start_date:
            queryset = queryset.filter(expense_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(expense_date__lte=end_date)

        return queryset

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Xarajatni tasdiqlash"""
        expense = self.get_object()

        if expense.status != 'pending':
            return Response({
                'success': False,
                'error': {'code': 'INVALID_STATUS', 'message': 'Faqat kutilayotgan xarajatni tasdiqlash mumkin'}
            }, status=status.HTTP_400_BAD_REQUEST)

        expense.status = 'approved'
        expense.approved_by = request.user
        expense.save()

        return Response({
            'success': True,
            'message': 'Xarajat tasdiqlandi',
            'data': ExpenseSerializer(expense).data
        })

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Xarajatlar statistikasi"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not start_date:
            start_date = timezone.now().date().replace(day=1)
        if not end_date:
            end_date = timezone.now().date()

        expenses = Expense.objects.filter(
            status='paid',
            expense_date__gte=start_date,
            expense_date__lte=end_date
        )

        total = expenses.aggregate(total=Sum('amount'))['total'] or 0

        by_category = expenses.values(
            'category__name', 'category__color'
        ).annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')

        return Response({
            'success': True,
            'data': {
                'period': {'start': str(start_date), 'end': str(end_date)},
                'total': total,
                'count': expenses.count(),
                'by_category': list(by_category)
            }
        })


class TransactionViewSet(viewsets.ModelViewSet):
    """
    Tranzaksiyalar (faqat o'qish)
    """
    queryset = Transaction.objects.select_related('created_by').all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['transaction_type']
    ordering = ['-transaction_date', '-created_at']
    http_method_names = ['get']  # Faqat o'qish

    role_permissions = {
        'list': ['owner', 'admin', 'accountant'],
        'retrieve': ['owner', 'admin', 'accountant'],
    }

    def get_queryset(self):
        queryset = super().get_queryset()

        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if start_date:
            queryset = queryset.filter(transaction_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(transaction_date__lte=end_date)

        return queryset


class SalaryViewSet(viewsets.ModelViewSet):
    """
    Ish haqlari CRUD
    """
    queryset = Salary.objects.select_related('teacher', 'approved_by', 'paid_by').all()
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['teacher', 'status', 'period_month', 'period_year']
    ordering = ['-period_year', '-period_month']

    role_permissions = {
        'list': ['owner', 'admin', 'accountant'],
        'retrieve': ['owner', 'admin', 'accountant'],
        'create': ['owner', 'admin', 'accountant'],
        'update': ['owner', 'admin'],
        'partial_update': ['owner', 'admin'],
        'destroy': ['owner'],
        'calculate': ['owner', 'admin', 'accountant'],
        'approve': ['owner', 'admin'],
        'pay': ['owner', 'admin'],
    }

    def get_serializer_class(self):
        if self.action == 'list':
            return SalaryListSerializer
        if self.action == 'calculate':
            return SalaryCalculateSerializer
        return SalarySerializer

    @action(detail=False, methods=['post'])
    def calculate(self, request):
        """
        Ish haqini hisoblash

        POST /api/v1/salaries/calculate/
        {
            "month": 1,
            "year": 2024,
            "teacher_id": "uuid" (optional)
        }
        """
        serializer = SalaryCalculateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        month = serializer.validated_data['month']
        year = serializer.validated_data['year']
        teacher_id = serializer.validated_data.get('teacher_id')

        teachers = Teacher.objects.filter(status='active')
        if teacher_id:
            teachers = teachers.filter(id=teacher_id)

        created_count = 0
        updated_count = 0
        results = []

        for teacher in teachers:
            # Allaqachon bor-yo'qligini tekshirish
            salary, created = Salary.objects.get_or_create(
                teacher=teacher,
                period_month=month,
                period_year=year,
                defaults={
                    'base_salary': 0,
                    'total': 0,
                    'status': 'calculated'
                }
            )

            # Hisoblash
            calculation = self._calculate_teacher_salary(teacher, month, year)

            salary.base_salary = calculation['base_salary']
            salary.total_lessons = calculation['total_lessons']
            salary.total_students = calculation['total_students']
            salary.calculation_details = calculation['details']
            salary.total = calculation['base_salary'] + salary.bonus - salary.deduction
            salary.save()

            if created:
                created_count += 1
            else:
                updated_count += 1

            results.append(SalaryListSerializer(salary).data)

        return Response({
            'success': True,
            'message': f"{created_count} ta yangi, {updated_count} ta yangilandi",
            'data': {
                'created': created_count,
                'updated': updated_count,
                'salaries': results
            }
        })

    def _calculate_teacher_salary(self, teacher, month, year):
        """O'qituvchi ish haqini hisoblash"""
        from django.db.models import Count

        # O'qituvchining guruhlari
        groups = Group.objects.filter(teacher=teacher, status='active')

        total_lessons = 0
        total_students = 0
        base_salary = Decimal('0')
        details = {'groups': []}

        for group in groups:
            # Shu oydagi darslar soni (attendance sessions)
            lessons = Attendance.objects.filter(
                group=group,
                date__year=year,
                date__month=month
            ).values('date').distinct().count()

            # Guruhda o'quvchilar soni
            students = GroupStudent.objects.filter(
                group=group,
                is_active=True
            ).count()

            total_lessons += lessons
            total_students += students

            # Ish haqi hisoblash
            if teacher.salary_type == 'fixed':
                # Belgilangan ish haqi (guruhlarga bo'linadi)
                group_salary = teacher.salary_amount / max(groups.count(), 1)
            elif teacher.salary_type == 'hourly':
                # Soatlik
                group_salary = teacher.salary_amount * lessons
            elif teacher.salary_type == 'percent':
                # Foizli - guruh daromadidan
                group_income = group.actual_price * students
                group_salary = group_income * (teacher.salary_percent / 100)
            else:
                group_salary = Decimal('0')

            base_salary += group_salary

            details['groups'].append({
                'group_id': str(group.id),
                'group_name': group.name,
                'lessons': lessons,
                'students': students,
                'salary': float(group_salary)
            })

        return {
            'base_salary': base_salary,
            'total_lessons': total_lessons,
            'total_students': total_students,
            'details': details
        }

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Ish haqini tasdiqlash"""
        salary = self.get_object()

        if salary.status != 'calculated':
            return Response({
                'success': False,
                'error': {'code': 'INVALID_STATUS', 'message': 'Faqat hisoblangan ish haqini tasdiqlash mumkin'}
            }, status=status.HTTP_400_BAD_REQUEST)

        salary.status = 'approved'
        salary.approved_by = request.user
        salary.approved_at = timezone.now()
        salary.save()

        return Response({
            'success': True,
            'message': 'Ish haqi tasdiqlandi',
            'data': SalarySerializer(salary).data
        })

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        """Ish haqini to'lash"""
        salary = self.get_object()

        if salary.status != 'approved':
            return Response({
                'success': False,
                'error': {'code': 'INVALID_STATUS', 'message': 'Faqat tasdiqlangan ish haqini to\'lash mumkin'}
            }, status=status.HTTP_400_BAD_REQUEST)

        salary.status = 'paid'
        salary.paid_by = request.user
        salary.paid_at = timezone.now()
        salary.save()

        # Tranzaksiya yaratish
        Transaction.objects.create(
            transaction_type='salary',
            amount=salary.total,
            transaction_date=timezone.now().date(),
            description=f"Ish haqi: {salary.teacher.full_name} - {salary.period_month}/{salary.period_year}",
            salary=salary,
            created_by=request.user
        )

        return Response({
            'success': True,
            'message': 'Ish haqi to\'landi',
            'data': SalarySerializer(salary).data
        })


class FinanceDashboardView(viewsets.ViewSet):
    """
    Moliyaviy dashboard
    """
    permission_classes = [IsAuthenticated, RoleBasedPermission]

    role_permissions = {
        'summary': ['owner', 'admin', 'accountant'],
        'monthly_report': ['owner', 'admin', 'accountant'],
        'profit_loss': ['owner', 'accountant'],
    }

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Moliyaviy xulosa — joriy oy, o'tgan oy va umumiy (all-time) ma'lumotlar.

        GET /api/v1/finance/dashboard/summary/?period=month
        """
        from apps.billing.models import Invoice

        period = request.query_params.get('period', 'month')
        today = timezone.now().date()

        if period == 'today':
            start_date = today
            end_date = today
            prev_start = today - timedelta(days=1)
            prev_end = today - timedelta(days=1)
        elif period == 'week':
            start_date = today - timedelta(days=7)
            end_date = today
            prev_start = today - timedelta(days=14)
            prev_end = today - timedelta(days=8)
        elif period == 'year':
            start_date = today.replace(month=1, day=1)
            end_date = today
            prev_start = start_date.replace(year=start_date.year - 1)
            prev_end = today.replace(year=today.year - 1)
        else:
            # month (default)
            start_date = today.replace(day=1)
            end_date = today
            if start_date.month == 1:
                prev_start = start_date.replace(year=start_date.year - 1, month=12, day=1)
            else:
                prev_start = start_date.replace(month=start_date.month - 1)
            # Previous period end = last day of previous month
            prev_end = start_date - timedelta(days=1)

        def _totals(s, e):
            income = Payment.objects.filter(
                status='completed',
                created_at__date__gte=s,
                created_at__date__lte=e,
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            expense = Expense.objects.filter(
                status='paid',
                expense_date__gte=s,
                expense_date__lte=e,
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            salary = Salary.objects.filter(
                status='paid',
                paid_at__date__gte=s,
                paid_at__date__lte=e,
            ).aggregate(total=Sum('total'))['total'] or Decimal('0')
            return income, expense, salary

        total_income, total_expense, total_salary = _totals(start_date, end_date)
        net_profit = total_income - total_expense - total_salary

        prev_income, prev_expense, prev_salary = _totals(prev_start, prev_end)
        prev_profit = prev_income - prev_expense - prev_salary

        # Umumiy (all-time)
        at_income = Payment.objects.filter(status='completed').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        at_expense = Expense.objects.filter(status='paid').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        at_salary = Salary.objects.filter(status='paid').aggregate(t=Sum('total'))['t'] or Decimal('0')

        # Kutilayotgan / qarz (invoice asosida, barcha faol invoicelar)
        inv_qs = Invoice.objects.exclude(status=Invoice.Status.CANCELLED)
        inv_expected = inv_qs.aggregate(t=Sum('total_amount'))['t'] or Decimal('0')
        inv_collected = inv_qs.aggregate(t=Sum('paid_amount'))['t'] or Decimal('0')

        def _delta_pct(curr, prev):
            if prev and prev != 0:
                return round(float((curr - prev) / abs(prev) * 100), 1)
            return None

        return Response({
            'success': True,
            'data': {
                'period': {'start': str(start_date), 'end': str(end_date)},
                'previous_period': {'start': str(prev_start), 'end': str(prev_end)},
                'total_income': total_income,
                'total_expense': total_expense,
                'total_salary': total_salary,
                'net_profit': net_profit,
                'profit_margin': round(
                    (net_profit / total_income * 100) if total_income > 0 else 0, 2
                ),
                'previous': {
                    'total_income': prev_income,
                    'total_expense': prev_expense,
                    'total_salary': prev_salary,
                    'net_profit': prev_profit,
                },
                'trend': {
                    'income_pct': _delta_pct(total_income, prev_income),
                    'expense_pct': _delta_pct(total_expense, prev_expense),
                    'salary_pct': _delta_pct(total_salary, prev_salary),
                    'profit_pct': _delta_pct(net_profit, prev_profit),
                },
                'all_time': {
                    'total_income': at_income,
                    'total_expense': at_expense,
                    'total_salary': at_salary,
                    'net_profit': at_income - at_expense - at_salary,
                },
                'expected_income': inv_expected,
                'total_debt': inv_expected - inv_collected,
            }
        })

    @action(detail=False, methods=['get'])
    def monthly_report(self, request):
        """
        Oylik hisobot

        GET /api/v1/finance/dashboard/monthly_report/?year=2024
        """
        year = request.query_params.get('year', timezone.now().year)

        months = []
        for month in range(1, 13):
            income = Payment.objects.filter(
                status='completed',
                created_at__year=year,
                created_at__month=month
            ).aggregate(total=Sum('amount'))['total'] or 0

            expense = Expense.objects.filter(
                status='paid',
                expense_date__year=year,
                expense_date__month=month
            ).aggregate(total=Sum('amount'))['total'] or 0

            salary = Salary.objects.filter(
                status='paid',
                period_year=year,
                period_month=month
            ).aggregate(total=Sum('total'))['total'] or 0

            months.append({
                'month': month,
                'income': income,
                'expense': expense,
                'salary': salary,
                'profit': income - expense - salary
            })

        return Response({
            'success': True,
            'data': {
                'year': year,
                'months': months
            }
        })