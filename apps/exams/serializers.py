"""
Edvora - Exams Serializers
"""

from rest_framework import serializers
from .models import Exam, ExamResult, Homework, HomeworkSubmission, LessonPlan


# ============ EXAM ============

class ExamListSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source='group.name', read_only=True)
    type_display = serializers.CharField(source='get_exam_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    average_score = serializers.ReadOnlyField()
    pass_rate = serializers.ReadOnlyField()

    class Meta:
        model = Exam
        fields = [
            'id', 'title', 'group', 'group_name',
            'exam_type', 'type_display',
            'max_score', 'passing_score',
            'exam_date', 'start_time', 'duration_minutes',
            'status', 'status_display',
            'average_score', 'pass_rate',
        ]


class ExamSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source='group.name', read_only=True)
    type_display = serializers.CharField(source='get_exam_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    average_score = serializers.ReadOnlyField()
    pass_rate = serializers.ReadOnlyField()
    results_count = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = [
            'id', 'title', 'description', 'group', 'group_name',
            'exam_type', 'type_display',
            'max_score', 'passing_score',
            'exam_date', 'start_time', 'duration_minutes',
            'status', 'status_display',
            'average_score', 'pass_rate', 'results_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_results_count(self, obj):
        return obj.results.count()


class ExamCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = [
            'title', 'description', 'group', 'exam_type',
            'max_score', 'passing_score',
            'exam_date', 'start_time', 'duration_minutes', 'status',
        ]


# ============ EXAM RESULT ============

class ExamResultSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    exam_title = serializers.CharField(source='exam.title', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    percentage = serializers.ReadOnlyField()
    is_passed = serializers.ReadOnlyField()
    grade_letter = serializers.ReadOnlyField()

    class Meta:
        model = ExamResult
        fields = [
            'id', 'exam', 'exam_title', 'student', 'student_name',
            'score', 'status', 'status_display',
            'percentage', 'is_passed', 'grade_letter',
            'feedback', 'graded_at',
        ]
        read_only_fields = ['id', 'graded_at']


class ExamResultCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamResult
        fields = ['exam', 'student', 'score', 'status', 'feedback']


class BulkExamResultSerializer(serializers.Serializer):
    exam_id = serializers.UUIDField()
    results = serializers.ListField(
        child=serializers.DictField(), min_length=1
    )


# ============ HOMEWORK ============

class HomeworkListSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source='group.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    submission_rate = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()

    class Meta:
        model = Homework
        fields = [
            'id', 'title', 'group', 'group_name',
            'max_score', 'assigned_date', 'due_date',
            'status', 'status_display',
            'submission_rate', 'is_overdue',
        ]


class HomeworkSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source='group.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    submission_rate = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()

    class Meta:
        model = Homework
        fields = [
            'id', 'title', 'description', 'group', 'group_name',
            'max_score', 'assigned_date', 'due_date',
            'status', 'status_display',
            'attachment', 'submission_rate', 'is_overdue',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class HomeworkCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Homework
        fields = [
            'title', 'description', 'group',
            'max_score', 'assigned_date', 'due_date',
            'status', 'attachment',
        ]


# ============ HOMEWORK SUBMISSION ============

class HomeworkSubmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    homework_title = serializers.CharField(source='homework.title', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_late = serializers.ReadOnlyField()

    class Meta:
        model = HomeworkSubmission
        fields = [
            'id', 'homework', 'homework_title',
            'student', 'student_name',
            'score', 'status', 'status_display',
            'submitted_at', 'attachment', 'comment', 'feedback',
            'is_late',
        ]
        read_only_fields = ['id', 'submitted_at']


class HomeworkSubmissionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeworkSubmission
        fields = ['homework', 'student', 'attachment', 'comment']


class HomeworkGradeSerializer(serializers.Serializer):
    score = serializers.DecimalField(max_digits=6, decimal_places=2)
    feedback = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(
        choices=['graded', 'resubmit'], default='graded'
    )


# ============ LESSON PLAN ============

class LessonPlanListSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source='group.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = LessonPlan
        fields = [
            'id', 'group', 'group_name', 'lesson_number',
            'title', 'date', 'duration_minutes',
            'status', 'status_display',
        ]


class LessonPlanSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source='group.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True, default=None)

    class Meta:
        model = LessonPlan
        fields = [
            'id', 'group', 'group_name', 'lesson_number',
            'title', 'description', 'objectives', 'materials',
            'homework_description', 'date', 'duration_minutes',
            'status', 'status_display', 'notes',
            'created_by', 'created_by_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']


class LessonPlanCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonPlan
        fields = [
            'group', 'lesson_number', 'title', 'description',
            'objectives', 'materials', 'homework_description',
            'date', 'duration_minutes', 'status', 'notes',
        ]
