"""
Edvora - Students Serializers
"""

from rest_framework import serializers
from .models import Student


class StudentListSerializer(serializers.ModelSerializer):
    """Ro'yxat uchun qisqa"""
    full_name = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    groups_count = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            'id', 'first_name', 'last_name', 'full_name',
            'phone', 'status', 'status_display', 'balance',
            'groups_count', 'created_at'
        ]

    def get_groups_count(self, obj):
        return obj.groups.filter(is_active=True).count()


class StudentSerializer(serializers.ModelSerializer):
    """To'liq ma'lumot"""
    full_name = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    gender_display = serializers.CharField(source='get_gender_display', read_only=True)
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    has_debt = serializers.ReadOnlyField()

    class Meta:
        model = Student
        fields = [
            'id', 'first_name', 'last_name', 'full_name',
            'phone', 'phone_secondary', 'email', 'photo',
            'birth_date', 'gender', 'gender_display', 'address',
            'parent_name', 'parent_phone',
            'status', 'status_display', 'enrolled_date',
            'balance', 'has_debt',
            'telegram_id', 'telegram_username',
            'source', 'source_display', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'enrolled_date', 'created_at', 'updated_at']


class StudentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = [
            'first_name', 'last_name', 'phone', 'phone_secondary',
            'email', 'photo', 'birth_date', 'gender', 'address',
            'parent_name', 'parent_phone', 'status',
            'telegram_id', 'telegram_username', 'source', 'notes'
        ]