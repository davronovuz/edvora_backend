"""
Edvora - Analytics Views
Dashboard va hisobotlar
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from core.permissions import RoleBasedPermission
from apps.students.models import Student
from apps.teachers.models import Teacher
from apps.groups.models import Group, GroupStudent
from apps.payments.models import Payment
from apps.finance.models import Expense, Salary
from apps.attendance.models import Attendance
from apps.leads.models import Lead
from apps.billing.models import Invoice
from .models import DailyStats, MonthlyStats
from .serializers import (
    DailyStatsSerializer,
    MonthlyStatsSerializer,
    DashboardSummarySerializer
)


class DashboardViewSet(viewsets.ViewSet):
    """
    Dashboard API
    """
    permission_classes = [IsAuthenticated, RoleBasedPermission]

    role_permissions = {
        'summary': ['owner', 'admin', 'teacher', 'accountant', 'registrar'],
        'students_chart': ['owner', 'admin'],
        'finance_chart': ['owner', 'admin', 'accountant'],
        'attendance_chart': ['owner', 'admin', 'teacher'],
        'leads_chart': ['owner', 'admin', 'registrar'],
        'recent_activity': ['owner', 'admin'],
        'top_groups': ['owner', 'admin'],
        'debtors_summary': ['owner', 'admin', 'accountant'],
        'billing_chart': ['owner', 'admin', 'accountant'],
        'billing_debtors': ['owner', 'admin', 'accountant'],
        'billing_summary': ['owner', 'admin', 'accountant'],
    }

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Dashboard umumiy ko'rsatkichlar

        GET /api/v1/analytics/dashboard/summary/
        """
        user = request.user
        today = timezone.now().date()
        month_start = today.replace(day=1)

        # Teacher uchun alohida summary
        if user.role == 'teacher':
            return self._teacher_summary(user, today, month_start)

        # O'quvchilar
        students_total = Student.objects.count()
        students_active = Student.objects.filter(status='active').count()
        students_new = Student.objects.filter(created_at__date__gte=month_start).count()
        students_with_debt = Student.objects.filter(balance__lt=0).count()

        # Guruhlar
        groups_total = Group.objects.count()
        groups_active = Group.objects.filter(status='active').count()

        # O'qituvchilar
        teachers_total = Teacher.objects.count()
        teachers_active = Teacher.objects.filter(status='active').count()

        # Moliya (shu oy)
        income = Payment.objects.filter(
            status='completed',
            created_at__date__gte=month_start
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        expense = Expense.objects.filter(
            status='paid',
            expense_date__gte=month_start
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        salary = Salary.objects.filter(
            status='paid',
            period_year=today.year,
            period_month=today.month
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')

        # Leadlar (shu oy)
        leads_total = Lead.objects.filter(created_at__date__gte=month_start).count()
        leads_converted = Lead.objects.filter(
            status='converted',
            converted_at__date__gte=month_start
        ).count()

        # Davomat (bugun)
        today_attendance = Attendance.objects.filter(date=today)
        attendance_total = today_attendance.count()
        attendance_present = today_attendance.filter(
            status__in=['present', 'late']
        ).count()
        attendance_rate = round(
            (attendance_present / attendance_total * 100) if attendance_total > 0 else 0, 1
        )

        # Billing — joriy oy uchun kutilayotgan/yig'ilgan,
        # qarz esa barcha to'lanmagan invoicelardan hisoblanadi.
        from django.db.models import F
        billing_month_qs = Invoice.objects.filter(
            period_year=today.year, period_month=today.month,
        ).exclude(status=Invoice.Status.CANCELLED)

        billing_expected = billing_month_qs.aggregate(s=Sum('total_amount'))['s'] or Decimal('0')
        billing_collected = billing_month_qs.aggregate(s=Sum('paid_amount'))['s'] or Decimal('0')

        # Barcha ochiq invoicelar bo'yicha qarz (oyga bog'liq emas)
        billing_debt = Invoice.objects.filter(
            status__in=[Invoice.Status.UNPAID, Invoice.Status.PARTIAL, Invoice.Status.OVERDUE],
        ).aggregate(
            t=Sum(F('total_amount') - F('paid_amount'))
        )['t'] or Decimal('0')

        billing_overdue = Invoice.objects.filter(
            status=Invoice.Status.OVERDUE,
        ).count()
        billing_collection_rate = round(
            float(billing_collected / billing_expected * 100) if billing_expected > 0 else 0, 1
        )

        return Response({
            'success': True,
            'data': {
                'students': {
                    'total': students_total,
                    'active': students_active,
                    'new_this_month': students_new,
                    'with_debt': students_with_debt
                },
                'groups': {
                    'total': groups_total,
                    'active': groups_active
                },
                'teachers': {
                    'total': teachers_total,
                    'active': teachers_active
                },
                'finance': {
                    'income': income,
                    'expense': expense,
                    'salary': salary,
                    'profit': income - expense - salary
                },
                'billing': {
                    'expected': billing_expected,
                    'collected': billing_collected,
                    'debt': billing_debt,
                    'collection_rate': billing_collection_rate,
                    'overdue_count': billing_overdue,
                },
                'leads': {
                    'total': leads_total,
                    'converted': leads_converted,
                    'conversion_rate': round(
                        (leads_converted / leads_total * 100) if leads_total > 0 else 0, 1
                    )
                },
                'attendance': {
                    'today_total': attendance_total,
                    'today_present': attendance_present,
                    'rate': attendance_rate
                }
            }
        })

    def _teacher_summary(self, user, today, month_start):
        """Teacher uchun maxsus dashboard summary"""
        teacher_profile = getattr(user, 'teacher_profile', None)

        if not teacher_profile:
            return Response({
                'success': True,
                'data': {
                    'is_teacher': True,
                    'no_profile': True,
                    'my_groups': [],
                    'groups': {'total': 0, 'active': 0},
                    'students': {'total': 0},
                    'attendance': {'today_total': 0, 'today_present': 0, 'rate': 0},
                }
            })

        # O'z guruhlari
        my_groups = Group.objects.filter(teacher=teacher_profile, status='active')
        my_group_ids = list(my_groups.values_list('id', flat=True))

        # O'z o'quvchilari
        my_students_count = GroupStudent.objects.filter(
            group__in=my_groups, is_active=True
        ).values('student').distinct().count()

        # Bugungi davomat (faqat o'z guruhlari)
        today_att = Attendance.objects.filter(date=today, group__in=my_groups)
        att_total = today_att.count()
        att_present = today_att.filter(status__in=['present', 'late']).count()
        att_rate = round((att_present / att_total * 100) if att_total > 0 else 0, 1)

        # Shu oydagi davomat umumiy
        month_att = Attendance.objects.filter(
            date__gte=month_start, date__lte=today, group__in=my_groups
        )
        month_att_total = month_att.count()
        month_att_present = month_att.filter(status__in=['present', 'late']).count()
        month_rate = round((month_att_present / month_att_total * 100) if month_att_total > 0 else 0, 1)

        # Guruhlar tafsiloti
        groups_data = []
        for g in my_groups.select_related('course', 'room'):
            g_students = GroupStudent.objects.filter(group=g, is_active=True).count()
            g_att = Attendance.objects.filter(date=today, group=g)
            g_att_total = g_att.count()
            g_att_present = g_att.filter(status__in=['present', 'late']).count()
            g_marked = g_att_total > 0

            groups_data.append({
                'id': str(g.id),
                'name': g.name,
                'course_name': g.course.name if g.course else '',
                'room_name': g.room.name if g.room else '',
                'students_count': g_students,
                'max_students': g.max_students,
                'days': g.days,
                'start_time': str(g.start_time) if g.start_time else '',
                'end_time': str(g.end_time) if g.end_time else '',
                'today_marked': g_marked,
                'today_present': g_att_present,
                'today_total': g_att_total,
            })

        return Response({
            'success': True,
            'data': {
                'is_teacher': True,
                'groups': {
                    'total': my_groups.count(),
                    'active': my_groups.count(),
                },
                'students': {
                    'total': my_students_count,
                },
                'attendance': {
                    'today_total': att_total,
                    'today_present': att_present,
                    'rate': att_rate,
                    'month_rate': month_rate,
                },
                'my_groups': groups_data,
            }
        })

    @action(detail=False, methods=['get'])
    def students_chart(self, request):
        """
        O'quvchilar dinamikasi (oxirgi 12 oy)

        GET /api/v1/analytics/dashboard/students_chart/
        """
        today = timezone.now().date()
        labels = []
        data = []

        for i in range(11, -1, -1):
            # i oy oldin
            if today.month - i > 0:
                year = today.year
                month = today.month - i
            else:
                year = today.year - 1
                month = today.month - i + 12

            month_name = f"{month:02d}/{year}"
            labels.append(month_name)

            # Shu oygacha bo'lgan faol o'quvchilar
            count = Student.objects.filter(
                created_at__year__lte=year,
                created_at__month__lte=month if year == today.year else 12,
                status='active'
            ).count()
            data.append(count)

        return Response({
            'success': True,
            'data': {
                'labels': labels,
                'datasets': [{
                    'label': "O'quvchilar soni",
                    'data': data
                }]
            }
        })

    @action(detail=False, methods=['get'])
    def finance_chart(self, request):
        """
        Moliya dinamikasi (oxirgi 12 oy)

        GET /api/v1/analytics/dashboard/finance_chart/
        """
        today = timezone.now().date()
        labels = []
        income_data = []
        expense_data = []
        profit_data = []

        for i in range(11, -1, -1):
            if today.month - i > 0:
                year = today.year
                month = today.month - i
            else:
                year = today.year - 1
                month = today.month - i + 12

            month_name = f"{month:02d}/{year}"
            labels.append(month_name)

            # Daromad
            income = Payment.objects.filter(
                status='completed',
                created_at__year=year,
                created_at__month=month
            ).aggregate(total=Sum('amount'))['total'] or 0

            # Xarajat
            expense = Expense.objects.filter(
                status='paid',
                expense_date__year=year,
                expense_date__month=month
            ).aggregate(total=Sum('amount'))['total'] or 0

            # Ish haqi
            salary = Salary.objects.filter(
                status='paid',
                period_year=year,
                period_month=month
            ).aggregate(total=Sum('total'))['total'] or 0

            income_data.append(float(income))
            expense_data.append(float(expense + salary))
            profit_data.append(float(income - expense - salary))

        return Response({
            'success': True,
            'data': {
                'labels': labels,
                'datasets': [
                    {'label': 'Daromad', 'data': income_data},
                    {'label': 'Xarajat', 'data': expense_data},
                    {'label': 'Foyda', 'data': profit_data}
                ]
            }
        })

    @action(detail=False, methods=['get'])
    def attendance_chart(self, request):
        """
        Davomat dinamikasi (oxirgi 30 kun)

        GET /api/v1/analytics/dashboard/attendance_chart/
        """
        today = timezone.now().date()
        labels = []
        data = []

        for i in range(29, -1, -1):
            date = today - timedelta(days=i)
            labels.append(date.strftime('%d.%m'))

            attendance = Attendance.objects.filter(date=date)
            total = attendance.count()
            present = attendance.filter(status__in=['present', 'late']).count()

            rate = round((present / total * 100) if total > 0 else 0, 1)
            data.append(rate)

        return Response({
            'success': True,
            'data': {
                'labels': labels,
                'datasets': [{
                    'label': 'Davomat %',
                    'data': data
                }]
            }
        })

    @action(detail=False, methods=['get'])
    def leads_chart(self, request):
        """
        Leadlar statistikasi

        GET /api/v1/analytics/dashboard/leads_chart/
        """
        # Status bo'yicha
        by_status = Lead.objects.values('status').annotate(count=Count('id'))

        # Manba bo'yicha
        by_source = Lead.objects.values('source').annotate(count=Count('id'))

        return Response({
            'success': True,
            'data': {
                'by_status': list(by_status),
                'by_source': list(by_source)
            }
        })

    @action(detail=False, methods=['get'])
    def recent_activity(self, request):
        """
        So'nggi faoliyatlar

        GET /api/v1/analytics/dashboard/recent_activity/
        """
        activities = []

        # So'nggi to'lovlar
        recent_payments = Payment.objects.filter(
            status='completed'
        ).select_related('student').order_by('-created_at')[:5]

        for p in recent_payments:
            activities.append({
                'type': 'payment',
                'title': f"To'lov qabul qilindi",
                'description': f"{p.student.full_name} - {p.amount:,.0f} so'm",
                'time': p.created_at
            })

        # So'nggi o'quvchilar
        recent_students = Student.objects.order_by('-created_at')[:5]

        for s in recent_students:
            activities.append({
                'type': 'student',
                'title': "Yangi o'quvchi",
                'description': s.full_name,
                'time': s.created_at
            })

        # So'nggi leadlar
        recent_leads = Lead.objects.order_by('-created_at')[:5]

        for l in recent_leads:
            activities.append({
                'type': 'lead',
                'title': 'Yangi lead',
                'description': f"{l.full_name} - {l.get_source_display()}",
                'time': l.created_at
            })

        # Vaqt bo'yicha saralash
        activities.sort(key=lambda x: x['time'], reverse=True)

        return Response({
            'success': True,
            'data': activities[:15]
        })

    @action(detail=False, methods=['get'])
    def top_groups(self, request):
        """
        Eng yaxshi guruhlar

        GET /api/v1/analytics/dashboard/top_groups/
        """
        groups = Group.objects.filter(status='active').select_related('course', 'teacher').annotate(
            active_students=Count('students', filter=Q(students__is_active=True))
        ).order_by('-active_students')[:10]

        data = []
        for g in groups:
            data.append({
                'id': str(g.id),
                'name': g.name,
                'course': g.course.name if g.course else '',
                'teacher': g.teacher.full_name if g.teacher else None,
                'students_count': g.active_students,
                'max_students': g.max_students,
                'fill_rate': round((g.active_students / g.max_students * 100) if g.max_students > 0 else 0, 1)
            })

        return Response({
            'success': True,
            'data': data
        })

    @action(detail=False, methods=['get'])
    def debtors_summary(self, request):
        """
        Qarzdorlar xulosasi

        GET /api/v1/analytics/dashboard/debtors_summary/
        """
        debtors = Student.objects.filter(balance__lt=0, status='active')

        total_debt = debtors.aggregate(total=Sum('balance'))['total'] or 0

        # Qarz bo'yicha guruhlash
        ranges = [
            {'min': -500000, 'max': 0, 'label': '0 - 500K'},
            {'min': -1000000, 'max': -500000, 'label': '500K - 1M'},
            {'min': -2000000, 'max': -1000000, 'label': '1M - 2M'},
            {'min': None, 'max': -2000000, 'label': '2M+'},
        ]

        by_range = []
        for r in ranges:
            q = debtors
            if r['min'] is not None:
                q = q.filter(balance__gte=r['min'])
            if r['max'] is not None:
                q = q.filter(balance__lt=r['max'])

            by_range.append({
                'label': r['label'],
                'count': q.count()
            })

        return Response({
            'success': True,
            'data': {
                'total_debtors': debtors.count(),
                'total_debt': abs(total_debt),
                'by_range': by_range
            }
        })

    @action(detail=False, methods=['get'])
    def billing_chart(self, request):
        """
        Billing dinamikasi (oxirgi 12 oy) — Invoice asosida.

        GET /api/v1/analytics/dashboard/billing_chart/
        """
        from django.db.models import F

        today = timezone.now().date()
        labels = []
        expected_data = []
        collected_data = []
        debt_data = []

        for i in range(11, -1, -1):
            if today.month - i > 0:
                year = today.year
                month = today.month - i
            else:
                year = today.year - 1
                month = today.month - i + 12

            labels.append(f"{month:02d}/{year}")

            qs = Invoice.objects.filter(
                period_year=year, period_month=month,
            ).exclude(status=Invoice.Status.CANCELLED)

            agg = qs.aggregate(
                expected=Sum('total_amount'),
                collected=Sum('paid_amount'),
            )
            expected = float(agg['expected'] or 0)
            collected = float(agg['collected'] or 0)

            expected_data.append(expected)
            collected_data.append(collected)
            debt_data.append(expected - collected)

        return Response({
            'success': True,
            'data': {
                'labels': labels,
                'datasets': [
                    {'label': 'Kutilayotgan', 'data': expected_data},
                    {'label': 'Yig\'ilgan', 'data': collected_data},
                    {'label': 'Qarz', 'data': debt_data},
                ]
            }
        })

    @action(detail=False, methods=['get'])
    def billing_debtors(self, request):
        """
        Invoice-based qarzdorlar (batafsil).

        GET /api/v1/analytics/dashboard/billing_debtors/
        """
        from django.db.models import F

        debtors = (
            Invoice.objects
            .filter(status__in=[
                Invoice.Status.UNPAID,
                Invoice.Status.PARTIAL,
                Invoice.Status.OVERDUE,
            ])
            .values(
                'student__id', 'student__first_name', 'student__last_name',
                'student__phone',
            )
            .annotate(
                total_debt=Sum(F('total_amount') - F('paid_amount')),
                invoice_count=Count('id'),
                overdue_count=Count('id', filter=Q(status=Invoice.Status.OVERDUE)),
            )
            .filter(total_debt__gt=0)
            .order_by('-total_debt')[:50]
        )

        # Umumiy statistika
        total_debt = sum(d['total_debt'] for d in debtors)
        total_debtors = len(debtors)

        # Qarz diapazonlari
        ranges = [
            {'min': 0, 'max': 500000, 'label': '0 - 500K'},
            {'min': 500000, 'max': 1000000, 'label': '500K - 1M'},
            {'min': 1000000, 'max': 2000000, 'label': '1M - 2M'},
            {'min': 2000000, 'max': None, 'label': '2M+'},
        ]
        by_range = []
        for r in ranges:
            count = sum(
                1 for d in debtors
                if d['total_debt'] >= r['min']
                and (r['max'] is None or d['total_debt'] < r['max'])
            )
            by_range.append({'label': r['label'], 'count': count})

        return Response({
            'success': True,
            'data': {
                'total_debtors': total_debtors,
                'total_debt': float(total_debt),
                'by_range': by_range,
                'debtors': list(debtors),
            }
        })

    @action(detail=False, methods=['get'])
    def billing_summary(self, request):
        """
        Oylik billing xulosasi (batafsil).

        GET /api/v1/analytics/dashboard/billing_summary/?year=2026&month=4
        """
        year = int(request.query_params.get('year', timezone.now().year))
        month = int(request.query_params.get('month', timezone.now().month))

        qs = Invoice.objects.filter(
            period_year=year, period_month=month,
        ).exclude(status=Invoice.Status.CANCELLED)

        agg = qs.aggregate(
            expected=Sum('total_amount'),
            collected=Sum('paid_amount'),
            discount=Sum('discount_amount'),
            leave_credit=Sum('leave_credit_amount'),
            late_fee=Sum('late_fee_amount'),
            base=Sum('base_amount'),
        )

        total_expected = agg['expected'] or Decimal('0')
        total_collected = agg['collected'] or Decimal('0')

        # Status bo'yicha
        by_status = {}
        for s_value, s_label in Invoice.Status.choices:
            if s_value == Invoice.Status.CANCELLED:
                continue
            cnt = qs.filter(status=s_value).count()
            if cnt > 0:
                by_status[s_value] = cnt

        # Guruh bo'yicha top 10 qarzlar
        from django.db.models import F
        by_group = list(
            qs.values('group__id', 'group__name')
            .annotate(
                group_expected=Sum('total_amount'),
                group_collected=Sum('paid_amount'),
                group_debt=Sum(F('total_amount') - F('paid_amount')),
                student_count=Count('student', distinct=True),
            )
            .filter(group_debt__gt=0)
            .order_by('-group_debt')[:10]
        )

        return Response({
            'success': True,
            'data': {
                'period': f"{year}-{month:02d}",
                'base_total': str(agg['base'] or 0),
                'discount_total': str(agg['discount'] or 0),
                'leave_credit_total': str(agg['leave_credit'] or 0),
                'late_fee_total': str(agg['late_fee'] or 0),
                'expected': str(total_expected),
                'collected': str(total_collected),
                'debt': str(total_expected - total_collected),
                'collection_rate': round(
                    float(total_collected / total_expected * 100)
                    if total_expected > 0 else 0, 1
                ),
                'by_status': by_status,
                'by_group': by_group,
            }
        })


class ReportViewSet(viewsets.ViewSet):
    """
    Hisobotlar API
    """
    permission_classes = [IsAuthenticated, RoleBasedPermission]

    role_permissions = {
        'students_report': ['owner', 'admin'],
        'finance_report': ['owner', 'accountant'],
        'attendance_report': ['owner', 'admin', 'teacher'],
        'teachers_report': ['owner', 'admin'],
        'lead_conversion': ['owner', 'admin', 'registrar'],
        'teacher_performance': ['owner', 'admin'],
        'write_off_report': ['owner', 'admin', 'accountant'],
    }

    @action(detail=False, methods=['get'])
    def students_report(self, request):
        """
        O'quvchilar hisoboti

        GET /api/v1/analytics/reports/students_report/?start_date=2024-01-01&end_date=2024-01-31
        """
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not start_date or not end_date:
            return Response({
                'success': False,
                'error': {'code': 'MISSING_PARAM', 'message': 'start_date va end_date kerak'}
            }, status=status.HTTP_400_BAD_REQUEST)

        # Yangi o'quvchilar
        new_students = Student.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).count()

        # Chiqib ketganlar
        dropped = Student.objects.filter(
            status='dropped',
            updated_at__date__gte=start_date,
            updated_at__date__lte=end_date
        ).count()

        # Manba bo'yicha
        by_source = Student.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).values('source').annotate(count=Count('id'))

        return Response({
            'success': True,
            'data': {
                'period': {'start': start_date, 'end': end_date},
                'new_students': new_students,
                'dropped_students': dropped,
                'net_growth': new_students - dropped,
                'by_source': list(by_source)
            }
        })

    @action(detail=False, methods=['get'])
    def finance_report(self, request):
        """
        Moliya hisoboti

        GET /api/v1/analytics/reports/finance_report/?year=2024&month=1
        """
        year = request.query_params.get('year', timezone.now().year)
        month = request.query_params.get('month', timezone.now().month)

        # Daromad
        income = Payment.objects.filter(
            status='completed',
            created_at__year=year,
            created_at__month=month
        ).aggregate(total=Sum('amount'))['total'] or 0

        # To'lov usullari bo'yicha
        income_by_method = Payment.objects.filter(
            status='completed',
            created_at__year=year,
            created_at__month=month
        ).values('payment_method').annotate(total=Sum('amount'))

        # Xarajatlar
        expense = Expense.objects.filter(
            status='paid',
            expense_date__year=year,
            expense_date__month=month
        ).aggregate(total=Sum('amount'))['total'] or 0

        # Kategoriya bo'yicha
        expense_by_category = Expense.objects.filter(
            status='paid',
            expense_date__year=year,
            expense_date__month=month
        ).values('category__name').annotate(total=Sum('amount'))

        # Ish haqlari
        salary = Salary.objects.filter(
            status='paid',
            period_year=year,
            period_month=month
        ).aggregate(total=Sum('total'))['total'] or 0

        return Response({
            'success': True,
            'data': {
                'period': {'year': year, 'month': month},
                'income': {
                    'total': income,
                    'by_method': list(income_by_method)
                },
                'expense': {
                    'total': expense,
                    'by_category': list(expense_by_category)
                },
                'salary': salary,
                'net_profit': income - expense - salary
            }
        })

    @action(detail=False, methods=['get'])
    def attendance_report(self, request):
        """
        Davomat hisoboti

        GET /api/v1/analytics/reports/attendance_report/?group_id=uuid&start_date=2024-01-01&end_date=2024-01-31
        """
        group_id = request.query_params.get('group_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not all([group_id, start_date, end_date]):
            return Response({
                'success': False,
                'error': {'code': 'MISSING_PARAM', 'message': 'group_id, start_date, end_date kerak'}
            }, status=status.HTTP_400_BAD_REQUEST)

        group = Group.objects.get(id=group_id)

        attendances = Attendance.objects.filter(
            group=group,
            date__gte=start_date,
            date__lte=end_date
        )

        total = attendances.count()
        present = attendances.filter(status='present').count()
        late = attendances.filter(status='late').count()
        absent = attendances.filter(status='absent').count()
        excused = attendances.filter(status='excused').count()

        # O'quvchi bo'yicha
        by_student = attendances.values(
            'student__id', 'student__first_name', 'student__last_name'
        ).annotate(
            total=Count('id'),
            present=Count('id', filter=Q(status='present')),
            late=Count('id', filter=Q(status='late')),
            absent=Count('id', filter=Q(status='absent'))
        )

        return Response({
            'success': True,
            'data': {
                'group': {'id': str(group.id), 'name': group.name},
                'period': {'start': start_date, 'end': end_date},
                'summary': {
                    'total': total,
                    'present': present,
                    'late': late,
                    'absent': absent,
                    'excused': excused,
                    'attendance_rate': round((present + late) / total * 100 if total > 0 else 0, 1)
                },
                'by_student': list(by_student)
            }
        })

    @action(detail=False, methods=['get'])
    def teachers_report(self, request):
        """
        O'qituvchilar hisoboti

        GET /api/v1/analytics/reports/teachers_report/?year=2024&month=1
        """
        year = request.query_params.get('year', timezone.now().year)
        month = request.query_params.get('month', timezone.now().month)

        teachers = Teacher.objects.filter(status='active')

        data = []
        for teacher in teachers:
            groups = Group.objects.filter(teacher=teacher, status='active')
            students = GroupStudent.objects.filter(
                group__in=groups,
                is_active=True
            ).count()

            salary = Salary.objects.filter(
                teacher=teacher,
                period_year=year,
                period_month=month
            ).first()

            data.append({
                'teacher_id': str(teacher.id),
                'teacher_name': teacher.full_name,
                'groups_count': groups.count(),
                'students_count': students,
                'salary': salary.total if salary else 0,
                'salary_status': salary.status if salary else 'not_calculated'
            })

        return Response({
            'success': True,
            'data': {
                'period': {'year': year, 'month': month},
                'teachers': data
            }
        })

    @action(detail=False, methods=['get'])
    def lead_conversion(self, request):
        """
        Lead konversiya hisoboti

        GET /api/v1/analytics/reports/lead_conversion/?start_date=2024-01-01&end_date=2024-12-31
        """
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not start_date or not end_date:
            return Response({
                'success': False,
                'error': {'code': 'MISSING_PARAM', 'message': 'start_date va end_date kerak'}
            }, status=status.HTTP_400_BAD_REQUEST)

        leads = Lead.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        )

        total = leads.count()
        converted = leads.filter(status='converted').count()
        lost = leads.filter(status='lost').count()
        active = leads.filter(status__in=['new', 'contacted', 'trial']).count()

        # Manba bo'yicha konversiya
        by_source = leads.values('source').annotate(
            total=Count('id'),
            converted=Count('id', filter=Q(status='converted')),
        )

        source_data = []
        for s in by_source:
            rate = round((s['converted'] / s['total'] * 100) if s['total'] > 0 else 0, 1)
            source_data.append({
                'source': s['source'],
                'total': s['total'],
                'converted': s['converted'],
                'conversion_rate': rate,
            })

        # O'rtacha konversiya vaqti (kun)
        converted_leads = leads.filter(
            status='converted',
            converted_at__isnull=False,
        )
        avg_days = None
        if converted_leads.exists():
            from django.db.models import F, ExpressionWrapper, DurationField
            durations = converted_leads.annotate(
                duration=ExpressionWrapper(
                    F('converted_at') - F('created_at'),
                    output_field=DurationField()
                )
            )
            avg_duration = durations.aggregate(avg=Avg('duration'))['avg']
            if avg_duration:
                avg_days = avg_duration.days

        return Response({
            'success': True,
            'data': {
                'period': {'start': start_date, 'end': end_date},
                'summary': {
                    'total_leads': total,
                    'converted': converted,
                    'lost': lost,
                    'active': active,
                    'conversion_rate': round((converted / total * 100) if total > 0 else 0, 1),
                    'avg_conversion_days': avg_days,
                },
                'by_source': source_data,
            }
        })

    @action(detail=False, methods=['get'])
    def teacher_performance(self, request):
        """
        O'qituvchi samaradorlik hisoboti

        GET /api/v1/analytics/reports/teacher_performance/?start_date=2024-01-01&end_date=2024-06-30
        """
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not start_date or not end_date:
            return Response({
                'success': False,
                'error': {'code': 'MISSING_PARAM', 'message': 'start_date va end_date kerak'}
            }, status=status.HTTP_400_BAD_REQUEST)

        teachers = Teacher.objects.filter(status='active')

        data = []
        for teacher in teachers:
            groups = Group.objects.filter(teacher=teacher, status='active')
            group_ids = groups.values_list('id', flat=True)

            # Faol o'quvchilar soni
            active_students = GroupStudent.objects.filter(
                group__in=groups,
                is_active=True,
            ).count()

            # Chiqib ketganlar (dropped) soni
            dropped_students = GroupStudent.objects.filter(
                group__in=groups,
                status='dropped',
                left_date__gte=start_date,
                left_date__lte=end_date,
            ).count()

            # Davomat foizi
            attendances = Attendance.objects.filter(
                group__in=groups,
                date__gte=start_date,
                date__lte=end_date,
            )
            att_total = attendances.count()
            att_present = attendances.filter(status__in=['present', 'late']).count()
            att_rate = round((att_present / att_total * 100) if att_total > 0 else 0, 1)

            # Retention rate
            total_ever = GroupStudent.objects.filter(group__in=groups).count()
            retention = round((active_students / total_ever * 100) if total_ever > 0 else 0, 1)

            data.append({
                'teacher_id': str(teacher.id),
                'teacher_name': teacher.full_name,
                'groups_count': groups.count(),
                'active_students': active_students,
                'dropped_students': dropped_students,
                'attendance_rate': att_rate,
                'retention_rate': retention,
            })

        # Samaradorlik bo'yicha saralash
        data.sort(key=lambda x: x['attendance_rate'], reverse=True)

        return Response({
            'success': True,
            'data': {
                'period': {'start': start_date, 'end': end_date},
                'teachers': data,
            }
        })

    @action(detail=False, methods=['get'])
    def write_off_report(self, request):
        """
        Write-off (yechib olish) hisoboti

        GET /api/v1/analytics/reports/write_off_report/?year=2026&month=3
        """
        from apps.payments.models import WriteOff

        year = int(request.query_params.get('year', timezone.now().year))
        month = int(request.query_params.get('month', timezone.now().month))

        write_offs = WriteOff.objects.filter(
            period_year=year,
            period_month=month,
        ).select_related('student', 'group')

        total_amount = write_offs.aggregate(total=Sum('amount'))['total'] or 0
        total_count = write_offs.count()

        # Guruh bo'yicha
        by_group = write_offs.values(
            'group__id', 'group__name'
        ).annotate(
            total=Sum('amount'),
            count=Count('id'),
        ).order_by('-total')

        return Response({
            'success': True,
            'data': {
                'period': {'year': year, 'month': month},
                'summary': {
                    'total_amount': total_amount,
                    'total_count': total_count,
                },
                'by_group': list(by_group),
            }
        })