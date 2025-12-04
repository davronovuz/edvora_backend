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
        'summary': ['owner', 'admin'],
        'students_chart': ['owner', 'admin'],
        'finance_chart': ['owner', 'admin', 'accountant'],
        'attendance_chart': ['owner', 'admin', 'teacher'],
        'leads_chart': ['owner', 'admin', 'registrar'],
        'recent_activity': ['owner', 'admin'],
        'top_groups': ['owner', 'admin'],
        'debtors_summary': ['owner', 'admin', 'accountant'],
    }

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Dashboard umumiy ko'rsatkichlar

        GET /api/v1/analytics/dashboard/summary/
        """
        today = timezone.now().date()
        month_start = today.replace(day=1)

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
        groups = Group.objects.filter(status='active').annotate(
            students_count=Count('students', filter=Q(students__is_active=True))
        ).order_by('-students_count')[:10]

        data = []
        for g in groups:
            data.append({
                'id': str(g.id),
                'name': g.name,
                'course': g.course.name,
                'teacher': g.teacher.full_name if g.teacher else None,
                'students_count': g.students_count,
                'max_students': g.max_students,
                'fill_rate': round((g.students_count / g.max_students * 100) if g.max_students > 0 else 0, 1)
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