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
        'schedule_conflicts': ['owner', 'admin'],
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