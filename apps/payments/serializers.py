"""
Edvora - Payments Serializers
"""

from rest_framework import serializers
from .models import Payment, Invoice, Discount


class PaymentListSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    group_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'student', 'student_name', 'group', 'group_name',
            'amount', 'payment_method', 'payment_method_display',
            'payment_type', 'payment_type_display',
            'status', 'status_display', 'receipt_number',
            'period_month', 'period_year', 'created_at'
        ]

    def get_group_name(self, obj):
        return obj.group.name if obj.group else None


class PaymentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    group_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    received_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            'id', 'student', 'student_name', 'group', 'group_name',
            'amount', 'payment_method', 'payment_method_display',
            'payment_type', 'payment_type_display',
            'status', 'status_display', 'receipt_number',
            'period_month', 'period_year',
            'received_by', 'received_by_name',
            'external_id', 'note',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'receipt_number', 'created_at', 'updated_at']

    def get_group_name(self, obj):
        return obj.group.name if obj.group else None

    def get_received_by_name(self, obj):
        return obj.received_by.full_name if obj.received_by else None


class PaymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'student', 'group', 'amount',
            'payment_method', 'payment_type',
            'period_month', 'period_year', 'note'
        ]

    def create(self, validated_data):
        validated_data['received_by'] = self.context['request'].user
        validated_data['status'] = 'completed'
        return super().create(validated_data)


class InvoiceListSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    group_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    remaining = serializers.ReadOnlyField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'student', 'student_name',
            'group', 'group_name', 'period_month', 'period_year',
            'total', 'paid_amount', 'remaining',
            'status', 'status_display', 'due_date'
        ]

    def get_group_name(self, obj):
        return obj.group.name if obj.group else None


class InvoiceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    group_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    remaining = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    payments_list = PaymentListSerializer(source='payments', many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'student', 'student_name',
            'group', 'group_name', 'period_month', 'period_year',
            'amount', 'discount', 'total', 'paid_amount', 'remaining',
            'status', 'status_display', 'due_date', 'paid_at', 'is_overdue',
            'payments_list', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'invoice_number', 'created_at', 'updated_at']

    def get_group_name(self, obj):
        return obj.group.name if obj.group else None


class InvoiceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = [
            'student', 'group', 'period_month', 'period_year',
            'amount', 'discount', 'due_date'
        ]


class DiscountSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    group_name = serializers.SerializerMethodField()
    discount_type_display = serializers.CharField(source='get_discount_type_display', read_only=True)

    class Meta:
        model = Discount
        fields = [
            'id', 'student', 'student_name', 'group', 'group_name',
            'name', 'discount_type', 'discount_type_display', 'value',
            'start_date', 'end_date', 'is_active', 'reason',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_group_name(self, obj):
        return obj.group.name if obj.group else None


class DebtorSerializer(serializers.Serializer):
    """Qarzdorlar ro'yxati"""
    student_id = serializers.UUIDField()
    student_name = serializers.CharField()
    student_phone = serializers.CharField()
    parent_phone = serializers.CharField(allow_null=True)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    groups = serializers.ListField(child=serializers.DictField())