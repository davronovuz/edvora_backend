"""
Edvora - Rooms Serializers
"""

from rest_framework import serializers
from .models import Room


class RoomListSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_room_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True, default=None)

    class Meta:
        model = Room
        fields = [
            'id', 'name', 'number', 'floor',
            'room_type', 'type_display',
            'capacity', 'status', 'status_display',
            'branch', 'branch_name',
            'has_projector', 'has_whiteboard', 'has_computers', 'has_air_conditioning',
        ]


class RoomSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_room_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True, default=None)

    class Meta:
        model = Room
        fields = [
            'id', 'name', 'number', 'floor',
            'room_type', 'type_display',
            'capacity', 'status', 'status_display',
            'branch', 'branch_name',
            'equipment',
            'has_projector', 'has_whiteboard', 'has_computers', 'has_air_conditioning',
            'photo', 'hourly_rate', 'description',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RoomCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = [
            'name', 'number', 'floor', 'room_type', 'capacity', 'status', 'branch',
            'equipment', 'has_projector', 'has_whiteboard', 'has_computers',
            'has_air_conditioning', 'photo', 'hourly_rate', 'description',
        ]


class RoomScheduleSerializer(serializers.Serializer):
    date = serializers.DateField()


class RoomAvailabilitySerializer(serializers.Serializer):
    date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
