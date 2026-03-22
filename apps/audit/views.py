"""
Edvora - Audit Views
"""

from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Count
from core.permissions import IsOwnerOrAdmin
from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                      viewsets.GenericViewSet):
    """
    Audit loglar - faqat ko'rish (o'chirish/o'zgartirish mumkin emas)
    """
    queryset = AuditLog.objects.select_related('user').all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['user', 'action', 'model_name']
    search_fields = ['object_repr', 'model_name']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Audit log statistikasi

        GET /api/v1/audit/summary/?days=7
        """
        from django.utils import timezone
        from datetime import timedelta

        days = int(request.query_params.get('days', 7))
        since = timezone.now() - timedelta(days=days)

        logs = AuditLog.objects.filter(created_at__gte=since)

        by_action = logs.values('action').annotate(
            count=Count('id')
        ).order_by('-count')

        by_user = logs.values('user__first_name', 'user__last_name').annotate(
            count=Count('id')
        ).order_by('-count')[:10]

        by_model = logs.values('model_name').annotate(
            count=Count('id')
        ).order_by('-count')

        return Response({
            'success': True,
            'data': {
                'total': logs.count(),
                'period_days': days,
                'by_action': list(by_action),
                'by_user': list(by_user),
                'by_model': list(by_model),
            }
        })

    @action(detail=False, methods=['get'])
    def object_history(self, request):
        """
        Bitta ob'ekt tarixi

        GET /api/v1/audit/object_history/?model=Student&object_id=uuid
        """
        model_name = request.query_params.get('model')
        object_id = request.query_params.get('object_id')

        if not model_name or not object_id:
            return Response({
                'success': False,
                'error': {'code': 'MISSING_PARAM', 'message': 'model va object_id kerak'}
            }, status=400)

        logs = AuditLog.objects.filter(
            model_name=model_name, object_id=object_id
        ).select_related('user').order_by('-created_at')

        serializer = AuditLogSerializer(logs, many=True)

        return Response({
            'success': True,
            'data': serializer.data
        })
