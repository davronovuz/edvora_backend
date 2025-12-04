"""
Edvora - Groups Serializers
"""

from rest_framework import serializers
from .models import Group, GroupStudent


class GroupListSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.name', read_only=True)
    teacher_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    students_count = serializers.ReadOnlyField()
    days_display = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = [
            'id', 'name', 'course', 'course_name',
            'teacher', 'teacher_name', 'status', 'status_display',
            'days', 'days_display', 'start_time', 'end_time', 'room',
            'students_count', 'max_students', 'start_date'
        ]

    def get_teacher_name(self, obj):
        return obj.teacher.full_name if obj.teacher else None

    def get_days_display(self, obj):
        return obj.get_days_display()


class GroupSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.name', read_only=True)
    teacher_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    students_count = serializers.ReadOnlyField()
    actual_price = serializers.ReadOnlyField()
    days_display = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = [
            'id', 'name', 'course', 'course_name',
            'teacher', 'teacher_name',
            'start_date', 'end_date',
            'days', 'days_display', 'start_time', 'end_time', 'room',
            'max_students', 'students_count',
            'status', 'status_display',
            'price', 'actual_price',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_teacher_name(self, obj):
        return obj.teacher.full_name if obj.teacher else None

    def get_days_display(self, obj):
        return obj.get_days_display()


class GroupCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = [
            'name', 'course', 'teacher',
            'start_date', 'end_date',
            'days', 'start_time', 'end_time', 'room',
            'max_students', 'status', 'price'
        ]


class GroupStudentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    student_phone = serializers.CharField(source='student.phone', read_only=True)
    monthly_price = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = GroupStudent
        fields = [
            'id', 'student', 'student_name', 'student_phone',
            'is_active', 'status', 'status_display',
            'joined_date', 'left_date',
            'custom_price', 'discount_percent', 'monthly_price'
        ]


class AddStudentToGroupSerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    custom_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    discount_percent = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, default=0)