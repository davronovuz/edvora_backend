"""
Edvora - Finance Celery Tasks
Oylik maoshlarni avtomatik hisoblash
"""

import logging
from celery import shared_task
from django.utils import timezone
from django.db.models import Count, Sum
from decimal import Decimal

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def calculate_monthly_salaries(self):
    """
    Barcha faol o'qituvchilar uchun oylik maoshni hisoblash.
    Har oyning 25-kuni ishlaydi.
    """
    from apps.teachers.models import Teacher
    from apps.finance.models import Salary
    from apps.groups.models import GroupStudent
    from apps.attendance.models import AttendanceSession

    now = timezone.now()
    month = now.month
    year = now.year

    teachers = Teacher.objects.filter(status='active')

    created_count = 0
    skipped_count = 0

    for teacher in teachers:
        # Bu oy uchun maosh bormi?
        exists = Salary.objects.filter(
            teacher=teacher, period_month=month, period_year=year
        ).exists()

        if exists:
            skipped_count += 1
            continue

        # O'qituvchining faol guruhlari
        active_groups = teacher.groups.filter(status='active')

        # Jami darslar soni (attendance sessions)
        total_lessons = AttendanceSession.objects.filter(
            group__in=active_groups,
            date__year=year,
            date__month=month,
        ).count()

        # Jami o'quvchilar
        total_students = GroupStudent.objects.filter(
            group__in=active_groups,
            is_active=True,
        ).count()

        # Maosh hisoblash
        base_salary = Decimal('0')
        calculation_details = {
            'groups': [],
            'salary_type': teacher.salary_type,
        }

        if teacher.salary_type == 'fixed':
            base_salary = teacher.salary_amount or Decimal('0')
            calculation_details['fixed_amount'] = str(base_salary)

        elif teacher.salary_type == 'hourly':
            hourly_rate = teacher.salary_amount or Decimal('0')
            # Har bir dars 1.5 soat deb hisoblanadi
            hours = Decimal(str(total_lessons)) * Decimal('1.5')
            base_salary = hours * hourly_rate
            calculation_details['hourly_rate'] = str(hourly_rate)
            calculation_details['total_hours'] = str(hours)

        elif teacher.salary_type == 'percent':
            percent = teacher.salary_percent or Decimal('0')
            # Har bir guruhdan foiz
            from apps.payments.models import Payment
            for group in active_groups:
                group_income = Payment.objects.filter(
                    group=group,
                    status='completed',
                    created_at__year=year,
                    created_at__month=month,
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

                group_salary = group_income * (percent / 100)
                base_salary += group_salary

                calculation_details['groups'].append({
                    'group_name': group.name,
                    'income': str(group_income),
                    'percent': str(percent),
                    'salary': str(group_salary),
                })

        Salary.objects.create(
            teacher=teacher,
            period_month=month,
            period_year=year,
            base_salary=base_salary,
            total=base_salary,
            total_lessons=total_lessons,
            total_students=total_students,
            calculation_details=calculation_details,
            status='calculated',
        )
        created_count += 1

    logger.info(f"Oylik maoshlar hisoblandi: {created_count} ta, {skipped_count} ta o'tkazildi")
    return {'created': created_count, 'skipped': skipped_count}
