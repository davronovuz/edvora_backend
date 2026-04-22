"""
Edvora - Students Views
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from core.permissions import RoleBasedPermission
from .models import Student, StudentGroupNote
from .serializers import (
    StudentListSerializer,
    StudentSerializer,
    StudentCreateSerializer,
    StudentGroupNoteSerializer,
    TagSerializer,
)
from .tags import Tag, TaggedItem


class StudentViewSet(viewsets.ModelViewSet):
    """
    O'quvchilar CRUD
    """
    queryset = Student.objects.all()
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'gender', 'source', 'branch']
    search_fields = ['first_name', 'last_name', 'phone', 'parent_phone']
    ordering_fields = ['first_name', 'last_name', 'created_at', 'balance']
    ordering = ['-created_at']

    role_permissions = {
        'list': ['owner', 'admin', 'teacher', 'accountant', 'registrar'],
        'retrieve': ['owner', 'admin', 'teacher', 'accountant', 'registrar'],
        'create': ['owner', 'admin', 'registrar'],
        'update': ['owner', 'admin'],
        'partial_update': ['owner', 'admin'],
        'destroy': ['owner'],
        'debtors': ['owner', 'admin', 'accountant'],
        'freeze': ['owner', 'admin'],
        'unfreeze': ['owner', 'admin'],
        'archive': ['owner', 'admin'],
        'groups': ['owner', 'admin', 'teacher', 'accountant', 'registrar'],
        'statistics': ['owner', 'admin', 'accountant'],
        'progress_summary': ['owner', 'admin', 'teacher', 'accountant', 'registrar'],
        'transfer_history': ['owner', 'admin', 'registrar'],
        'lesson_grades_history': ['owner', 'admin', 'teacher', 'accountant', 'registrar'],
    }

    def get_serializer_class(self):
        if self.action == 'list':
            return StudentListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return StudentCreateSerializer
        return StudentSerializer

    def get_queryset(self):
        queryset = Student.objects.all()
        user = self.request.user

        # Teacher faqat o'z guruhlaridagi o'quvchilarni ko'radi
        if user.role == 'teacher':
            teacher_profile = getattr(user, 'teacher_profile', None)
            if teacher_profile:
                from apps.groups.models import GroupStudent
                student_ids = GroupStudent.objects.filter(
                    group__teacher=teacher_profile,
                    is_active=True,
                ).values_list('student_id', flat=True).distinct()
                queryset = queryset.filter(id__in=student_ids)
            else:
                queryset = queryset.none()

        # Qarzdorlar filtri
        has_debt = self.request.query_params.get('has_debt')
        if has_debt is not None:
            if has_debt.lower() == 'true':
                queryset = queryset.filter(balance__lt=0)
            else:
                queryset = queryset.filter(balance__gte=0)

        return queryset

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """O'quvchilar statistikasi"""
        total = Student.objects.count()
        active = Student.objects.filter(status='active').count()
        with_debt = Student.objects.filter(balance__lt=0).count()

        return Response({
            'success': True,
            'data': {
                'total': total,
                'active': active,
                'inactive': total - active,
                'with_debt': with_debt,
            }
        })

    @action(detail=False, methods=['get'])
    def debtors(self, request):
        """Qarzdor o'quvchilar ro'yxati"""
        students = Student.objects.filter(
            status='active',
            balance__lt=0,
        ).order_by('balance')

        serializer = StudentListSerializer(students, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'total_debt': sum(s.balance for s in students),
        })

    @action(detail=True, methods=['post'])
    def freeze(self, request, pk=None):
        """O'quvchini muzlatish"""
        student = self.get_object()

        if student.status == Student.Status.FROZEN:
            return Response({
                'success': False,
                'error': {'code': 'ALREADY_FROZEN', 'message': "O'quvchi allaqachon muzlatilgan"}
            }, status=status.HTTP_400_BAD_REQUEST)

        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        reason = request.data.get('reason', '')

        if not start_date:
            return Response({
                'success': False,
                'error': {'code': 'START_DATE_REQUIRED', 'message': "Boshlanish sanasi kerak"}
            }, status=status.HTTP_400_BAD_REQUEST)

        from datetime import datetime
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None

        student.freeze(start_date=start_date, end_date=end_date, reason=reason)

        return Response({
            'success': True,
            'message': f"{student.full_name} muzlatildi",
            'data': StudentSerializer(student).data,
        })

    @action(detail=True, methods=['post'])
    def unfreeze(self, request, pk=None):
        """Muzlatishni bekor qilish"""
        student = self.get_object()

        if student.status != Student.Status.FROZEN:
            return Response({
                'success': False,
                'error': {'code': 'NOT_FROZEN', 'message': "O'quvchi muzlatilmagan"}
            }, status=status.HTTP_400_BAD_REQUEST)

        student.unfreeze()

        return Response({
            'success': True,
            'message': f"{student.full_name} faollashtirildi",
            'data': StudentSerializer(student).data,
        })

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """O'quvchini arxivga olish"""
        student = self.get_object()

        reason = request.data.get('reason', '')
        student.archive(reason=reason)

        return Response({
            'success': True,
            'message': f"{student.full_name} arxivga olindi",
            'data': StudentSerializer(student).data,
        })

    @action(detail=True, methods=['get'], url_path='progress-summary')
    def progress_summary(self, request, pk=None):
        """
        O'quvchining umumiy progress ma'lumotlari — bir endpointda.

        GET /api/v1/students/{id}/progress-summary/

        Qaytaradi:
          - student: asosiy ma'lumot (status, freeze holati)
          - attendance: joriy oy va oxirgi 90 kun %, trend
          - grades: imtihon o'rtachasi, uy vazifasi o'rtachasi
          - finance: umumiy qarz, qarzdor guruhlar soni
          - groups: faol guruhlar ro'yxati (balans bilan)
        """
        from django.utils import timezone
        from django.db.models import Avg, Sum
        from datetime import timedelta
        from apps.attendance.models import Attendance
        from apps.exams.models import ExamResult, HomeworkSubmission

        student = self.get_object()
        today = timezone.now().date()
        month_start = today.replace(day=1)
        ninety_days_ago = today - timedelta(days=90)

        def attendance_rate(qs):
            total = qs.count()
            if total == 0:
                return None
            present = qs.filter(status__in=['present', 'late']).count()
            return round(present / total * 100, 1)

        att_all = Attendance.objects.filter(student=student)
        month_rate = attendance_rate(att_all.filter(date__gte=month_start, date__lte=today))
        quarter_rate = attendance_rate(att_all.filter(date__gte=ninety_days_ago, date__lte=today))
        trend = None
        if month_rate is not None and quarter_rate is not None:
            diff = month_rate - quarter_rate
            if diff > 2:
                trend = 'up'
            elif diff < -2:
                trend = 'down'
            else:
                trend = 'stable'

        exam_avg = ExamResult.objects.filter(
            student=student, status='graded',
        ).aggregate(avg=Avg('score'))['avg']
        exam_count = ExamResult.objects.filter(student=student, status='graded').count()

        hw_graded = HomeworkSubmission.objects.filter(student=student, status__in=['graded'])
        hw_avg = hw_graded.aggregate(avg=Avg('score'))['avg']
        hw_pending = HomeworkSubmission.objects.filter(student=student, status='pending').count()

        # Guruhlar va balans
        active_gs = student.groups.filter(is_active=True).select_related(
            'group__course', 'group__teacher'
        )
        groups_data = []
        total_group_debt = 0
        groups_with_debt = 0
        for gs in active_gs:
            bal = float(gs.balance or 0)
            if bal < 0:
                total_group_debt += abs(bal)
                groups_with_debt += 1
            groups_data.append({
                'id': str(gs.group.id),
                'name': gs.group.name,
                'course': gs.group.course.name,
                'teacher': gs.group.teacher.full_name if gs.group.teacher else None,
                'status': gs.status,
                'balance': bal,
                'monthly_price': float(gs.monthly_price) if gs.monthly_price else 0,
            })

        return Response({
            'success': True,
            'data': {
                'student': {
                    'id': str(student.id),
                    'full_name': student.full_name,
                    'status': student.status,
                    'is_frozen': student.is_frozen,
                    'freeze_start_date': student.freeze_start_date,
                    'freeze_end_date': student.freeze_end_date,
                    'freeze_reason': student.freeze_reason,
                    'balance': float(student.balance or 0),
                },
                'attendance': {
                    'month_rate': month_rate,
                    'quarter_rate': quarter_rate,
                    'trend': trend,
                    'total_records': att_all.count(),
                },
                'grades': {
                    'exam_avg': round(float(exam_avg), 1) if exam_avg else None,
                    'exam_count': exam_count,
                    'homework_avg': round(float(hw_avg), 1) if hw_avg else None,
                    'homework_pending': hw_pending,
                },
                'finance': {
                    'balance': float(student.balance or 0),
                    'groups_debt_total': round(total_group_debt, 2),
                    'groups_with_debt': groups_with_debt,
                },
                'groups': groups_data,
            }
        })

    @action(detail=True, methods=['get'], url_path='lesson-grades')
    def lesson_grades_history(self, request, pk=None):
        """
        O'quvchining dars baholari tarixi (barcha guruhlar bo'yicha, yoki filtrlash).

        GET /api/v1/students/{id}/lesson-grades/?group_id=uuid
        """
        from apps.attendance.models import LessonGrade
        from apps.attendance.serializers import LessonGradeSerializer

        student = self.get_object()
        qs = LessonGrade.objects.filter(student=student).select_related('group', 'graded_by')

        group_id = request.query_params.get('group_id')
        if group_id:
            qs = qs.filter(group_id=group_id)

        qs = qs.order_by('-date')[:200]

        return Response({
            'success': True,
            'data': LessonGradeSerializer(qs, many=True).data,
            'total': qs.count() if hasattr(qs, 'count') else len(list(qs)),
        })

    @action(detail=True, methods=['get'], url_path='transfer-history')
    def transfer_history(self, request, pk=None):
        """
        O'quvchining guruhdan guruhga ko'chirilishlari tarixi.
        AuditLog dan olinadi (transfer_student amali yozadi).

        GET /api/v1/students/{id}/transfer-history/
        """
        from apps.audit.models import AuditLog

        student = self.get_object()
        logs = AuditLog.objects.filter(
            action=AuditLog.Action.TRANSFER,
            model_name='GroupStudent',
            object_id=str(student.id),
        ).select_related('user').order_by('-created_at')

        data = []
        for log in logs:
            extra = log.extra_data or {}
            source_id = extra.get('source_group')
            target_id = extra.get('target_group')
            source_name = None
            target_name = None
            if log.object_repr and ':' in log.object_repr:
                try:
                    _, path = log.object_repr.split(':', 1)
                    if '->' in path:
                        source_name, target_name = [p.strip() for p in path.split('->', 1)]
                except Exception:
                    pass

            data.append({
                'id': str(log.id),
                'date': log.created_at,
                'from_group': {'id': source_id, 'name': source_name},
                'to_group': {'id': target_id, 'name': target_name},
                'reason': extra.get('reason', ''),
                'performed_by': {
                    'id': str(log.user.id) if log.user else None,
                    'name': log.user.get_full_name() if log.user else 'System',
                } if log.user else None,
            })

        return Response({
            'success': True,
            'data': data,
            'total': len(data),
        })

    @action(detail=True, methods=['get'])
    def groups(self, request, pk=None):
        """O'quvchining guruhlari"""
        student = self.get_object()
        groups = student.groups.select_related('group__course', 'group__teacher').filter(is_active=True)

        data = []
        for gs in groups:
            data.append({
                'id': str(gs.group.id),
                'group_student_id': str(gs.id),
                'name': gs.group.name,
                'course': gs.group.course.name,
                'teacher': gs.group.teacher.full_name if gs.group.teacher else None,
                'days': gs.group.get_days_display(),
                'time': f"{gs.group.start_time.strftime('%H:%M')} - {gs.group.end_time.strftime('%H:%M')}",
                'monthly_price': gs.monthly_price,
                'joined_date': gs.joined_date,
                'status': gs.status,
            })

        return Response({
            'success': True,
            'data': data
        })

    @action(detail=True, methods=['get', 'post', 'delete'], url_path='tags(?:/(?P<tag_id>[^/.]+))?')
    def tags(self, request, pk=None, tag_id=None):
        """
        O'quvchining teglari

        GET /api/v1/students/{id}/tags/ - teglar ro'yxati
        POST /api/v1/students/{id}/tags/ {"tag_id": "uuid"} - teg qo'shish
        DELETE /api/v1/students/{id}/tags/{tag_id}/ - tegni o'chirish
        """
        from django.contrib.contenttypes.models import ContentType

        student = self.get_object()
        ct = ContentType.objects.get_for_model(Student)

        if request.method == 'GET':
            tagged = TaggedItem.objects.filter(
                content_type=ct,
                object_id=student.id,
            ).select_related('tag')
            tags_data = [{'id': str(ti.tag.id), 'name': ti.tag.name, 'color': ti.tag.color} for ti in tagged]
            return Response({'success': True, 'data': tags_data})

        elif request.method == 'POST':
            tag_uuid = request.data.get('tag_id')
            if not tag_uuid:
                return Response({'success': False, 'error': {'message': 'tag_id kerak'}}, status=status.HTTP_400_BAD_REQUEST)

            tag = Tag.objects.filter(id=tag_uuid).first()
            if not tag:
                return Response({'success': False, 'error': {'message': 'Teg topilmadi'}}, status=status.HTTP_404_NOT_FOUND)

            _, created = TaggedItem.objects.get_or_create(
                tag=tag, content_type=ct, object_id=student.id,
            )
            return Response({
                'success': True,
                'message': f"'{tag.name}' tegi qo'shildi" if created else 'Teg allaqachon mavjud',
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

        elif request.method == 'DELETE':
            if not tag_id:
                return Response({'success': False, 'error': {'message': 'tag_id kerak'}}, status=status.HTTP_400_BAD_REQUEST)
            deleted, _ = TaggedItem.objects.filter(
                tag_id=tag_id, content_type=ct, object_id=student.id,
            ).delete()
            if deleted:
                return Response({'success': True, 'message': "Teg o'chirildi"})
            return Response({'success': False, 'error': {'message': 'Teg topilmadi'}}, status=status.HTTP_404_NOT_FOUND)


class TagViewSet(viewsets.ModelViewSet):
    """
    Teglar CRUD
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [SearchFilter]
    search_fields = ['name']

    role_permissions = {
        'list': ['owner', 'admin', 'teacher', 'registrar'],
        'retrieve': ['owner', 'admin', 'teacher', 'registrar'],
        'create': ['owner', 'admin'],
        'update': ['owner', 'admin'],
        'partial_update': ['owner', 'admin'],
        'destroy': ['owner'],
    }


class StudentGroupNoteViewSet(viewsets.ModelViewSet):
    """
    O'quvchi-guruh izohlari CRUD
    """
    queryset = StudentGroupNote.objects.select_related('student', 'group', 'created_by').all()
    serializer_class = StudentGroupNoteSerializer
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['student', 'group', 'note_type', 'is_pinned']
    ordering = ['-is_pinned', '-created_at']

    role_permissions = {
        'list': ['owner', 'admin', 'teacher'],
        'retrieve': ['owner', 'admin', 'teacher'],
        'create': ['owner', 'admin', 'teacher'],
        'update': ['owner', 'admin', 'teacher'],
        'partial_update': ['owner', 'admin', 'teacher'],
        'destroy': ['owner', 'admin', 'teacher'],
    }

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == 'teacher':
            teacher_profile = getattr(user, 'teacher_profile', None)
            if teacher_profile:
                qs = qs.filter(group__teacher=teacher_profile)
            else:
                qs = qs.none()
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        note = serializer.instance
        user = self.request.user
        if user.role == 'teacher' and note.created_by_id and note.created_by_id != user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Faqat o'zingiz yozgan izohni tahrirlashingiz mumkin")
        serializer.save()