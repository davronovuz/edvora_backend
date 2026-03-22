"""
Edvora - Rooms Views
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from core.permissions import RoleBasedPermission
from .models import Room
from .serializers import (
    RoomListSerializer, RoomSerializer, RoomCreateSerializer,
    RoomScheduleSerializer, RoomAvailabilitySerializer,
)


class RoomViewSet(viewsets.ModelViewSet):
    """Xonalar CRUD + jadval va mavjudlik tekshiruvi"""
    queryset = Room.objects.all()
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['room_type', 'status', 'floor', 'branch']
    search_fields = ['name', 'number']
    ordering_fields = ['number', 'capacity', 'created_at']
    ordering = ['number']

    role_permissions = {
        'list': ['owner', 'admin', 'teacher', 'registrar'],
        'retrieve': ['owner', 'admin', 'teacher', 'registrar'],
        'create': ['owner', 'admin'],
        'update': ['owner', 'admin'],
        'partial_update': ['owner', 'admin'],
        'destroy': ['owner'],
        'schedule': ['owner', 'admin', 'teacher', 'registrar'],
        'availability': ['owner', 'admin', 'teacher', 'registrar'],
    }

    def get_serializer_class(self):
        if self.action == 'list':
            return RoomListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return RoomCreateSerializer
        return RoomSerializer

    @action(detail=True, methods=['get'])
    def schedule(self, request, pk=None):
        """
        Xona jadvali berilgan kunga

        GET /api/v1/rooms/{id}/schedule/?date=2024-03-15
        """
        room = self.get_object()
        date_str = request.query_params.get('date')

        if date_str:
            from datetime import datetime
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            date = timezone.now().date()

        groups = room.get_schedule_for_date(date)

        schedule_data = []
        for group in groups:
            schedule_data.append({
                'group_id': str(group.id),
                'group_name': group.name,
                'course_name': group.course.name,
                'teacher_name': group.teacher.full_name if group.teacher else None,
                'start_time': group.start_time.strftime('%H:%M'),
                'end_time': group.end_time.strftime('%H:%M'),
                'students_count': group.students_count,
            })

        return Response({
            'success': True,
            'data': {
                'room': RoomListSerializer(room).data,
                'date': str(date),
                'weekday': date.strftime('%A'),
                'schedule': schedule_data,
            }
        })

    @action(detail=True, methods=['get'])
    def availability(self, request, pk=None):
        """
        Xona berilgan vaqtda bo'shmi?

        GET /api/v1/rooms/{id}/availability/?date=2024-03-15&start_time=09:00&end_time=11:00
        """
        room = self.get_object()
        serializer = RoomAvailabilitySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        date = serializer.validated_data['date']
        start_time = serializer.validated_data['start_time']
        end_time = serializer.validated_data['end_time']

        is_available = room.is_available_at(date, start_time, end_time)

        return Response({
            'success': True,
            'data': {
                'room_id': str(room.id),
                'room_name': room.name,
                'date': str(date),
                'start_time': str(start_time),
                'end_time': str(end_time),
                'is_available': is_available,
            }
        })

    @action(detail=False, methods=['get'])
    def available(self, request):
        """
        Berilgan vaqtda bo'sh xonalar ro'yxati

        GET /api/v1/rooms/available/?date=2024-03-15&start_time=09:00&end_time=11:00
        """
        serializer = RoomAvailabilitySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        date = serializer.validated_data['date']
        start_time = serializer.validated_data['start_time']
        end_time = serializer.validated_data['end_time']

        rooms = Room.objects.filter(status=Room.Status.ACTIVE)
        available_rooms = [
            room for room in rooms
            if room.is_available_at(date, start_time, end_time)
        ]

        return Response({
            'success': True,
            'data': RoomListSerializer(available_rooms, many=True).data
        })
