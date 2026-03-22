"""
Edvora - Analytics Celery Tasks
Kunlik va oylik statistikani avtomatik hisoblash
"""

import logging
from celery import shared_task
from django.utils import timezone
from django.db.models import Sum, Count, Q, Avg
from decimal import Decimal

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def calculate_daily_stats(self):
    """
    Kunlik statistika hisoblash.
    Har kuni kechqurun 23:00 da ishlaydi.
    """
    from apps.analytics.models import DailyStats
    from apps.students.models import Student
    from apps.teachers.models import Teacher
    from apps.groups.models import Group
    from apps.payments.models import Payment
    from apps.finance.models import Expense, Salary
    from apps.leads.models import Lead
    from apps.attendance.models import Attendance

    today = timezone.now().date()

    # O'quvchilar
    total_students = Student.objects.count()
    active_students = Student.objects.filter(status='active').count()
    new_students = Student.objects.filter(created_at__date=today).count()

    # Guruhlar
    total_groups = Group.objects.count()
    active_groups = Group.objects.filter(status='active').count()

    # O'qituvchilar
    total_teachers = Teacher.objects.count()
    active_teachers = Teacher.objects.filter(status='active').count()

    # Moliya
    total_income = Payment.objects.filter(
        status='completed', created_at__date=today
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    total_expense = Expense.objects.filter(
        status='paid', expense_date=today
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    # Davomat
    today_attendance = Attendance.objects.filter(date=today)
    total_att = today_attendance.count()
    present_att = today_attendance.filter(
        status__in=['present', 'late']
    ).count()
    attendance_rate = round(present_att / total_att * 100, 1) if total_att > 0 else 0

    # Leadlar
    total_leads = Lead.objects.filter(created_at__date=today).count()
    converted_leads = Lead.objects.filter(
        status='converted', converted_at__date=today
    ).count()

    stats, created = DailyStats.objects.update_or_create(
        date=today,
        defaults={
            'total_students': total_students,
            'active_students': active_students,
            'new_students': new_students,
            'total_groups': total_groups,
            'active_groups': active_groups,
            'total_teachers': total_teachers,
            'active_teachers': active_teachers,
            'total_income': total_income,
            'total_expense': total_expense,
            'attendance_rate': Decimal(str(attendance_rate)),
            'total_leads': total_leads,
            'converted_leads': converted_leads,
        }
    )

    logger.info(f"Kunlik statistika hisoblandi: {today}")
    return {'date': str(today), 'created': created}


@shared_task(bind=True, max_retries=3)
def calculate_monthly_stats(self):
    """
    Oylik statistika hisoblash.
    Har oyning 1-kuni ishlaydi (oldingi oy uchun).
    """
    from apps.analytics.models import MonthlyStats
    from apps.students.models import Student
    from apps.payments.models import Payment
    from apps.finance.models import Expense, Salary
    from apps.leads.models import Lead
    from apps.attendance.models import Attendance

    now = timezone.now()
    # Oldingi oy
    if now.month == 1:
        month, year = 12, now.year - 1
    else:
        month, year = now.month - 1, now.year

    # O'quvchilar
    total_students = Student.objects.filter(
        created_at__year__lte=year,
        created_at__month__lte=month,
    ).count()

    new_students = Student.objects.filter(
        created_at__year=year,
        created_at__month=month,
    ).count()

    dropped_students = Student.objects.filter(
        status='dropped',
        updated_at__year=year,
        updated_at__month=month,
    ).count()

    # Moliya
    total_income = Payment.objects.filter(
        status='completed',
        created_at__year=year,
        created_at__month=month,
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    total_expense = Expense.objects.filter(
        status='paid',
        expense_date__year=year,
        expense_date__month=month,
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    total_salary = Salary.objects.filter(
        status='paid',
        period_year=year,
        period_month=month,
    ).aggregate(total=Sum('total'))['total'] or Decimal('0')

    net_profit = total_income - total_expense - total_salary

    # Davomat
    month_attendance = Attendance.objects.filter(
        date__year=year, date__month=month
    )
    total_att = month_attendance.count()
    present_att = month_attendance.filter(status__in=['present', 'late']).count()
    avg_attendance = round(present_att / total_att * 100, 1) if total_att > 0 else 0

    # Leadlar
    total_leads = Lead.objects.filter(
        created_at__year=year, created_at__month=month
    ).count()
    converted_leads = Lead.objects.filter(
        status='converted',
        converted_at__year=year, converted_at__month=month,
    ).count()
    conversion_rate = round(
        converted_leads / total_leads * 100, 1
    ) if total_leads > 0 else 0

    stats, created = MonthlyStats.objects.update_or_create(
        year=year,
        month=month,
        defaults={
            'total_students': total_students,
            'new_students': new_students,
            'dropped_students': dropped_students,
            'total_income': total_income,
            'total_expense': total_expense,
            'total_salary': total_salary,
            'net_profit': net_profit,
            'average_attendance_rate': Decimal(str(avg_attendance)),
            'total_leads': total_leads,
            'converted_leads': converted_leads,
            'conversion_rate': Decimal(str(conversion_rate)),
        }
    )

    logger.info(f"Oylik statistika hisoblandi: {month}/{year}")
    return {'month': month, 'year': year, 'created': created}
