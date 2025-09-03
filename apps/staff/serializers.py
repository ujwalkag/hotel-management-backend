
# apps/staff/serializers.py - Complete Staff Management Serializers
from rest_framework import serializers
from .models import StaffProfile, AttendanceRecord, AdvancePayment
from apps.users.models import CustomUser

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'role', 'is_active', 'can_create_orders', 'can_generate_bills', 'can_access_kitchen']

class StaffProfileSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer(read_only=True)
    current_month_attendance = serializers.ReadOnlyField()

    class Meta:
        model = StaffProfile
        fields = [
            'id', 'user', 'employee_id', 'full_name', 'phone', 'address',
            'date_of_birth', 'hire_date', 'department', 'position', 
            'base_salary', 'hourly_rate', 'employment_status',
            'emergency_contact_name', 'emergency_contact_phone',
            'current_month_attendance', 'created_at', 'updated_at'
        ]

class AttendanceRecordSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='staff.full_name', read_only=True)
    staff_employee_id = serializers.CharField(source='staff.employee_id', read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = [
            'id', 'staff', 'staff_name', 'staff_employee_id', 'date',
            'check_in_time', 'check_out_time', 'break_duration',
            'total_hours', 'overtime_hours', 'status', 'notes',
            'created_by', 'created_at'
        ]

class AdvancePaymentSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='staff.full_name', read_only=True)

    class Meta:
        model = AdvancePayment
        fields = [
            'id', 'staff', 'staff_name', 'amount', 'reason',
            'request_date', 'status', 'approved_by', 'approved_date',
            'paid_date', 'remaining_amount', 'monthly_deduction', 'notes'
        ]

