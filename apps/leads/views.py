"""
Edvora - Leads Views
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from django.utils import timezone
from core.permissions import RoleBasedPermission
from apps.students.models import Student
from apps.groups.models import GroupStudent
from rest_framework.permissions import AllowAny
from .models import Lead, LeadActivity, DemoRequest
from .serializers import (
    LeadListSerializer,
    LeadSerializer,
    LeadCreateSerializer,
    LeadActivitySerializer,
    LeadActivityCreateSerializer,
    LeadConvertSerializer,
    DemoRequestSerializer,
    DemoRequestListSerializer,
)


class LeadViewSet(viewsets.ModelViewSet):
    """
    Leadlar CRUD
    """
    queryset = Lead.objects.select_related(
        'interested_course', 'interested_subject', 'assigned_to'
    ).all()
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'source', 'priority', 'assigned_to', 'interested_course']
    search_fields = ['first_name', 'last_name', 'phone', 'email']
    ordering_fields = ['created_at', 'next_contact_date', 'priority']
    ordering = ['-created_at']

    role_permissions = {
        'list': ['owner', 'admin', 'registrar'],
        'retrieve': ['owner', 'admin', 'registrar'],
        'create': ['owner', 'admin', 'registrar'],
        'update': ['owner', 'admin', 'registrar'],
        'partial_update': ['owner', 'admin', 'registrar'],
        'destroy': ['owner', 'admin'],
        'convert': ['owner', 'admin', 'registrar'],
        'activities': ['owner', 'admin', 'registrar'],
        'add_activity': ['owner', 'admin', 'registrar'],
        'statistics': ['owner', 'admin'],
        'pipeline': ['owner', 'admin', 'registrar'],
    }

    def get_serializer_class(self):
        if self.action == 'list':
            return LeadListSerializer
        if self.action == 'create':
            return LeadCreateSerializer
        if self.action == 'convert':
            return LeadConvertSerializer
        if self.action == 'add_activity':
            return LeadActivityCreateSerializer
        return LeadSerializer

    @action(detail=True, methods=['post'])
    def convert(self, request, pk=None):
        """
        Lead'ni o'quvchiga aylantirish

        POST /api/v1/leads/{id}/convert/
        {
            "group_id": "uuid" (optional),
            "notes": "Izoh"
        }
        """
        lead = self.get_object()

        if lead.status == 'converted':
            return Response({
                'success': False,
                'error': {'code': 'ALREADY_CONVERTED', 'message': 'Bu lead allaqachon o\'quvchi bo\'lgan'}
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = LeadConvertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # O'quvchi yaratish
        student = Student.objects.create(
            first_name=lead.first_name,
            last_name=lead.last_name or '',
            phone=lead.phone,
            phone_secondary=lead.phone_secondary,
            email=lead.email,
            source=lead.source,
            notes=f"Lead'dan konvertatsiya: {lead.notes or ''}\n{serializer.validated_data.get('notes', '')}"
        )

        # Guruhga qo'shish (agar berilgan bo'lsa)
        group_id = serializer.validated_data.get('group_id')
        if group_id:
            from apps.groups.models import Group
            group = get_object_or_404(Group, id=group_id)
            GroupStudent.objects.create(
                group=group,
                student=student,
                joined_date=timezone.now().date(),
            )

        # Lead'ni yangilash
        lead.status = 'converted'
        lead.converted_student = student
        lead.converted_at = timezone.now()
        lead.save()

        # Activity qo'shish
        LeadActivity.objects.create(
            lead=lead,
            activity_type='status_change',
            description=f"O'quvchiga aylantirildi: {student.full_name}",
            created_by=request.user
        )

        return Response({
            'success': True,
            'message': "Lead o'quvchiga aylantirildi",
            'data': {
                'lead': LeadSerializer(lead).data,
                'student_id': str(student.id)
            }
        })

    @action(detail=True, methods=['get'])
    def activities(self, request, pk=None):
        """Lead faoliyatlari"""
        lead = self.get_object()
        activities = lead.activities.select_related('created_by').all()
        serializer = LeadActivitySerializer(activities, many=True)

        return Response({
            'success': True,
            'data': serializer.data
        })

    @action(detail=True, methods=['post'])
    def add_activity(self, request, pk=None):
        """Faoliyat qo'shish"""
        lead = self.get_object()

        data = request.data.copy()
        data['lead'] = lead.id

        serializer = LeadActivityCreateSerializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        activity = serializer.save()

        return Response({
            'success': True,
            'message': 'Faoliyat qo\'shildi',
            'data': LeadActivitySerializer(activity).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Lead statistikasi

        GET /api/v1/leads/statistics/?period=month
        """
        period = request.query_params.get('period', 'month')
        today = timezone.now().date()

        if period == 'week':
            start_date = today - timezone.timedelta(days=7)
        elif period == 'month':
            start_date = today.replace(day=1)
        elif period == 'year':
            start_date = today.replace(month=1, day=1)
        else:
            start_date = None

        queryset = Lead.objects.all()
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)

        total = queryset.count()
        stats = queryset.values('status').annotate(count=Count('id'))

        status_counts = {s['status']: s['count'] for s in stats}

        converted = status_counts.get('converted', 0)
        conversion_rate = round((converted / total * 100) if total > 0 else 0, 2)

        # Manba bo'yicha
        by_source = queryset.values('source').annotate(count=Count('id'))

        return Response({
            'success': True,
            'data': {
                'total': total,
                'new': status_counts.get('new', 0),
                'contacted': status_counts.get('contacted', 0),
                'interested': status_counts.get('interested', 0),
                'trial': status_counts.get('trial', 0),
                'negotiation': status_counts.get('negotiation', 0),
                'converted': converted,
                'lost': status_counts.get('lost', 0),
                'conversion_rate': conversion_rate,
                'by_source': list(by_source)
            }
        })

    @action(detail=False, methods=['get'])
    def pipeline(self, request):
        """
        Sales pipeline (Kanban uchun)

        GET /api/v1/leads/pipeline/
        """
        stages = ['new', 'contacted', 'interested', 'trial', 'negotiation']

        pipeline = {}
        for stage in stages:
            leads = Lead.objects.filter(status=stage).order_by('-priority', '-created_at')[:20]
            pipeline[stage] = LeadListSerializer(leads, many=True).data

        return Response({
            'success': True,
            'data': pipeline
        })

    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """
        Status o'zgartirish

        POST /api/v1/leads/{id}/change_status/
        {"status": "contacted", "note": "Qo'ng'iroq qildim"}
        """
        lead = self.get_object()
        new_status = request.data.get('status')
        note = request.data.get('note', '')

        if new_status not in dict(Lead.Status.choices):
            return Response({
                'success': False,
                'error': {'code': 'INVALID_STATUS', 'message': 'Noto\'g\'ri status'}
            }, status=status.HTTP_400_BAD_REQUEST)

        old_status = lead.status
        lead.status = new_status

        # Yo'qotilgan bo'lsa sabab yozish
        if new_status == 'lost':
            lead.lost_reason = note

        lead.save()

        # Activity qo'shish
        LeadActivity.objects.create(
            lead=lead,
            activity_type='status_change',
            description=f"Status o'zgartirildi: {old_status} → {new_status}. {note}",
            created_by=request.user
        )

        return Response({
            'success': True,
            'message': 'Status o\'zgartirildi',
            'data': LeadSerializer(lead).data
        })


class LeadActivityViewSet(viewsets.ModelViewSet):
    """
    Lead faoliyatlari CRUD
    """
    queryset = LeadActivity.objects.select_related('lead', 'created_by').all()
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['lead', 'activity_type']
    ordering = ['-created_at']

    role_permissions = {
        'list': ['owner', 'admin', 'registrar'],
        'retrieve': ['owner', 'admin', 'registrar'],
        'create': ['owner', 'admin', 'registrar'],
        'update': ['owner', 'admin'],
        'partial_update': ['owner', 'admin'],
        'destroy': ['owner'],
    }

    def get_serializer_class(self):
        if self.action == 'create':
            return LeadActivityCreateSerializer
        return LeadActivitySerializer


class DemoRequestViewSet(viewsets.ModelViewSet):
    """
    Demo so'rovlar
    - POST /api/v1/demo-requests/ (public - autentifikatsiyasiz)
    - GET /api/v1/demo-requests/ (admin only)
    """
    queryset = DemoRequest.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['name', 'phone', 'center_name']
    ordering = ['-created_at']

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated(), RoleBasedPermission()]

    role_permissions = {
        'list': ['owner', 'admin'],
        'retrieve': ['owner', 'admin'],
        'update': ['owner', 'admin'],
        'partial_update': ['owner', 'admin'],
        'destroy': ['owner'],
    }

    def get_serializer_class(self):
        if self.action == 'create':
            return DemoRequestSerializer
        return DemoRequestListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'success': True,
            'message': "So'rovingiz qabul qilindi!"
        }, status=status.HTTP_201_CREATED)