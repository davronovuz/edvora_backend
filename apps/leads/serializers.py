"""
Edvora - Leads Serializers
"""

from rest_framework import serializers
from .models import Lead, LeadActivity, DemoRequest


class LeadListSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    interested_course_name = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = [
            'id', 'first_name', 'last_name', 'full_name',
            'phone', 'status', 'status_display',
            'source', 'source_display',
            'priority', 'priority_display',
            'interested_course', 'interested_course_name',
            'assigned_to', 'assigned_to_name',
            'next_contact_date', 'created_at'
        ]

    def get_interested_course_name(self, obj):
        return obj.interested_course.name if obj.interested_course else None

    def get_assigned_to_name(self, obj):
        return obj.assigned_to.full_name if obj.assigned_to else None


class LeadSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    interested_course_name = serializers.SerializerMethodField()
    interested_subject_name = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()
    activities_count = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = [
            'id', 'first_name', 'last_name', 'full_name',
            'phone', 'phone_secondary', 'email',
            'interested_course', 'interested_course_name',
            'interested_subject', 'interested_subject_name',
            'status', 'status_display',
            'source', 'source_display',
            'priority', 'priority_display',
            'assigned_to', 'assigned_to_name',
            'next_contact_date',
            'converted_student', 'converted_at',
            'lost_reason', 'notes',
            'utm_source', 'utm_medium', 'utm_campaign',
            'activities_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_interested_course_name(self, obj):
        return obj.interested_course.name if obj.interested_course else None

    def get_interested_subject_name(self, obj):
        return obj.interested_subject.name if obj.interested_subject else None

    def get_assigned_to_name(self, obj):
        return obj.assigned_to.full_name if obj.assigned_to else None

    def get_activities_count(self, obj):
        return obj.activities.count()


class LeadCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = [
            'first_name', 'last_name', 'phone', 'phone_secondary', 'email',
            'interested_course', 'interested_subject',
            'source', 'priority', 'assigned_to',
            'next_contact_date', 'notes',
            'utm_source', 'utm_medium', 'utm_campaign'
        ]


class LeadActivitySerializer(serializers.ModelSerializer):
    activity_type_display = serializers.CharField(source='get_activity_type_display', read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = LeadActivity
        fields = [
            'id', 'lead', 'activity_type', 'activity_type_display',
            'description', 'call_duration',
            'created_by', 'created_by_name', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_created_by_name(self, obj):
        return obj.created_by.full_name if obj.created_by else None


class LeadActivityCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadActivity
        fields = ['lead', 'activity_type', 'description', 'call_duration']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class DemoRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemoRequest
        fields = ['name', 'phone', 'center_name', 'message']


class DemoRequestListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = DemoRequest
        fields = [
            'id', 'name', 'phone', 'center_name', 'message',
            'status', 'status_display', 'notes', 'created_at'
        ]


class LeadConvertSerializer(serializers.Serializer):
    """Lead'ni o'quvchiga aylantirish"""
    group_id = serializers.UUIDField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)


class LeadStatisticsSerializer(serializers.Serializer):
    """Lead statistikasi"""
    total = serializers.IntegerField()
    new = serializers.IntegerField()
    contacted = serializers.IntegerField()
    interested = serializers.IntegerField()
    converted = serializers.IntegerField()
    lost = serializers.IntegerField()
    conversion_rate = serializers.FloatField()