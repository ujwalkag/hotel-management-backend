# apps/staff/models.py - FIXED VERSION (NO CIRCULAR IMPORTS)
"""
STAFF MANAGEMENT SYSTEM - Complete HR & Payroll
FIXED: Removed circular import from line 6
COMPATIBLE: Works with existing CustomUser system
"""

from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.users.models import CustomUser  # Your existing user model - NO CIRCULAR IMPORT
from decimal import Decimal
from datetime import datetime, date, timedelta
import uuid

class StaffDepartment(models.Model):
    """Departments for organizing staff"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    head_of_department = models.CharField(max_length=100, blank=True)
    budget_allocation = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'staff_departments'
        verbose_name = 'Staff Department'
        verbose_name_plural = 'Staff Departments'
        ordering = ['name']

class StaffEmployee(models.Model):
    """
    Complete HR Management System - Separate from User Access Control
    This handles employee data, payroll, attendance etc.
    Links to CustomUser only if staff needs system access
    """
    EMPLOYMENT_STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('terminated', 'Terminated'),
        ('on_leave', 'On Leave'),
        ('probation', 'Probation'),
        ('suspended', 'Suspended'),
    ]

    EMPLOYMENT_TYPE_CHOICES = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('temporary', 'Temporary'),
        ('hourly', 'Hourly'),
    ]

    SHIFT_TYPE_CHOICES = [
        ('day', 'Day Shift (6 AM - 6 PM)'),
        ('night', 'Night Shift (6 PM - 6 AM)'),
        ('rotational', 'Rotational'),
        ('flexible', 'Flexible'),
    ]

    # Basic Information
    employee_id = models.CharField(max_length=20, unique=True, blank=True)
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True, null=True, blank=True)
    phone = models.CharField(max_length=15)

    # Link to system user (optional - only if staff needs system access)
    system_user = models.OneToOneField(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Link to system user account if staff needs app access"
    )

    # Personal Details
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)

    # Employment Details
    department = models.ForeignKey(StaffDepartment, on_delete=models.PROTECT)
    position = models.CharField(max_length=100)
    employment_status = models.CharField(max_length=20, choices=EMPLOYMENT_STATUS_CHOICES, default='active')
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES, default='full_time')
    shift_type = models.CharField(max_length=20, choices=SHIFT_TYPE_CHOICES, default='day')

    # Employment Dates
    hire_date = models.DateField()
    probation_end_date = models.DateField(null=True, blank=True)
    termination_date = models.DateField(null=True, blank=True)

    # Salary Information - HOURLY AND OVERNIGHT SUPPORT
    base_salary = models.DecimalField(max_digits=10, decimal_places=2, help_text="Monthly base salary")
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Hourly rate for hourly employees")
    overtime_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Overtime hourly rate")

    # Shift Allowances - OVERNIGHT PAY SUPPORT
    night_shift_allowance = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text="Additional pay per hour for night shifts")
    weekend_allowance = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text="Additional pay for weekend work")

    # Monthly Allowances
    house_rent_allowance = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    transport_allowance = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    medical_allowance = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    # Bank Details
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=20, blank=True)
    ifsc_code = models.CharField(max_length=11, blank=True)

    # System Fields
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_employees')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Auto-generate employee ID
        if not self.employee_id:
            dept_code = self.department.name[:3].upper() if self.department else 'EMP'
            today = timezone.now().strftime('%y%m')
            count = StaffEmployee.objects.filter(
                created_at__year=timezone.now().year,
                created_at__month=timezone.now().month
            ).count() + 1
            self.employee_id = f"{dept_code}{today}{count:03d}"

        # Auto-calculate overtime rate
        if not self.overtime_rate and self.hourly_rate:
            self.overtime_rate = self.hourly_rate * Decimal('1.5')
        elif not self.overtime_rate and self.base_salary:
            # Calculate hourly rate from monthly salary (160 hours/month)
            self.hourly_rate = self.base_salary / 160
            self.overtime_rate = self.hourly_rate * Decimal('1.5')

        super().save(*args, **kwargs)

    @property
    def age(self):
        if self.date_of_birth:
            return (date.today() - self.date_of_birth).days // 365
        return None

    @property
    def years_of_service(self):
        if self.hire_date:
            return (date.today() - self.hire_date).days // 365
        return 0

    @property
    def current_monthly_salary(self):
        """Calculate total monthly salary including allowances"""
        return (self.base_salary + self.house_rent_allowance + 
                self.transport_allowance + self.medical_allowance)

    def __str__(self):
        return f"{self.employee_id} - {self.full_name}"

    class Meta:
        db_table = 'staff_employees'
        verbose_name = 'Staff Employee'
        verbose_name_plural = 'Staff Employees'
        ordering = ['employee_id']

class StaffAttendance(models.Model):
    """Mobile attendance tracking with location support"""
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('half_day', 'Half Day'),
        ('leave', 'On Leave'),
        ('holiday', 'Holiday'),
        ('weekend', 'Weekend'),
    ]

    employee = models.ForeignKey(StaffEmployee, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')

    # Time tracking
    check_in_time = models.TimeField(null=True, blank=True)
    check_out_time = models.TimeField(null=True, blank=True)
    break_start_time = models.TimeField(null=True, blank=True)
    break_end_time = models.TimeField(null=True, blank=True)

    # Calculated hours - AUTOMATIC CALCULATIONS
    total_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    regular_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    break_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Mobile check-in support
    check_in_location = models.CharField(max_length=255, blank=True)
    check_out_location = models.CharField(max_length=255, blank=True)
    device_info = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    # Shift information
    is_night_shift = models.BooleanField(default=False)
    is_weekend = models.BooleanField(default=False)
    is_holiday = models.BooleanField(default=False)

    # Approval
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    approval_date = models.DateTimeField(null=True, blank=True)

    # Additional info
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def calculate_hours(self):
        """Auto-calculate work hours with night shift support"""
        if self.check_in_time and self.check_out_time:
            # Handle night shift checkout next day
            check_in_datetime = datetime.combine(self.date, self.check_in_time)

            if self.is_night_shift and self.check_out_time < self.check_in_time:
                # Next day checkout
                check_out_datetime = datetime.combine(self.date + timedelta(days=1), self.check_out_time)
            else:
                check_out_datetime = datetime.combine(self.date, self.check_out_time)

            # Calculate total minutes worked
            total_minutes = (check_out_datetime - check_in_datetime).total_seconds() / 60

            # Calculate break time
            break_minutes = 0
            if self.break_start_time and self.break_end_time:
                if self.break_end_time > self.break_start_time:
                    break_delta = datetime.combine(self.date, self.break_end_time) - datetime.combine(self.date, self.break_start_time)
                    break_minutes = break_delta.total_seconds() / 60

            # Update hours
            self.break_hours = Decimal(str(break_minutes / 60))
            worked_minutes = total_minutes - break_minutes
            self.total_hours = Decimal(str(worked_minutes / 60))

            # Calculate regular vs overtime (8 hours standard)
            regular_limit = 8
            if self.total_hours <= regular_limit:
                self.regular_hours = self.total_hours
                self.overtime_hours = Decimal('0')
            else:
                self.regular_hours = Decimal(str(regular_limit))
                self.overtime_hours = self.total_hours - self.regular_hours

            self.save(update_fields=['total_hours', 'regular_hours', 'overtime_hours', 'break_hours'])

    def __str__(self):
        return f"{self.employee.full_name} - {self.date} ({self.get_status_display()})"

    class Meta:
        db_table = 'staff_attendance'
        verbose_name = 'Staff Attendance'
        verbose_name_plural = 'Staff Attendance'
        unique_together = ['employee', 'date']
        ordering = ['-date', 'employee__full_name']

class StaffPayroll(models.Model):
    """Advanced payroll with automatic calculations"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('calculated', 'Calculated'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]

    employee = models.ForeignKey(StaffEmployee, on_delete=models.CASCADE, related_name='payroll_records')
    month = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    year = models.IntegerField()

    # Pay period
    pay_period_start = models.DateField()
    pay_period_end = models.DateField()

    # Hours worked - AUTOMATIC FROM ATTENDANCE
    regular_hours_worked = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    overtime_hours_worked = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    night_shift_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    weekend_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    holiday_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    # Earnings - AUTOMATIC CALCULATIONS
    base_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    overtime_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    night_shift_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    weekend_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    holiday_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Allowances
    hra = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    transport_allowance = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    medical_allowance = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    performance_bonus = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    # Deductions - AUTOMATIC ADVANCE DEDUCTION
    advance_deduction = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    loan_deduction = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    provident_fund = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    professional_tax = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    income_tax = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    # Totals
    gross_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Status and processing
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    calculated_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='calculated_payrolls')
    calculation_date = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_payrolls')
    approval_date = models.DateTimeField(null=True, blank=True)

    # Payment info
    payment_date = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)

    # System fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)

    def calculate_payroll(self):
        """Calculate complete payroll with HOURLY and OVERNIGHT support"""
        # Get attendance records for the period
        attendance_records = StaffAttendance.objects.filter(
            employee=self.employee,
            date__range=[self.pay_period_start, self.pay_period_end],
            is_approved=True
        )

        # Calculate total hours by type
        self.regular_hours_worked = sum(record.regular_hours for record in attendance_records)
        self.overtime_hours_worked = sum(record.overtime_hours for record in attendance_records)
        self.night_shift_hours = sum(record.total_hours for record in attendance_records if record.is_night_shift)
        self.weekend_hours = sum(record.total_hours for record in attendance_records if record.is_weekend)
        self.holiday_hours = sum(record.total_hours for record in attendance_records if record.is_holiday)

        # Calculate pay based on employment type
        if self.employee.employment_type == 'hourly':
            # Hourly employee calculations
            self.base_pay = self.regular_hours_worked * self.employee.hourly_rate
            self.overtime_pay = self.overtime_hours_worked * (self.employee.overtime_rate or self.employee.hourly_rate * Decimal('1.5'))
        else:
            # Monthly salary employee calculations
            working_days = 26  # Standard working days
            present_days = attendance_records.filter(status__in=['present', 'late']).count()
            half_days = attendance_records.filter(status='half_day').count()
            effective_days = present_days + (half_days * 0.5)

            # Proportional base pay
            self.base_pay = (self.employee.base_salary / working_days) * Decimal(str(effective_days))
            self.overtime_pay = self.overtime_hours_worked * (self.employee.overtime_rate or Decimal('100'))

        # Calculate shift allowances - OVERNIGHT PAY
        self.night_shift_pay = self.night_shift_hours * self.employee.night_shift_allowance
        self.weekend_pay = self.weekend_hours * self.employee.weekend_allowance
        self.holiday_pay = self.holiday_hours * (self.employee.hourly_rate or Decimal('100')) * Decimal('2')  # Double pay for holidays

        # Copy allowances from employee
        self.hra = self.employee.house_rent_allowance
        self.transport_allowance = self.employee.transport_allowance
        self.medical_allowance = self.employee.medical_allowance

        # Calculate automatic deductions
        self._calculate_automatic_deductions()

        # Calculate totals
        self.gross_pay = (
            self.base_pay + self.overtime_pay + self.night_shift_pay + 
            self.weekend_pay + self.holiday_pay + self.hra + 
            self.transport_allowance + self.medical_allowance + self.performance_bonus
        )

        self.total_deductions = (
            self.advance_deduction + self.loan_deduction + self.provident_fund + 
            self.professional_tax + self.income_tax + self.other_deductions
        )

        self.net_pay = self.gross_pay - self.total_deductions

        # Update status
        self.status = 'calculated'
        self.calculation_date = timezone.now()
        self.save()

    def _calculate_automatic_deductions(self):
        """Calculate PF, tax, and advance deductions automatically"""
        # PF calculation (12% of basic salary, max 1800)
        if self.gross_pay > 15000:
            self.provident_fund = min(self.base_pay * Decimal('0.12'), Decimal('1800'))

        # Professional tax (state-specific)
        if self.gross_pay > 10000:
            self.professional_tax = Decimal('200')

        # Calculate advance payment deductions
        advance_deduction = Decimal('0')
        active_advances = StaffAdvancePayment.objects.filter(
            employee=self.employee,
            status='disbursed',
            remaining_balance__gt=0
        )

        for advance in active_advances:
            if advance.monthly_deduction_amount:
                deduction_amount = min(advance.monthly_deduction_amount, advance.remaining_balance)
                advance_deduction += deduction_amount

                # Update advance balance
                advance.remaining_balance -= deduction_amount
                if advance.remaining_balance <= 0:
                    advance.status = 'completed'
                advance.save()

        self.advance_deduction = advance_deduction

    def __str__(self):
        return f"{self.employee.full_name} - {self.month:02d}/{self.year}"

    class Meta:
        db_table = 'staff_payroll'
        verbose_name = 'Staff Payroll'
        verbose_name_plural = 'Staff Payroll'
        unique_together = ['employee', 'month', 'year']
        ordering = ['-year', '-month', 'employee__full_name']

