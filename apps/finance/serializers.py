"""
Edvora - Finance Serializers
"""

from rest_framework import serializers
from .models import ExpenseCategory, Expense, Transaction, Salary


class ExpenseCategorySerializer(serializers.ModelSerializer):
    expenses_count = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = ExpenseCategory
        fields = [
            'id', 'name', 'slug', 'icon', 'color',
            'is_active', 'expenses_count', 'total_amount'
        ]

    def get_expenses_count(self, obj):
        return obj.expenses.filter(status='paid').count()

    def get_total_amount(self, obj):
        from django.db.models import Sum
        return obj.expenses.filter(status='paid').aggregate(
            total=Sum('amount')
        )['total'] or 0


class ExpenseListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Expense
        fields = [
            'id', 'category', 'category_name', 'title',
            'amount', 'expense_date', 'status', 'status_display',
            'is_recurring', 'created_at'
        ]


class ExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Expense
        fields = [
            'id', 'category', 'category_name', 'title', 'description',
            'amount', 'expense_date', 'status', 'status_display',
            'created_by', 'created_by_name',
            'approved_by', 'approved_by_name',
            'receipt', 'is_recurring', 'recurring_day',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_created_by_name(self, obj):
        return obj.created_by.full_name if obj.created_by else None

    def get_approved_by_name(self, obj):
        return obj.approved_by.full_name if obj.approved_by else None


class ExpenseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = [
            'category', 'title', 'description', 'amount',
            'expense_date', 'status', 'receipt',
            'is_recurring', 'recurring_day'
        ]

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class TransactionSerializer(serializers.ModelSerializer):
    transaction_type_display = serializers.CharField(
        source='get_transaction_type_display', read_only=True
    )

    class Meta:
        model = Transaction
        fields = [
            'id', 'transaction_type', 'transaction_type_display',
            'amount', 'transaction_date', 'description',
            'payment', 'expense', 'salary',
            'created_by', 'created_at'
        ]


class SalaryListSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Salary
        fields = [
            'id', 'teacher', 'teacher_name',
            'period_month', 'period_year',
            'base_salary', 'bonus', 'deduction', 'total',
            'status', 'status_display'
        ]


class SalarySerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    approved_by_name = serializers.SerializerMethodField()
    paid_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Salary
        fields = [
            'id', 'teacher', 'teacher_name',
            'period_month', 'period_year',
            'base_salary', 'bonus', 'deduction', 'total',
            'total_lessons', 'total_students', 'calculation_details',
            'status', 'status_display',
            'approved_by', 'approved_by_name', 'approved_at',
            'paid_by', 'paid_by_name', 'paid_at',
            'note', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'total', 'created_at', 'updated_at']

    def get_approved_by_name(self, obj):
        return obj.approved_by.full_name if obj.approved_by else None

    def get_paid_by_name(self, obj):
        return obj.paid_by.full_name if obj.paid_by else None


class SalaryCalculateSerializer(serializers.Serializer):
    """Ish haqini hisoblash uchun"""
    month = serializers.IntegerField(min_value=1, max_value=12)
    year = serializers.IntegerField(min_value=2020)
    teacher_id = serializers.UUIDField(required=False)


class FinanceSummarySerializer(serializers.Serializer):
    """Moliyaviy xulosa"""
    total_income = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_expense = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_salary = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_profit = serializers.DecimalField(max_digits=12, decimal_places=2)
    period = serializers.DictField()