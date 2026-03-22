"""
Edvora - Audit Serializers
"""

from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'user_name',
            'action', 'action_display',
            'model_name', 'object_id', 'object_repr',
            'changes', 'extra_data',
            'ip_address', 'created_at',
        ]

    def get_user_name(self, obj):
        if obj.user:
            return obj.user.get_full_name()
        return 'System'