class StaffAdvancePayment(models.Model):
    """ADVANCE PAYMENT SYSTEM with automatic payroll deduction"""
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('disbursed', 'Disbursed'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    employee = models.ForeignKey(StaffEmployee, on_delete=models.CASCADE, related_name='advance_payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    urgency_level = models.CharField(
        max_length=10,
        choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('urgent', 'Urgent')],
        default='medium'
    )

    # Request details
    request_date = models.DateField(auto_now_add=True)
    required_by_date = models.DateField()

    # Repayment plan - AUTOMATIC DEDUCTION
    deduction_months = models.IntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(12)])
    monthly_deduction_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    remaining_balance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Approval
    approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_advances')
    approval_date = models.DateTimeField(null=True, blank=True)
    approval_notes = models.TextField(blank=True)

    # Disbursement
    disbursed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='disbursed_advances')
    disbursement_date = models.DateTimeField(null=True, blank=True)
    disbursement_method = models.CharField(max_length=50, blank=True)

    # System fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.monthly_deduction_amount:
            self.monthly_deduction_amount = self.amount / self.deduction_months

        if self.remaining_balance is None:
            self.remaining_balance = self.amount

        super().save(*args, **kwargs)

    def approve_advance(self, approved_by_user, notes=""):
        """Approve the advance payment request"""
        if self.status == 'pending':
            self.status = 'approved'
            self.approved_by = approved_by_user
            self.approval_date = timezone.now()
            self.approval_notes = notes
            self.save()
            return True
        return False

    def disburse_advance(self, disbursed_by_user, method="bank_transfer"):
        """Disburse approved advance payment"""
        if self.status == 'approved':
            self.status = 'disbursed'
            self.disbursed_by = disbursed_by_user
            self.disbursement_date = timezone.now()
            self.disbursement_method = method
            self.save()
            return True
        return False

    def __str__(self):
        return f"{self.employee.full_name} - ₹{self.amount} ({self.get_status_display()})"

    class Meta:
        db_table = 'staff_advance_payments'
        verbose_name = 'Staff Advance Payment'
        verbose_name_plural = 'Staff Advance Payments'
        ordering = ['-created_at']

