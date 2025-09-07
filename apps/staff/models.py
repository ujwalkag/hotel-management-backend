
# apps/staff/models.py - COMPLETELY UPDATED FOR SEPARATE STAFF MANAGEMENT
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.users.models import CustomUser
from decimal import Decimal
from datetime import date, datetime
import uuid

class StaffProfile(models.Model):
    """
    Separate staff management - NOT linked to base users
    This is for attendance and payroll only
    """
    DEPARTMENT_CHOICES = [
        ('kitchen', 'Kitchen'),
        ('service', 'Service'),
        ('housekeeping', 'Housekeeping'), 
        ('management', 'Management'),
        ('billing', 'Billing'),
        ('security', 'Security'),
    ]

    EMPLOYMENT_STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('terminated', 'Terminated'),
        ('on_leave', 'On Leave'),
    ]

    # Basic Information
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    employee_id = models.CharField(max_length=20, unique=True, blank=True)
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    department = models.CharField(max_length=20, choices=DEPARTMENT_CHOICES)
    position = models.CharField(max_length=100)

    # Employment Details
    hire_date = models.DateField()
    employment_status = models.CharField(max_length=20, choices=EMPLOYMENT_STATUS_CHOICES, default='active')
    base_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    hourly_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    # Additional Information
    emergency_contact = models.CharField(max_length=255, blank=True)
    emergency_phone = models.CharField(max_length=15, blank=True)
    notes = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.employee_id:
            # Generate unique employee ID
            prefix = self.department[:3].upper()
            random_id = str(uuid.uuid4().hex[:6]).upper()
            self.employee_id = f"{prefix}-{random_id}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} ({self.employee_id})"

    class Meta:
        db_table = 'staff_profiles'
        verbose_name = 'Staff Profile'
        verbose_name_plural = 'Staff Profiles'
        ordering = ['full_name']

class AttendanceRecord(models.Model):
    """Daily attendance tracking for staff"""
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('half_day', 'Half Day'),
        ('leave', 'Leave'),
        ('holiday', 'Holiday'),
    ]

    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    total_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    overtime_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def calculate_hours(self):
        """Calculate total and overtime hours"""
        if self.check_in and self.check_out:
            # Convert to datetime for calculation
            checkin_dt = datetime.combine(self.date, self.check_in)
            checkout_dt = datetime.combine(self.date, self.check_out)

            # Handle next day checkout
            if checkout_dt < checkin_dt:
                checkout_dt = checkout_dt.replace(day=checkout_dt.day + 1)

            total_minutes = (checkout_dt - checkin_dt).total_seconds() / 60
            self.total_hours = Decimal(total_minutes / 60)

            # Calculate overtime (more than 8 hours)
            if self.total_hours > 8:
                self.overtime_hours = self.total_hours - 8
            else:
                self.overtime_hours = 0

        self.save()

    def __str__(self):
        return f"{self.staff.full_name} - {self.date} ({self.status})"

    class Meta:
        db_table = 'staff_attendance'
        unique_together = ['staff', 'date']
        verbose_name = 'Attendance Record'
        verbose_name_plural = 'Attendance Records'
        ordering = ['-date']

class PayrollRecord(models.Model):
    """Monthly payroll calculation for staff"""
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='payroll_records')
    month = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    year = models.IntegerField(validators=[MinValueValidator(2020)])

    # Salary Components
    base_salary = models.DecimalField(max_digits=10, decimal_places=2)
    overtime_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Attendance Summary
    total_working_days = models.IntegerField(default=0)
    days_present = models.IntegerField(default=0)
    days_absent = models.IntegerField(default=0)
    total_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    overtime_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    # Final Amounts
    gross_salary = models.DecimalField(max_digits=10, decimal_places=2)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2)

    # Payment Information
    payment_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, default='cash')
    payment_status = models.CharField(max_length=20, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def calculate_payroll(self):
        """Calculate monthly payroll based on attendance"""
        # Get attendance records for the month
        attendance_records = AttendanceRecord.objects.filter(
            staff=self.staff,
            date__year=self.year,
            date__month=self.month
        )

        self.days_present = attendance_records.filter(status='present').count()
        self.days_absent = attendance_records.filter(status='absent').count()
        self.total_hours = sum([record.total_hours for record in attendance_records])
        self.overtime_hours = sum([record.overtime_hours for record in attendance_records])

        # Calculate overtime amount
        self.overtime_amount = self.overtime_hours * self.staff.hourly_rate * Decimal('1.5')

        # Calculate gross salary
        self.gross_salary = self.base_salary + self.overtime_amount + self.bonus

        # Calculate net salary
        self.net_salary = self.gross_salary - self.deductions

        self.save()

    def __str__(self):
        return f"{self.staff.full_name} - {self.month}/{self.year}"

    class Meta:
        db_table = 'staff_payroll'
        unique_together = ['staff', 'month', 'year']
        verbose_name = 'Payroll Record'
        verbose_name_plural = 'Payroll Records'
        ordering = ['-year', '-month']

class LeaveRequest(models.Model):
    """Leave request management"""
    LEAVE_TYPE_CHOICES = [
        ('casual', 'Casual Leave'),
        ('sick', 'Sick Leave'), 
        ('annual', 'Annual Leave'),
        ('emergency', 'Emergency Leave'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.IntegerField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_by = models.CharField(max_length=255, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Calculate total days
        self.total_days = (self.end_date - self.start_date).days + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.staff.full_name} - {self.leave_type} ({self.start_date} to {self.end_date})"

    class Meta:
        db_table = 'staff_leave_requests'
        verbose_name = 'Leave Request'
        verbose_name_plural = 'Leave Requests'
        ordering = ['-created_at']

