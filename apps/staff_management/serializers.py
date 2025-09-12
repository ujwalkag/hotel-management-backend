from rest_framework import serializers
from .models import Employee, Designation, Attendance, MonthlyPayment
from datetime import datetime

class DesignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Designation
        fields = ['id', 'name', 'daily_wage', 'monthly_salary', 'description', 'created_at']

class EmployeeSerializer(serializers.ModelSerializer):
    designation_name = serializers.CharField(source='designation.name', read_only=True)
    effective_daily_wage = serializers.SerializerMethodField()
    total_pay = serializers.SerializerMethodField()
    
    class Meta:
        model = Employee
        fields = [
            'id', 'name', 'address', 'aadhar_number', 'phone',
            'designation', 'designation_name', 'monthly_salary',
            'daily_wage', 'effective_daily_wage', 'date_of_joining', 
            'is_active', 'total_pay', 'created_at', 'updated_at'
        ]
    
    def get_effective_daily_wage(self, obj):
        return float(obj.get_effective_daily_wage())
    
    def get_total_pay(self, obj):
        return float(obj.get_total_pay())

class AttendanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.name', read_only=True)
    
    class Meta:
        model = Attendance
        fields = [
            'id', 'employee', 'employee_name', 'date',
            'is_present', 'remarks', 'created_at'
        ]

class MonthlyPaymentSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.name', read_only=True)
    
    class Meta:
        model = MonthlyPayment
        fields = [
            'id', 'employee', 'employee_name', 'year', 'month',
            'base_salary', 'attendance_bonus', 'deductions',
            'total_paid', 'payment_date', 'present_days',
            'working_days', 'remarks', 'created_at'
        ]

class EmployeeDetailSerializer(serializers.ModelSerializer):
    designation_name = serializers.CharField(source='designation.name', read_only=True)
    effective_daily_wage = serializers.SerializerMethodField()
    total_pay = serializers.SerializerMethodField()
    monthly_stats = serializers.SerializerMethodField()
    recent_payments = serializers.SerializerMethodField()
    
    class Meta:
        model = Employee
        fields = [
            'id', 'name', 'address', 'aadhar_number', 'phone',
            'designation', 'designation_name', 'monthly_salary',
            'daily_wage', 'effective_daily_wage', 'date_of_joining',
            'is_active', 'total_pay', 'monthly_stats', 'recent_payments',
            'created_at', 'updated_at'
        ]
    
    def get_effective_daily_wage(self, obj):
        return float(obj.get_effective_daily_wage())
    
    def get_total_pay(self, obj):
        return float(obj.get_total_pay())
    
    def get_monthly_stats(self, obj):
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        present_days = obj.get_monthly_present(current_year, current_month)
        absent_days = obj.get_monthly_absent(current_year, current_month)
        monthly_pay_by_attendance = obj.get_monthly_pay_by_attendance(current_year, current_month)
        
        return {
            'monthly_present': present_days,
            'monthly_absent': absent_days,
            'monthly_pay_by_attendance': float(monthly_pay_by_attendance),
            'fixed_monthly_salary': float(obj.monthly_salary),
            'current_month': current_month,
            'current_year': current_year
        }
    
    def get_recent_payments(self, obj):
        payments = MonthlyPayment.objects.filter(employee=obj).order_by('-year', '-month')[:6]
        return MonthlyPaymentSerializer(payments, many=True).data

