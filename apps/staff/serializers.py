# apps/staff/serializers.py
from rest_framework import serializers
from django.utils import timezone
from .models import StaffProfile, Attendance, PaymentRecord, AdvancePayment

class StaffProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    total_worked_days = serializers.ReadOnlyField()
    total_earned = serializers.ReadOnlyField()
    total_paid = serializers.ReadOnlyField()
    pending_salary = serializers.ReadOnlyField()
    current_month_attendance = serializers.ReadOnlyField()
    position_display = serializers.CharField(source='get_position_display', read_only=True)

    class Meta:
        model = StaffProfile
        fields = ['id', 'user', 'user_email', 'employee_id', 'phone', 'position', 
                 'position_display', 'salary_per_day', 'joining_date', 'is_active', 
                 'address', 'emergency_contact', 'emergency_contact_name', 
                 'bank_account_number', 'bank_name', 'aadhar_number', 'total_worked_days', 
                 'total_earned', 'total_paid', 'pending_salary', 'current_month_attendance',
                 'created_at', 'updated_at']
        read_only_fields = ['user_email', 'total_worked_days', 'total_earned', 
                           'total_paid', 'pending_salary', 'current_month_attendance',
                           'created_at', 'updated_at']

    def validate_employee_id(self, value):
        if self.instance and self.instance.employee_id == value:
            return value
        if StaffProfile.objects.filter(employee_id=value).exists():
            raise serializers.ValidationError("Employee ID must be unique")
        return value

    def validate_phone(self, value):
        if not value.isdigit() or len(value) < 10:
            raise serializers.ValidationError("Enter a valid phone number")
        return value

    def validate_salary_per_day(self, value):
        if value <= 0:
            raise serializers.ValidationError("Salary per day must be greater than 0")
        return value

class AttendanceSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='staff.user.email', read_only=True)
    employee_id = serializers.CharField(source='staff.employee_id', read_only=True)
    position = serializers.CharField(source='staff.position', read_only=True)
    marked_by_name = serializers.CharField(source='marked_by.email', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Attendance
        fields = ['id', 'staff', 'staff_name', 'employee_id', 'position', 'date', 
                 'check_in_time', 'check_out_time', 'status', 'status_display', 
                 'total_hours', 'overtime_hours', 'salary_amount', 'notes', 
                 'marked_by', 'marked_by_name', 'created_at', 'updated_at']
        read_only_fields = ['salary_amount', 'marked_by', 'marked_by_name', 
                           'created_at', 'updated_at']

class AttendanceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = ['staff', 'date', 'check_in_time', 'check_out_time', 'status', 
                 'total_hours', 'overtime_hours', 'notes']

    def validate_date(self, value):
        if value > timezone.now().date():
            raise serializers.ValidationError("Cannot mark attendance for future dates")
        return value

    def validate(self, data):
        # Check if attendance already exists for this staff and date
        staff = data.get('staff')
        date = data.get('date')
        
        if staff and date:
            existing = Attendance.objects.filter(
                staff=staff, 
                date=date
            ).exclude(pk=getattr(self.instance, 'pk', None))
            
            if existing.exists():
                raise serializers.ValidationError(
                    "Attendance already exists for this staff member on this date"
                )
        
        # Validate check times
        check_in = data.get('check_in_time')
        check_out = data.get('check_out_time')
        
        if check_in and check_out:
            if check_out <= check_in:
                raise serializers.ValidationError(
                    "Check out time must be after check in time"
                )
        
        return data

class BulkAttendanceSerializer(serializers.Serializer):
    date = serializers.DateField()
    attendance_records = serializers.ListField(
        child=serializers.DictField()
    )

    def validate_date(self, value):
        if value > timezone.now().date():
            raise serializers.ValidationError("Cannot mark attendance for future dates")
        return value

    def validate_attendance_records(self, value):
        if not value:
            raise serializers.ValidationError("At least one attendance record is required")
            
        for record in value:
            if 'staff_id' not in record or 'status' not in record:
                raise serializers.ValidationError(
                    "Each attendance record must have staff_id and status"
                )
        return value

class PaymentRecordSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='staff.user.email', read_only=True)
    employee_id = serializers.CharField(source='staff.employee_id', read_only=True)
    paid_by_name = serializers.CharField(source='paid_by.email', read_only=True)
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)

    class Meta:
        model = PaymentRecord
        fields = ['id', 'staff', 'staff_name', 'employee_id', 'payment_date', 
                 'amount_paid', 'payment_type', 'payment_type_display', 
                 'payment_method', 'payment_method_display', 'reference_number',
                 'description', 'from_date', 'to_date', 'paid_by', 'paid_by_name',
                 'created_at']
        read_only_fields = ['paid_by', 'paid_by_name', 'created_at']

    def validate_amount_paid(self, value):
        if value <= 0:
            raise serializers.ValidationError("Payment amount must be greater than 0")
        return value

    def validate(self, data):
        # Validate date range for salary payments
        payment_type = data.get('payment_type')
        from_date = data.get('from_date')
        to_date = data.get('to_date')
        
        if payment_type == 'salary':
            if not from_date or not to_date:
                raise serializers.ValidationError(
                    "From date and to date are required for salary payments"
                )
            if to_date <= from_date:
                raise serializers.ValidationError(
                    "To date must be after from date"
                )
        
        return data

class AdvancePaymentSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='staff.user.email', read_only=True)
    employee_id = serializers.CharField(source='staff.employee_id', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.email', read_only=True)
    remaining_amount = serializers.ReadOnlyField()
    adjustment_progress = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = AdvancePayment
        fields = ['id', 'staff', 'staff_name', 'employee_id', 'advance_date', 
                 'amount', 'reason', 'status', 'status_display', 'adjustment_start_date',
                 'adjustment_amount_per_day', 'total_adjusted', 'remaining_amount',
                 'adjustment_progress', 'approved_by', 'approved_by_name', 'notes',
                 'created_at', 'updated_at']
        read_only_fields = ['approved_by', 'approved_by_name', 'remaining_amount',
                           'adjustment_progress', 'created_at', 'updated_at']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Advance amount must be greater than 0")
        return value

    def validate_reason(self, value):
        if not value.strip():
            raise serializers.ValidationError("Reason for advance is required")
        return value.strip()

class StaffSummarySerializer(serializers.ModelSerializer):
    """Summary serializer for dashboard views"""
    user_email = serializers.CharField(source='user.email', read_only=True)
    position_display = serializers.CharField(source='get_position_display', read_only=True)
    pending_salary = serializers.ReadOnlyField()
    last_attendance = serializers.SerializerMethodField()
    
    class Meta:
        model = StaffProfile
        fields = ['id', 'user_email', 'employee_id', 'position', 'position_display',
                 'salary_per_day', 'is_active', 'pending_salary', 'last_attendance']
    
    def get_last_attendance(self, obj):
        last_record = obj.attendance_records.first()
        if last_record:
            return {
                'date': last_record.date,
                'status': last_record.status,
                'status_display': last_record.get_status_display()
            }
        return None

class AttendanceSummarySerializer(serializers.Serializer):
    """Serializer for attendance summary reports"""
    date = serializers.DateField()
    total_staff = serializers.IntegerField()
    present_count = serializers.IntegerField()
    absent_count = serializers.IntegerField()
    half_day_count = serializers.IntegerField()
    leave_count = serializers.IntegerField()
    overtime_count = serializers.IntegerField()
    total_salary = serializers.DecimalField(max_digits=12, decimal_places=2)
