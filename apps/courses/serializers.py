"""
Edvora - Courses Serializers
"""

from rest_framework import serializers
from .models import Subject, Course


class SubjectSerializer(serializers.ModelSerializer):
    courses_count = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = [
            'id', 'name', 'slug', 'description',
            'icon', 'color', 'is_active', 'courses_count',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_courses_count(self, obj):
        return obj.courses.filter(is_active=True).count()


class SubjectCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['name', 'slug', 'description', 'icon', 'color', 'is_active']


class CourseSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    groups_count = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'name', 'subject', 'subject_name', 'description',
            'level', 'level_display', 'duration_months', 'total_lessons',
            'price', 'is_active', 'groups_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_groups_count(self, obj):
        return obj.groups.filter(status='active').count()


class CourseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = [
            'name', 'subject', 'description', 'level',
            'duration_months', 'total_lessons', 'price', 'is_active'
        ]