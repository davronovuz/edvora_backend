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
from .models import Student
from .serializers import (
    StudentListSerializer,
    StudentSerializer,
    StudentCreateSerializer,
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