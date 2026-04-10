"""
Edvora - Billing Serializers
"""

from decimal import Decimal

from rest_framework import serializers

from .models import (
    BillingProfile,
    Discount,
    Invoice,
    InvoiceLine,
    StudentLeave,
)


# =============================================================================
# BillingProfile
# =============================================================================

class BillingProfileListSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True, default=None)
    mode_display = serializers.CharField(source='get_mode_display', read_only=True)
    invoices_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = BillingProfile
        fields = [
            'id', 'name', 'description', 'mode', 'mode_display',
            'branch', 'branch_name', 'is_default', 'is_active',
            'billing_day', 'due_days', 'leave_policy',
            'invoices_count', 'created_at',
        ]


class BillingProfileSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True, default=None)
    mode_display = serializers.CharField(source='get_mode_display', read_only=True)

    class Meta:
        model = BillingProfile
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class BillingProfileCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingProfile
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, data):
        mode = data.get('mode', '')
        if mode in ('per_lesson', 'per_attendance') and not data.get('price_per_lesson'):
            raise serializers.ValidationError(
                {'price_per_lesson': "Bu mode uchun dars narxi kiritilishi shart"}
            )
        if mode == 'hourly' and not data.get('price_per_hour'):
            raise serializers.ValidationError(
                {'price_per_hour': "Hourly mode uchun soat narxi kiritilishi shart"}
            )
        return data


# =============================================================================
# StudentLeave
# =============================================================================

class StudentLeaveSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    group_name = serializers.SerializerMethodField()
    days_count = serializers.IntegerField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = StudentLeave
        fields = [
            'id', 'group_student', 'student_name', 'group_name',
            'start_date', 'end_date', 'reason', 'days_count',
            'status', 'status_display',
            'requested_by', 'approved_by', 'approved_at',
            'created_at',
        ]
        read_only_fields = ['id', 'approved_by', 'approved_at', 'created_at', 'updated_at']

    def get_student_name(self, obj):
        return obj.group_student.student.full_name if obj.group_student else None

    def get_group_name(self, obj):
        return obj.group_student.group.name if obj.group_student else None


# =============================================================================
# Discount
# =============================================================================

class DiscountListSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source='get_kind_display', read_only=True)
    value_type_display = serializers.CharField(source='get_value_type_display', read_only=True)
    student_name = serializers.CharField(source='student.full_name', read_only=True, default=None)
    group_name = serializers.CharField(source='group.name', read_only=True, default=None)
    is_usable = serializers.BooleanField(read_only=True)

    class Meta:
        model = Discount
        fields = [
            'id', 'kind', 'kind_display', 'name', 'code',
            'value_type', 'value_type_display', 'value', 'max_amount',
            'student', 'student_name', 'group', 'group_name',
            'start_date', 'end_date',
            'stackable', 'priority', 'is_active', 'is_usable',
            'uses_count', 'max_uses',
            'created_at',
        ]


class DiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discount
        fields = '__all__'
        read_only_fields = ['id', 'uses_count', 'created_at', 'updated_at']


# =============================================================================
# InvoiceLine
# =============================================================================

class InvoiceLineSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source='get_kind_display', read_only=True)

    class Meta:
        model = InvoiceLine
        fields = [
            'id', 'kind', 'kind_display', 'description', 'amount',
            'discount', 'leave', 'meta', 'created_at',
        ]


# =============================================================================
# Invoice
# =============================================================================

class InvoiceListSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    remaining = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'number', 'student', 'student_name',
            'group', 'group_name',
            'period_month', 'period_year',
            'base_amount', 'discount_amount', 'leave_credit_amount',
            'total_amount', 'paid_amount', 'remaining',
            'status', 'status_display', 'is_overdue',
            'due_date', 'issue_date', 'paid_at',
            'created_at',
        ]


class InvoiceDetailSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    profile_name = serializers.CharField(source='billing_profile.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    remaining = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    lines = InvoiceLineSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'number', 'student', 'student_name',
            'group', 'group_name', 'group_student',
            'billing_profile', 'profile_name',
            'period_month', 'period_year',
            'period_start', 'period_end',
            'base_amount', 'discount_amount', 'leave_credit_amount',
            'late_fee_amount', 'extra_amount',
            'total_amount', 'paid_amount', 'remaining',
            'billable_days', 'total_period_days',
            'billable_lessons', 'total_period_lessons',
            'status', 'status_display', 'is_overdue',
            'due_date', 'issue_date', 'paid_at',
            'lines', 'note',
            'created_at', 'updated_at',
        ]


class InvoiceGenerateSerializer(serializers.Serializer):
    """Invoice generatsiya qilish uchun kirish."""
    group_student_id = serializers.UUIDField()
    year = serializers.IntegerField(min_value=2020, max_value=2100)
    month = serializers.IntegerField(min_value=1, max_value=12)
    promo_code = serializers.CharField(required=False, allow_blank=True, default=None)
    force = serializers.BooleanField(required=False, default=False)


class InvoiceGenerateGroupSerializer(serializers.Serializer):
    """Guruh uchun batch invoice generatsiya."""
    group_id = serializers.UUIDField()
    year = serializers.IntegerField(min_value=2020, max_value=2100)
    month = serializers.IntegerField(min_value=1, max_value=12)


class PaymentAllocateSerializer(serializers.Serializer):
    """To'lovni invoice'larga taqsimlash."""
    payment_id = serializers.UUIDField()
    group_student_id = serializers.UUIDField(required=False, default=None)
