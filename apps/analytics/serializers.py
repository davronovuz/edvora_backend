"""
Edvora - Analytics Serializers
"""

from rest_framework import serializers
from .models import DailyStats, MonthlyStats


class DailyStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyStats
        fields = '__all__'


class MonthlyStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthlyStats
        fields = '__all__'


class DashboardSummarySerializer(serializers.Serializer):
    """Dashboard umumiy ko'rsatkichlar"""
    students = serializers.DictField()
    groups = serializers.DictField()
    teachers = serializers.DictField()
    finance = serializers.DictField()
    leads = serializers.DictField()
    attendance = serializers.DictField()


class ChartDataSerializer(serializers.Serializer):
    """Grafik uchun ma'lumot"""
    labels = serializers.ListField(child=serializers.CharField())
    datasets = serializers.ListField(child=serializers.DictField())