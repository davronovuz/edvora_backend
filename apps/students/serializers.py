"""
Edvora - Students Serializers
"""

from rest_framework import serializers
from .models import Student
from .tags import Tag, TaggedItem


class StudentListSerializer(serializers.ModelSerializer):
    """Ro'yxat uchun qisqa"""
    full_name = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    groups_count = serializers.SerializerMethodField()
    branch_name = serializers.CharField(source='branch.name', read_only=True, default=None)

    class Meta:
        model = Student
        fields = [
            'id', 'first_name', 'last_name', 'full_name',
            'phone', 'status', 'status_display', 'balance',
            'branch', 'branch_name',
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
    is_frozen = serializers.ReadOnlyField()
    branch_name = serializers.CharField(source='branch.name', read_only=True, default=None)

    class Meta:
        model = Student
        fields = [
            'id', 'first_name', 'last_name', 'full_name',
            'phone', 'phone_secondary', 'email', 'photo',
            'branch', 'branch_name',
            'birth_date', 'gender', 'gender_display', 'address',
            'parent_name', 'parent_phone', 'passport_series',
            'status', 'status_display', 'enrolled_date',
            'balance', 'has_debt', 'is_frozen',
            'freeze_start_date', 'freeze_end_date', 'freeze_reason',
            'archive_reason', 'archived_at',
            'telegram_id', 'telegram_username',
            'source', 'source_display', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'enrolled_date', 'created_at', 'updated_at',
            'balance', 'freeze_start_date', 'freeze_end_date',
            'freeze_reason', 'archive_reason', 'archived_at',
        ]


class StudentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = [
            'first_name', 'last_name', 'phone', 'phone_secondary',
            'email', 'photo', 'birth_date', 'gender', 'address',
            'parent_name', 'parent_phone', 'passport_series', 'status',
            'telegram_id', 'telegram_username', 'source', 'notes',
            'branch',
        ]


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'color', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']


class TaggedItemSerializer(serializers.Serializer):
    tag_id = serializers.UUIDField()
    model_type = serializers.ChoiceField(choices=['student', 'group', 'lead'])
    object_id = serializers.UUIDField()