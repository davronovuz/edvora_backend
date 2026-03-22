"""
Edvora - Branch Serializers
"""

from rest_framework import serializers
from .models import Branch


class BranchListSerializer(serializers.ModelSerializer):
    """Ro'yxat uchun qisqa"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    groups_count = serializers.ReadOnlyField()
    rooms_count = serializers.ReadOnlyField()
    teachers_count = serializers.ReadOnlyField()
    students_count = serializers.ReadOnlyField()

    class Meta:
        model = Branch
        fields = [
            'id', 'name', 'address', 'phone', 'city',
            'status', 'status_display', 'is_main',
            'groups_count', 'rooms_count', 'teachers_count', 'students_count',
        ]


class BranchSerializer(serializers.ModelSerializer):
    """To'liq ma'lumot"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    groups_count = serializers.ReadOnlyField()
    rooms_count = serializers.ReadOnlyField()
    teachers_count = serializers.ReadOnlyField()
    students_count = serializers.ReadOnlyField()

    class Meta:
        model = Branch
        fields = [
            'id', 'name', 'address', 'phone', 'phone_secondary',
            'city', 'district', 'landmark',
            'latitude', 'longitude',
            'working_hours', 'working_days',
            'manager_name', 'manager_phone',
            'status', 'status_display', 'is_main',
            'groups_count', 'rooms_count', 'teachers_count', 'students_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class BranchCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = [
            'name', 'address', 'phone', 'phone_secondary',
            'city', 'district', 'landmark',
            'latitude', 'longitude',
            'working_hours', 'working_days',
            'manager_name', 'manager_phone',
            'status', 'is_main',
        ]
