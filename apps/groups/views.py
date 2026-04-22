"""
Edvora - Groups Views
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.shortcuts import get_object_or_404
from core.permissions import RoleBasedPermission
from apps.students.models import Student
from .models import Group, GroupStudent
from .serializers import (
    GroupListSerializer,
    GroupSerializer,
    GroupCreateSerializer,
    GroupStudentSerializer,
    AddStudentToGroupSerializer,
    TransferStudentSerializer,
)


class GroupViewSet(viewsets.ModelViewSet):
    """
    Guruhlar CRUD
    """
    queryset = Group.objects.select_related('course', 'teacher').all()
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['course', 'teacher', 'status', 'branch']
    search_fields = ['name']
    ordering_fields = ['name', 'start_date', 'created_at']
    ordering = ['-start_date']

    role_permissions = {
        'list': ['owner', 'admin', 'teacher', 'registrar'],
        'retrieve': ['owner', 'admin', 'teacher', 'registrar'],
        'create': ['owner', 'admin'],
        'update': ['owner', 'admin'],
        'partial_update': ['owner', 'admin'],
        'destroy': ['owner'],
        'students': ['owner', 'admin', 'teacher'],
        'add_student': ['owner', 'admin', 'registrar'],
        'remove_student': ['owner', 'admin'],
        'transfer_student': ['owner', 'admin'],
        'summary': ['owner', 'admin', 'teacher'],
        'schedule_conflicts': ['owner', 'admin'],
        'lesson_grades': ['owner', 'admin', 'teacher'],
    }

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == 'teacher':
            teacher_profile = getattr(user, 'teacher_profile', None)
            if teacher_profile:
                qs = qs.filter(teacher=teacher_profile)
            else:
                qs = qs.none()
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return GroupListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return GroupCreateSerializer
        return GroupSerializer

    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        """Guruhdagi o'quvchilar"""
        group = self.get_object()
        students = group.students.select_related('student').all()
        serializer = GroupStudentSerializer(students, many=True)

        return Response({
            'success': True,
            'data': serializer.data
        })

    @action(detail=True, methods=['post'])
    def add_student(self, request, pk=None):
        """Guruhga o'quvchi qo'shish"""
        group = self.get_object()
        serializer = AddStudentToGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        student = get_object_or_404(Student, id=serializer.validated_data['student_id'])

        # Tekshirish
        if group.is_full:
            return Response({
                'success': False,
                'error': {'code': 'GROUP_FULL', 'message': 'Guruh to\'lgan'}
            }, status=status.HTTP_400_BAD_REQUEST)

        if GroupStudent.objects.filter(group=group, student=student, is_active=True).exists():
            return Response({
                'success': False,
                'error': {'code': 'ALREADY_EXISTS', 'message': 'O\'quvchi allaqachon guruhda'}
            }, status=status.HTTP_400_BAD_REQUEST)

        # Qo'shish
        from django.utils import timezone
        from dateutil.relativedelta import relativedelta
        today = timezone.now().date()
        next_wo = today + relativedelta(months=1, day=1)  # Keyingi oyning 1-kuni

        gs = GroupStudent.objects.create(
            group=group,
            student=student,
            joined_date=today,
            custom_price=serializer.validated_data.get('custom_price'),
            discount_percent=serializer.validated_data.get('discount_percent', 0),
            next_write_off_date=next_wo,
        )

        return Response({
            'success': True,
            'message': f"{student.full_name} guruhga qo'shildi",
            'data': GroupStudentSerializer(gs).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='remove-student/(?P<student_id>[^/.]+)')
    def remove_student(self, request, pk=None, student_id=None):
        """Guruhdan o'quvchini chiqarish"""
        group = self.get_object()

        gs = get_object_or_404(GroupStudent, group=group, student_id=student_id, is_active=True)
        gs.is_active = False
        gs.status = 'dropped'
        gs.save()

        return Response({
            'success': True,
            'message': "O'quvchi guruhdan chiqarildi"
        })

    @action(detail=True, methods=['post'])
    def transfer_student(self, request, pk=None):
        """
        O'quvchini boshqa guruhga o'tkazish

        POST /api/v1/groups/{id}/transfer_student/
        {
            "student_id": "uuid",
            "target_group_id": "uuid",
            "custom_price": null,
            "discount_percent": 0,
            "reason": "Vaqt mos kelmadi"
        }
        """
        from django.utils import timezone as tz

        source_group = self.get_object()
        serializer = TransferStudentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        student_id = serializer.validated_data['student_id']
        target_group_id = serializer.validated_data['target_group_id']

        student = get_object_or_404(Student, id=student_id)
        target_group = get_object_or_404(Group, id=target_group_id)

        # Tekshirishlar
        source_gs = GroupStudent.objects.filter(
            group=source_group, student=student, is_active=True
        ).first()

        if not source_gs:
            return Response({
                'success': False,
                'error': {'code': 'NOT_IN_GROUP', 'message': "O'quvchi bu guruhda emas"}
            }, status=status.HTTP_400_BAD_REQUEST)

        if target_group.is_full:
            return Response({
                'success': False,
                'error': {'code': 'TARGET_FULL', 'message': "Maqsad guruh to'lgan"}
            }, status=status.HTTP_400_BAD_REQUEST)

        if GroupStudent.objects.filter(
            group=target_group, student=student, is_active=True
        ).exists():
            return Response({
                'success': False,
                'error': {'code': 'ALREADY_IN_TARGET', 'message': "O'quvchi allaqachon maqsad guruhda"}
            }, status=status.HTTP_400_BAD_REQUEST)

        # Eski guruhdan chiqarish
        source_gs.is_active = False
        source_gs.status = GroupStudent.Status.TRANSFERRED
        source_gs.left_date = tz.now().date()
        source_gs.save()

        # Yangi guruhga qo'shish
        target_gs = GroupStudent.objects.create(
            group=target_group,
            student=student,
            joined_date=tz.now().date(),
            custom_price=serializer.validated_data.get('custom_price'),
            discount_percent=serializer.validated_data.get('discount_percent', 0),
        )

        # Audit log
        from apps.audit.models import AuditLog
        AuditLog.log(
            user=request.user,
            action='transfer',
            model_name='GroupStudent',
            object_id=str(student.id),
            object_repr=f"{student.full_name}: {source_group.name} -> {target_group.name}",
            extra_data={
                'reason': serializer.validated_data.get('reason', ''),
                'source_group': str(source_group.id),
                'target_group': str(target_group.id),
            }
        )

        return Response({
            'success': True,
            'message': f"{student.full_name} '{source_group.name}' dan '{target_group.name}' ga o'tkazildi",
            'data': {
                'student_name': student.full_name,
                'from_group': source_group.name,
                'to_group': target_group.name,
                'new_enrollment': GroupStudentSerializer(target_gs).data,
            }
        })

    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """
        Guruh umumiy statistikasi — GroupDetail Overview tab uchun

        GET /api/v1/groups/{id}/summary/
        """
        from django.utils import timezone
        from django.db.models import Avg, Count, Q
        from datetime import timedelta

        group = self.get_object()
        today = timezone.now().date()
        month_start = today.replace(day=1)

        # O'quvchilar
        active_students = GroupStudent.objects.filter(group=group, is_active=True)
        total_students = active_students.count()
        debtors = active_students.filter(balance__lt=0).count()

        # Davomat — joriy oy
        from apps.attendance.models import Attendance
        month_attendance = Attendance.objects.filter(
            group=group, date__gte=month_start, date__lte=today
        )
        att_total = month_attendance.count()
        att_present = month_attendance.filter(status='present').count()
        att_late = month_attendance.filter(status='late').count()
        att_absent = month_attendance.filter(status='absent').count()
        att_rate = round((att_present + att_late) / att_total * 100, 1) if att_total > 0 else 0

        # Imtihonlar
        from apps.exams.models import Exam, ExamResult
        exams = Exam.objects.filter(group=group)
        total_exams = exams.count()
        completed_exams = exams.filter(status='completed').count()
        avg_score = ExamResult.objects.filter(
            exam__group=group, status='graded'
        ).aggregate(avg=Avg('score'))['avg']

        # Uy vazifalari
        from apps.exams.models import Homework
        homeworks = Homework.objects.filter(group=group)
        total_homeworks = homeworks.count()
        active_homeworks = homeworks.filter(status='active').count()

        # Moliya
        from apps.payments.models import Payment
        month_payments = Payment.objects.filter(
            group=group, status='completed',
            created_at__gte=month_start
        )
        month_revenue = sum(p.amount for p in month_payments)
        total_expected = sum(s.monthly_price for s in active_students if s.monthly_price)
        total_debt = sum(abs(s.balance) for s in active_students if s.balance and s.balance < 0)

        return Response({
            'success': True,
            'data': {
                'students': {
                    'total': total_students,
                    'debtors': debtors,
                    'max': group.max_students,
                },
                'attendance': {
                    'rate': att_rate,
                    'present': att_present,
                    'absent': att_absent,
                    'late': att_late,
                    'total_records': att_total,
                },
                'exams': {
                    'total': total_exams,
                    'completed': completed_exams,
                    'avg_score': round(avg_score, 1) if avg_score else 0,
                },
                'homeworks': {
                    'total': total_homeworks,
                    'active': active_homeworks,
                },
                'finance': {
                    'month_revenue': float(month_revenue),
                    'expected': float(total_expected),
                    'total_debt': float(total_debt),
                },
            }
        })

    @action(detail=True, methods=['get', 'post'], url_path='lesson-grades')
    def lesson_grades(self, request, pk=None):
        """
        Dars baholari — GET ro'yxat, POST bulk upsert.

        GET  /api/v1/groups/{id}/lesson-grades/?date=YYYY-MM-DD
        POST /api/v1/groups/{id}/lesson-grades/
              {"date": "2026-04-22", "grades": [{"student_id": uuid, "score": 4.5, "note": "..."}]}
        """
        from apps.attendance.models import LessonGrade
        from apps.attendance.serializers import (
            LessonGradeSerializer, LessonGradeBulkSerializer,
        )

        group = self.get_object()

        user = request.user
        if user.role == 'teacher':
            teacher_profile = getattr(user, 'teacher_profile', None)
            if not teacher_profile or group.teacher_id != teacher_profile.id:
                return Response({
                    'success': False,
                    'error': {'code': 'FORBIDDEN', 'message': "Bu guruhga kirish huquqingiz yo'q"}
                }, status=status.HTTP_403_FORBIDDEN)

        if request.method == 'GET':
            qs = LessonGrade.objects.filter(group=group).select_related('student', 'graded_by')
            date_param = request.query_params.get('date')
            if date_param:
                qs = qs.filter(date=date_param)
            qs = qs.order_by('-date', 'student__first_name')
            return Response({
                'success': True,
                'data': LessonGradeSerializer(qs, many=True).data,
            })

        serializer = LessonGradeBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        date = serializer.validated_data['date']
        grades_data = serializer.validated_data['grades']

        valid_student_ids = set(
            str(sid) for sid in GroupStudent.objects.filter(
                group=group, is_active=True,
            ).values_list('student_id', flat=True)
        )

        created = 0
        updated = 0
        skipped = []
        for item in grades_data:
            student_id = str(item.get('student_id', ''))
            if student_id not in valid_student_ids:
                skipped.append({'student_id': student_id, 'reason': 'NOT_IN_GROUP'})
                continue
            try:
                score = float(item.get('score'))
            except (TypeError, ValueError):
                skipped.append({'student_id': student_id, 'reason': 'INVALID_SCORE'})
                continue
            if score < 0 or score > 5:
                skipped.append({'student_id': student_id, 'reason': 'SCORE_OUT_OF_RANGE'})
                continue

            _, is_created = LessonGrade.objects.update_or_create(
                group=group,
                student_id=student_id,
                date=date,
                defaults={
                    'score': score,
                    'note': item.get('note', '') or '',
                    'graded_by': request.user,
                },
            )
            if is_created:
                created += 1
            else:
                updated += 1

        return Response({
            'success': True,
            'message': f"Baholar saqlandi: {created} yangi, {updated} yangilandi",
            'data': {
                'created': created,
                'updated': updated,
                'skipped': skipped,
            },
        })

    @action(detail=False, methods=['get'])
    def schedule_conflicts(self, request):
        """
        Jadval konfliktlarini aniqlash (xona yoki o'qituvchi bo'yicha)

        GET /api/v1/groups/schedule_conflicts/
        """
        active_groups = Group.objects.filter(
            status__in=['forming', 'active']
        ).select_related('teacher', 'room', 'course')

        conflicts = []
        groups_list = list(active_groups)

        for i, g1 in enumerate(groups_list):
            for g2 in groups_list[i + 1:]:
                # Kunlar kesishishi
                common_days = set(g1.days) & set(g2.days)
                if not common_days:
                    continue

                # Vaqt overlap: start1 < end2 AND start2 < end1
                if not (g1.start_time < g2.end_time and g2.start_time < g1.end_time):
                    continue

                # Xona konflikti
                if g1.room and g2.room and g1.room_id == g2.room_id:
                    conflicts.append({
                        'type': 'room',
                        'room': str(g1.room),
                        'group_1': {'id': str(g1.id), 'name': g1.name,
                                    'time': f"{g1.start_time}-{g1.end_time}"},
                        'group_2': {'id': str(g2.id), 'name': g2.name,
                                    'time': f"{g2.start_time}-{g2.end_time}"},
                        'common_days': list(common_days),
                    })

                # O'qituvchi konflikti
                if g1.teacher and g2.teacher and g1.teacher_id == g2.teacher_id:
                    conflicts.append({
                        'type': 'teacher',
                        'teacher': g1.teacher.full_name,
                        'group_1': {'id': str(g1.id), 'name': g1.name,
                                    'time': f"{g1.start_time}-{g1.end_time}"},
                        'group_2': {'id': str(g2.id), 'name': g2.name,
                                    'time': f"{g2.start_time}-{g2.end_time}"},
                        'common_days': list(common_days),
                    })

        return Response({
            'success': True,
            'data': {
                'total_conflicts': len(conflicts),
                'conflicts': conflicts,
            }
        })