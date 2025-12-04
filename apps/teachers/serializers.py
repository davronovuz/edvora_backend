"""
Edvora - Teachers Serializers
"""

from rest_framework import serializers
from .models import Teacher


class TeacherListSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    subjects_list = serializers.SerializerMethodField()
    groups_count = serializers.SerializerMethodField()

    class Meta:
        model = Teacher
        fields = [
            'id', 'first_name', 'last_name', 'full_name',
            'phone', 'photo', 'status', 'status_display',
            'subjects_list', 'groups_count'
        ]

    def get_subjects_list(self, obj):
        return [s.name for s in obj.subjects.all()[:3]]

    def get_groups_count(self, obj):
        return obj.groups.filter(status='active').count()


class TeacherSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    subjects_data = serializers.SerializerMethodField()

    class Meta:
        model = Teacher
        fields = [
            'id', 'user', 'first_name', 'last_name', 'full_name',
            'phone', 'phone_secondary', 'email', 'photo',
            'birth_date', 'address', 'bio',
            'subjects', 'subjects_data',
            'salary_type', 'salary_amount', 'salary_percent',
            'status', 'status_display', 'hired_date',
            'telegram_id', 'telegram_username',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_subjects_data(self, obj):
        return [{'id': str(s.id), 'name': s.name} for s in obj.subjects.all()]


class TeacherCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Teacher
        fields = [
            'first_name', 'last_name', 'phone', 'phone_secondary',
            'email', 'photo', 'birth_date', 'address', 'bio',
            'subjects', 'salary_type', 'salary_amount', 'salary_percent',
            'status', 'hired_date', 'telegram_id', 'telegram_username'
        ]