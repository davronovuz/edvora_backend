"""
Edvora - Attendance Serializers
"""

from rest_framework import serializers
from .models import Attendance, AttendanceSession, Holiday, LessonGrade


class AttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    marked_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = [
            'id', 'group', 'student', 'student_name',
            'date', 'status', 'status_display',
            'marked_by', 'marked_by_name', 'note',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_marked_by_name(self, obj):
        return obj.marked_by.full_name if obj.marked_by else None


class AttendanceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = ['group', 'student', 'date', 'status', 'note']


class BulkAttendanceSerializer(serializers.Serializer):
    """Bir vaqtda ko'p o'quvchi uchun davomat"""
    group_id = serializers.UUIDField()
    date = serializers.DateField()
    attendances = serializers.ListField(
        child=serializers.DictField(
            child=serializers.CharField(allow_blank=True)
        )
    )
    # attendances: [{"student_id": "uuid", "status": "present"}]


class AttendanceSessionSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source='group.name', read_only=True)
    attendance_rate = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceSession
        fields = [
            'id', 'group', 'group_name', 'date',
            'total_students', 'present_count', 'absent_count', 'late_count',
            'attendance_rate', 'created_by', 'created_at'
        ]

    def get_attendance_rate(self, obj):
        if obj.total_students == 0:
            return 0
        return round((obj.present_count + obj.late_count) / obj.total_students * 100, 1)


class AttendanceReportSerializer(serializers.Serializer):
    """Davomat hisoboti"""
    student_id = serializers.UUIDField()
    student_name = serializers.CharField()
    total_days = serializers.IntegerField()
    present_days = serializers.IntegerField()
    absent_days = serializers.IntegerField()
    late_days = serializers.IntegerField()
    attendance_rate = serializers.FloatField()


class LessonGradeSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    graded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = LessonGrade
        fields = [
            'id', 'group', 'student', 'student_name',
            'date', 'score', 'note',
            'graded_by', 'graded_by_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'graded_by']

    def get_graded_by_name(self, obj):
        return obj.graded_by.full_name if obj.graded_by else None


class LessonGradeBulkSerializer(serializers.Serializer):
    """Bir dars uchun bir nechta o'quvchi bahosi"""
    date = serializers.DateField()
    grades = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False,
    )
    # grades: [{"student_id": "uuid", "score": 4.5, "note": ""}]


class HolidaySerializer(serializers.ModelSerializer):
    holiday_type_display = serializers.CharField(source='get_holiday_type_display', read_only=True)

    class Meta:
        model = Holiday
        fields = [
            'id', 'name', 'date', 'end_date',
            'holiday_type', 'holiday_type_display',
            'is_active', 'description',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']