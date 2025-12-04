"""
Edvora - Notifications Serializers
"""

from rest_framework import serializers
from .models import Notification, NotificationTemplate, NotificationLog


class NotificationSerializer(serializers.ModelSerializer):
    notification_type_display = serializers.CharField(
        source='get_notification_type_display', read_only=True
    )
    channel_display = serializers.CharField(
        source='get_channel_display', read_only=True
    )
    priority_display = serializers.CharField(
        source='get_priority_display', read_only=True
    )

    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message',
            'notification_type', 'notification_type_display',
            'channel', 'channel_display',
            'priority', 'priority_display',
            'is_read', 'read_at',
            'is_sent', 'sent_at',
            'related_model', 'related_id', 'data',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class NotificationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'user', 'student', 'teacher',
            'title', 'message',
            'notification_type', 'channel', 'priority',
            'related_model', 'related_id', 'data'
        ]


class NotificationTemplateSerializer(serializers.ModelSerializer):
    notification_type_display = serializers.CharField(
        source='get_notification_type_display', read_only=True
    )

    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'name', 'slug',
            'notification_type', 'notification_type_display',
            'title_template', 'message_template',
            'channels', 'is_active',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class NotificationLogSerializer(serializers.ModelSerializer):
    channel_display = serializers.CharField(
        source='get_channel_display', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )

    class Meta:
        model = NotificationLog
        fields = [
            'id', 'notification',
            'channel', 'channel_display',
            'status', 'status_display',
            'external_id', 'response', 'error_message',
            'created_at'
        ]


class BulkNotificationSerializer(serializers.Serializer):
    """Ommaviy xabarnoma yuborish"""
    title = serializers.CharField(max_length=255)
    message = serializers.CharField()
    notification_type = serializers.ChoiceField(choices=Notification.NotificationType.choices)
    channels = serializers.ListField(child=serializers.CharField())

    # Kimga
    target_type = serializers.ChoiceField(choices=['all_students', 'group', 'debtors', 'selected'])
    group_id = serializers.UUIDField(required=False)
    student_ids = serializers.ListField(child=serializers.UUIDField(), required=False)