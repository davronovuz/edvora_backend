"""
Edvora - Attendance Views
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from core.permissions import RoleBasedPermission
from apps.groups.models import Group, GroupStudent
from apps.students.models import Student
from .models import Attendance, AttendanceSession, Holiday
from .serializers import (
    AttendanceSerializer,
    AttendanceCreateSerializer,
    BulkAttendanceSerializer,
    AttendanceSessionSerializer,
    AttendanceReportSerializer,
    HolidaySerializer,
)


class AttendanceViewSet(viewsets.ModelViewSet):
    """
    Davomat CRUD
    """
    queryset = Attendance.objects.select_related('group', 'student', 'marked_by').all()
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['group', 'student', 'status', 'date']
    ordering_fields = ['date', 'created_at']
    ordering = ['-date']

    role_permissions = {
        'list': ['owner', 'admin', 'teacher'],
        'retrieve': ['owner', 'admin', 'teacher'],
        'create': ['owner', 'admin', 'teacher'],
        'update': ['owner', 'admin', 'teacher'],
        'partial_update': ['owner', 'admin', 'teacher'],
        'destroy': ['owner', 'admin'],
        'bulk_create': ['owner', 'admin', 'teacher'],
        'by_group': ['owner', 'admin', 'teacher'],
        'by_student': ['owner', 'admin', 'teacher', 'accountant'],
        'report': ['owner', 'admin', 'teacher'],
    }

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == 'teacher' and hasattr(user, 'teacher_profile'):
            qs = qs.filter(group__teacher=user.teacher_profile)
        return qs

    def _check_teacher_group_access(self, group):
        """Teacher faqat o'z guruhiga access olsin"""
        user = self.request.user
        if user.role == 'teacher':
            if not hasattr(user, 'teacher_profile') or group.teacher_id != user.teacher_profile.id:
                return False
        return True

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AttendanceCreateSerializer
        if self.action == 'bulk_create':
            return BulkAttendanceSerializer
        return AttendanceSerializer

    def perform_create(self, serializer):
        serializer.save(marked_by=self.request.user)

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """
        Bir vaqtda ko'p o'quvchi uchun davomat

        POST /api/v1/attendance/bulk_create/
        {
            "group_id": "uuid",
            "date": "2024-01-15",
            "attendances": [
                {"student_id": "uuid", "status": "present", "note": ""},
                {"student_id": "uuid", "status": "absent", "note": "Kasal"}
            ]
        }
        """
        serializer = BulkAttendanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group_id = serializer.validated_data['group_id']
        date = serializer.validated_data['date']
        attendances_data = serializer.validated_data['attendances']

        group = get_object_or_404(Group, id=group_id)

        if not self._check_teacher_group_access(group):
            return Response({
                'success': False,
                'error': {'code': 'FORBIDDEN', 'message': 'Bu guruhga davomat qo\'yish huquqingiz yo\'q'}
            }, status=status.HTTP_403_FORBIDDEN)

        created_count = 0
        updated_count = 0

        for item in attendances_data:
            student_id = item.get('student_id')
            status_value = item.get('status', 'present')
            note = item.get('note', '')

            attendance, created = Attendance.objects.update_or_create(
                group=group,
                student_id=student_id,
                date=date,
                defaults={
                    'status': status_value,
                    'note': note,
                    'marked_by': request.user
                }
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        # Session yaratish/yangilash
        session, _ = AttendanceSession.objects.get_or_create(
            group=group,
            date=date,
            defaults={'created_by': request.user}
        )
        session.update_stats()

        return Response({
            'success': True,
            'message': f"Davomat saqlandi: {created_count} ta yangi, {updated_count} ta yangilandi",
            'data': {
                'created': created_count,
                'updated': updated_count,
                'session': AttendanceSessionSerializer(session).data
            }
        })

    @action(detail=False, methods=['get'])
    def by_group(self, request):
        """
        Guruh bo'yicha davomat

        GET /api/v1/attendance/by_group/?group_id=uuid&date=2024-01-15
        """
        group_id = request.query_params.get('group_id')
        date = request.query_params.get('date', timezone.now().date())

        if not group_id:
            return Response({
                'success': False,
                'error': {'code': 'MISSING_PARAM', 'message': 'group_id kerak'}
            }, status=status.HTTP_400_BAD_REQUEST)

        group = get_object_or_404(Group, id=group_id)

        if not self._check_teacher_group_access(group):
            return Response({
                'success': False,
                'error': {'code': 'FORBIDDEN', 'message': 'Bu guruhga kirish huquqingiz yo\'q'}
            }, status=status.HTTP_403_FORBIDDEN)

        # Guruhdagi barcha o'quvchilar
        group_students = GroupStudent.objects.filter(
            group=group,
            is_active=True
        ).select_related('student')

        # Shu kunga davomat
        attendances = {
            a.student_id: a for a in
            Attendance.objects.filter(group=group, date=date)
        }

        data = []
        for gs in group_students:
            attendance = attendances.get(gs.student_id)
            data.append({
                'student_id': str(gs.student.id),
                'student_name': gs.student.full_name,
                'student_phone': gs.student.phone,
                'status': attendance.status if attendance else None,
                'note': attendance.note if attendance else None,
                'attendance_id': str(attendance.id) if attendance else None,
            })

        return Response({
            'success': True,
            'data': {
                'group': {
                    'id': str(group.id),
                    'name': group.name,
                },
                'date': str(date),
                'students': data
            }
        })

    @action(detail=False, methods=['get'])
    def by_student(self, request):
        """
        O'quvchi bo'yicha davomat tarixi

        GET /api/v1/attendance/by_student/?student_id=uuid&group_id=uuid&month=2024-01
        """
        student_id = request.query_params.get('student_id')
        group_id = request.query_params.get('group_id')
        month = request.query_params.get('month')  # 2024-01 format

        if not student_id:
            return Response({
                'success': False,
                'error': {'code': 'MISSING_PARAM', 'message': 'student_id kerak'}
            }, status=status.HTTP_400_BAD_REQUEST)

        student = get_object_or_404(Student, id=student_id)

        queryset = Attendance.objects.filter(student=student)

        if group_id:
            queryset = queryset.filter(group_id=group_id)

        if month:
            year, m = month.split('-')
            queryset = queryset.filter(date__year=year, date__month=m)

        attendances = queryset.order_by('-date')

        # Statistika
        total = attendances.count()
        present = attendances.filter(status='present').count()
        absent = attendances.filter(status='absent').count()
        late = attendances.filter(status='late').count()

        return Response({
            'success': True,
            'data': {
                'student': {
                    'id': str(student.id),
                    'name': student.full_name,
                },
                'statistics': {
                    'total': total,
                    'present': present,
                    'absent': absent,
                    'late': late,
                    'rate': round((present + late) / total * 100, 1) if total > 0 else 0
                },
                'attendances': AttendanceSerializer(attendances[:50], many=True).data
            }
        })

    @action(detail=False, methods=['get'])
    def report(self, request):
        """
        Guruh davomat hisoboti

        GET /api/v1/attendance/report/?group_id=uuid&start_date=2024-01-01&end_date=2024-01-31
        """
        group_id = request.query_params.get('group_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not all([group_id, start_date, end_date]):
            return Response({
                'success': False,
                'error': {'code': 'MISSING_PARAM', 'message': 'group_id, start_date, end_date kerak'}
            }, status=status.HTTP_400_BAD_REQUEST)

        group = get_object_or_404(Group, id=group_id)

        if not self._check_teacher_group_access(group):
            return Response({
                'success': False,
                'error': {'code': 'FORBIDDEN', 'message': 'Bu guruhga kirish huquqingiz yo\'q'}
            }, status=status.HTTP_403_FORBIDDEN)

        # Guruhdagi o'quvchilar
        group_students = GroupStudent.objects.filter(
            group=group,
            is_active=True
        ).select_related('student')

        report = []
        for gs in group_students:
            attendances = Attendance.objects.filter(
                group=group,
                student=gs.student,
                date__gte=start_date,
                date__lte=end_date
            )

            total = attendances.count()
            present = attendances.filter(status='present').count()
            absent = attendances.filter(status='absent').count()
            late = attendances.filter(status='late').count()

            report.append({
                'student_id': str(gs.student.id),
                'student_name': gs.student.full_name,
                'total_days': total,
                'present_days': present,
                'absent_days': absent,
                'late_days': late,
                'attendance_rate': round((present + late) / total * 100, 1) if total > 0 else 0
            })

        return Response({
            'success': True,
            'data': {
                'group': {
                    'id': str(group.id),
                    'name': group.name,
                },
                'period': {
                    'start': start_date,
                    'end': end_date
                },
                'report': report
            }
        })


class HolidayViewSet(viewsets.ModelViewSet):
    """
    Dam olish kunlari CRUD
    """
    queryset = Holiday.objects.all()
    serializer_class = HolidaySerializer
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['holiday_type', 'is_active']
    ordering = ['date']

    role_permissions = {
        'list': ['owner', 'admin', 'teacher', 'accountant', 'registrar'],
        'retrieve': ['owner', 'admin', 'teacher', 'accountant', 'registrar'],
        'create': ['owner', 'admin'],
        'update': ['owner', 'admin'],
        'partial_update': ['owner', 'admin'],
        'destroy': ['owner'],
        'check_date': ['owner', 'admin', 'teacher'],
        'upcoming': ['owner', 'admin', 'teacher', 'accountant', 'registrar'],
    }

    @action(detail=False, methods=['get'], url_path='check-date')
    def check_date(self, request):
        """
        Berilgan sana dam olish kuniga to'g'ri keladimi tekshirish

        GET /api/v1/holidays/check-date/?date=2026-03-21
        """
        date_str = request.query_params.get('date')
        if not date_str:
            return Response({
                'success': False,
                'error': {'code': 'MISSING_PARAM', 'message': 'date kerak'}
            }, status=status.HTTP_400_BAD_REQUEST)

        from datetime import datetime as dt
        check_date = dt.strptime(date_str, '%Y-%m-%d').date()
        is_holiday = Holiday.is_holiday(check_date)

        holiday_name = None
        if is_holiday:
            from django.db.models import Q
            holiday = Holiday.objects.filter(
                is_active=True,
                date__lte=check_date,
            ).filter(
                Q(end_date__gte=check_date) | Q(end_date__isnull=True, date=check_date)
            ).first()
            if holiday:
                holiday_name = holiday.name

        return Response({
            'success': True,
            'data': {
                'date': date_str,
                'is_holiday': is_holiday,
                'holiday_name': holiday_name,
            }
        })

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Kelayotgan dam olish kunlari"""
        today = timezone.now().date()
        holidays = Holiday.objects.filter(
            is_active=True,
            date__gte=today,
        )[:20]

        serializer = HolidaySerializer(holidays, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
        })