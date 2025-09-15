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

class AttendanceWithPaymentSerializer(serializers.ModelSerializer):
    """Enhanced attendance serializer with payment control"""
    employee_name = serializers.CharField(source='employee.name', read_only=True)
    employee_designation = serializers.CharField(source='employee.designation.name', read_only=True)
    daily_wage = serializers.SerializerMethodField()
    payment_amount = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = [
            'id', 'employee', 'employee_name', 'employee_designation', 'date',
            'is_present', 'include_payment', 'daily_wage', 'payment_amount',
            'remarks', 'created_at'
        ]

    def get_daily_wage(self, obj):
        return float(obj.employee.get_effective_daily_wage())

    def get_payment_amount(self, obj):
        """Calculate payment amount for this attendance record"""
        if obj.include_payment:
            return float(obj.employee.get_effective_daily_wage())
        return 0.0

class MonthlyPaymentSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.name', read_only=True)
    employee_designation = serializers.CharField(source='employee.designation.name', read_only=True)

    class Meta:
        model = MonthlyPayment
        fields = [
            'id', 'employee', 'employee_name', 'employee_designation', 'year', 'month',
            'base_salary', 'attendance_bonus', 'deductions',
            'total_paid', 'payment_date', 'present_days', 'paid_days',
            'working_days', 'remarks', 'created_at'
        ]

class EmployeeDetailSerializer(serializers.ModelSerializer):
    """Enhanced employee detail serializer with comprehensive information"""
    designation_name = serializers.CharField(source='designation.name', read_only=True)
    effective_daily_wage = serializers.SerializerMethodField()
    total_pay = serializers.SerializerMethodField()
    monthly_stats = serializers.SerializerMethodField()
    yearly_stats = serializers.SerializerMethodField()
    recent_payments = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            'id', 'name', 'address', 'aadhar_number', 'phone',
            'designation', 'designation_name', 'monthly_salary',
            'daily_wage', 'effective_daily_wage', 'date_of_joining',
            'is_active', 'total_pay', 'monthly_stats', 'yearly_stats',
            'recent_payments', 'created_at', 'updated_at'
        ]

    def get_effective_daily_wage(self, obj):
        return float(obj.get_effective_daily_wage())

    def get_total_pay(self, obj):
        return float(obj.get_total_pay())

    def get_monthly_stats(self, obj):
        """Get current month statistics"""
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month

        present_days = obj.get_monthly_present(current_year, current_month)
        absent_days = obj.get_monthly_absent(current_year, current_month)
        paid_days = obj.get_monthly_paid_days(current_year, current_month)
        monthly_pay_by_attendance = obj.get_monthly_pay_by_attendance(current_year, current_month)

        return {
            'monthly_present': present_days,
            'monthly_absent': absent_days,
            'monthly_paid_days': paid_days,
            'monthly_pay_by_attendance': float(monthly_pay_by_attendance),
            'fixed_monthly_salary': float(obj.monthly_salary),
            'current_month': current_month,
            'current_year': current_year
        }

    def get_yearly_stats(self, obj):
        """Get current year statistics"""
        current_date = datetime.now()
        current_year = current_date.year

        from datetime import date
        yearly_stats = obj.get_attendance_stats(
            start_date=date(current_year, 1, 1),
            end_date=date(current_year, 12, 31)
        )

        return {
            'year': current_year,
            'total_present': yearly_stats['total_present'],
            'total_absent': yearly_stats['total_absent'],
            'total_paid_days': yearly_stats['total_paid_days'],
            'total_pay': float(yearly_stats['total_pay'])
        }

    def get_recent_payments(self, obj):
        """Get recent payment records"""
        payments = MonthlyPayment.objects.filter(employee=obj).order_by('-year', '-month')[:6]
        return MonthlyPaymentSerializer(payments, many=True).data

class EmployeeCustomRangeSerializer(serializers.Serializer):
    """Serializer for custom date range employee details"""
    employee = EmployeeSerializer(read_only=True)
    period = serializers.DictField(read_only=True)
    attendance_summary = serializers.DictField(read_only=True)
    monthly_stats = serializers.DictField(read_only=True)
    attendance_records = AttendanceWithPaymentSerializer(many=True, read_only=True)
    recent_payments = MonthlyPaymentSerializer(many=True, read_only=True)

class PayrollSummarySerializer(serializers.Serializer):
    """Serializer for payroll summary with custom time intervals"""
    total_employees = serializers.IntegerField(read_only=True)
    designations = serializers.ListField(read_only=True)
    period_summary = serializers.DictField(read_only=True)
    total_paid = serializers.DictField(read_only=True)

class AttendanceSheetSerializer(serializers.Serializer):
    """Serializer for daily attendance sheet with payment control"""
    employee_id = serializers.IntegerField()
    employee_name = serializers.CharField(read_only=True)
    designation = serializers.CharField(read_only=True)
    monthly_salary = serializers.FloatField(read_only=True)
    daily_wage = serializers.FloatField(read_only=True)
    is_present = serializers.BooleanField()
    include_payment = serializers.BooleanField()
    remarks = serializers.CharField(allow_blank=True)

    def validate(self, data):
        """Validate attendance data"""
        # If not present but payment is included, this might be intentional (sick pay, etc.)
        # So we don't enforce any strict validation here
        return data
