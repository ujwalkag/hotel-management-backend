from rest_framework import serializers
from .models import StaffDepartment, StaffEmployee, StaffAttendance, StaffPayroll, StaffAdvancePayment
from django.utils import timezone
from decimal import Decimal

class StaffDepartmentSerializer(serializers.ModelSerializer):
    employee_count = serializers.SerializerMethodField()
    total_budget = serializers.ReadOnlyField(source='budget_allocation')
    
    class Meta:
        model = StaffDepartment
        fields = '__all__'
        
    def get_employee_count(self, obj):
        return obj.staffemployee_set.filter(is_active=True).count()

class StaffEmployeeListSerializer(serializers.ModelSerializer):
    """Simplified serializer for employee lists"""
    department_name = serializers.CharField(source='department.name', read_only=True)
    age = serializers.ReadOnlyField()
    years_of_service = serializers.ReadOnlyField()
    current_monthly_salary = serializers.ReadOnlyField()
    
    class Meta:
        model = StaffEmployee
        fields = [
            'id', 'employee_id', 'full_name', 'phone', 'email',
            'department_name', 'position', 'employment_status',
            'employment_type', 'base_salary', 'current_monthly_salary',
            'age', 'years_of_service', 'hire_date', 'is_active'
        ]

class StaffEmployeeDetailSerializer(serializers.ModelSerializer):
    """Complete serializer for employee details"""
    department_name = serializers.CharField(source='department.name', read_only=True)
    age = serializers.ReadOnlyField()
    years_of_service = serializers.ReadOnlyField()
    current_monthly_salary = serializers.ReadOnlyField()
    system_user_email = serializers.CharField(source='system_user.email', read_only=True)
    
    class Meta:
        model = StaffEmployee
        fields = '__all__'
        
    def validate(self, data):
        # Validate hire_date is not in future
        if data.get('hire_date') and data['hire_date'] > timezone.now().date():
            raise serializers.ValidationError("Hire date cannot be in the future")
        
        # Validate salary is positive
        if data.get('base_salary') and data['base_salary'] <= 0:
            raise serializers.ValidationError("Base salary must be positive")
            
        return data

class StaffAttendanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    employee_id = serializers.CharField(source='employee.employee_id', read_only=True)
    
    class Meta:
        model = StaffAttendance
        fields = '__all__'
        read_only_fields = ['total_hours', 'regular_hours', 'overtime_hours', 'break_hours']

class MobileAttendanceSerializer(serializers.Serializer):
    """Mobile check-in/out serializer"""
    employee_id = serializers.CharField(max_length=20)
    location = serializers.CharField(max_length=255, required=False, allow_blank=True)
    device_info = serializers.JSONField(required=False, default=dict)
    action = serializers.ChoiceField(choices=['check_in', 'check_out'], default='check_in')

class StaffPayrollSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    employee_id = serializers.CharField(source='employee.employee_id', read_only=True)
    
    class Meta:
        model = StaffPayroll
        fields = '__all__'
        read_only_fields = [
            'regular_hours_worked', 'overtime_hours_worked', 'night_shift_hours',
            'weekend_hours', 'holiday_hours', 'base_pay', 'overtime_pay',
            'night_shift_pay', 'weekend_pay', 'holiday_pay', 'advance_deduction',
            'gross_pay', 'total_deductions', 'net_pay'
        ]

class StaffAdvancePaymentSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    employee_id = serializers.CharField(source='employee.employee_id', read_only=True)
    
    class Meta:
        model = StaffAdvancePayment
        fields = '__all__'
        read_only_fields = ['monthly_deduction_amount', 'remaining_balance']
