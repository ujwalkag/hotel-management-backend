# apps/staff/models.py - FIXED VERSION WITHOUT CIRCULAR IMPORTS
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.users.models import CustomUser
from decimal import Decimal
from datetime import datetime, date, timedelta
import uuid

class Department(models.Model):
    """Departments for staff organization"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    head_of_department = models.CharField(max_length=100, blank=True)
    budget = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'staff_departments'
        ordering = ['name']

class StaffProfile(models.Model):
    """Complete staff profile for HR management - SEPARATE from user access control"""
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
        ('intern', 'Intern'),
        ('consultant', 'Consultant'),
    ]

    SHIFT_TYPE_CHOICES = [
        ('day', 'Day Shift'),
        ('night', 'Night Shift'),
        ('rotational', 'Rotational'),
        ('flexible', 'Flexible'),
    ]

    MARITAL_STATUS_CHOICES = [
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
    ]

    # Basic Information
    employee_id = models.CharField(max_length=20, unique=True, blank=True)
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True, null=True, blank=True)
    phone = models.CharField(max_length=15)
    alternative_phone = models.CharField(max_length=15, blank=True)

    # Link to user account (optional - for staff who need system access)
    user = models.OneToOneField(CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
                               help_text="Link to system user account if staff needs system access")

    # Personal Details
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], blank=True)
    marital_status = models.CharField(max_length=10, choices=MARITAL_STATUS_CHOICES, blank=True)
    blood_group = models.CharField(max_length=5, blank=True)
    nationality = models.CharField(max_length=50, default='Indian')

    # Address Information
    current_address = models.TextField()
    permanent_address = models.TextField(blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)

    # Employment Details
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    position = models.CharField(max_length=100)
    employment_status = models.CharField(max_length=20, choices=EMPLOYMENT_STATUS_CHOICES, default='active')
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES, default='full_time')
    shift_type = models.CharField(max_length=20, choices=SHIFT_TYPE_CHOICES, default='day')

    # Dates
    hire_date = models.DateField()
    probation_end_date = models.DateField(null=True, blank=True)
    termination_date = models.DateField(null=True, blank=True)
    contract_end_date = models.DateField(null=True, blank=True)

    # Salary Information
    base_salary = models.DecimalField(max_digits=10, decimal_places=2)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    overtime_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    night_shift_allowance = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    # Allowances
    house_rent_allowance = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    transport_allowance = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    medical_allowance = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    special_allowance = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    # Bank Details
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account_number = models.CharField(max_length=20, blank=True)
    ifsc_code = models.CharField(max_length=11, blank=True)

    # Documents
    aadhar_number = models.CharField(max_length=12, blank=True)
    pan_number = models.CharField(max_length=10, blank=True)
    passport_number = models.CharField(max_length=20, blank=True)

    # Emergency Contact
    emergency_contact_name = models.CharField(max_length=255, blank=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True)
    emergency_contact_relation = models.CharField(max_length=50, blank=True)

    # System Fields
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_staff')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Profile Picture
    profile_picture = models.ImageField(upload_to='staff_profiles/', null=True, blank=True)

    # Additional Information
    skills = models.TextField(blank=True)
    certifications = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if not self.employee_id:
            # Generate employee ID
            dept_code = self.department.name[:3].upper() if self.department else 'STF'
            today = timezone.now().strftime('%y%m')
            count = StaffProfile.objects.filter(
                created_at__year=timezone.now().year,
                created_at__month=timezone.now().month
            ).count() + 1
            self.employee_id = f"{dept_code}{today}{count:03d}"

        # Auto-calculate overtime rate if not provided
        if not self.overtime_rate and self.hourly_rate:
            self.overtime_rate = self.hourly_rate * Decimal('1.5')
        elif not self.overtime_rate and self.base_salary:
            monthly_hours = 160  # Assuming 8 hours * 20 days
            self.hourly_rate = self.base_salary / monthly_hours
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
    def is_on_probation(self):
        if self.probation_end_date:
            return date.today() <= self.probation_end_date
        return False

    @property
    def current_salary(self):
        return self.base_salary + self.house_rent_allowance + self.transport_allowance + self.medical_allowance + self.special_allowance

    def __str__(self):
        return f"{self.employee_id} - {self.full_name}"

    class Meta:
        db_table = 'staff_profiles'
        ordering = ['employee_id']
        verbose_name = 'Staff Profile'
        verbose_name_plural = 'Staff Profiles'

class AttendanceRecord(models.Model):
    """Daily attendance tracking"""
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('half_day', 'Half Day'),
        ('leave', 'On Leave'),
        ('holiday', 'Holiday'),
        ('weekend', 'Weekend'),
    ]

    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')

    # Time tracking
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    break_start = models.TimeField(null=True, blank=True)
    break_end = models.TimeField(null=True, blank=True)

    # Calculated fields
    total_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    regular_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    break_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Location and device tracking
    location = models.CharField(max_length=255, blank=True)
    device_info = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    # Approval
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    approval_date = models.DateTimeField(null=True, blank=True)

    # Additional information
    notes = models.TextField(blank=True)
    is_night_shift = models.BooleanField(default=False)

    # System fields
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def calculate_hours(self):
        """Calculate work hours automatically"""
        if self.check_in and self.check_out:
            # Handle next day checkout for night shifts
            check_in_datetime = datetime.combine(self.date, self.check_in)

            if self.is_night_shift and self.check_out < self.check_in:
                # Next day checkout
                check_out_datetime = datetime.combine(self.date + timedelta(days=1), self.check_out)
            else:
                check_out_datetime = datetime.combine(self.date, self.check_out)

            # Calculate total time worked
            total_time = check_out_datetime - check_in_datetime
            total_minutes = total_time.total_seconds() / 60

            # Subtract break time
            break_minutes = 0
            if self.break_start and self.break_end:
                if self.break_end > self.break_start:
                    break_time = datetime.combine(self.date, self.break_end) - datetime.combine(self.date, self.break_start)
                    break_minutes = break_time.total_seconds() / 60

            self.break_hours = Decimal(str(break_minutes / 60))
            worked_minutes = total_minutes - break_minutes
            self.total_hours = Decimal(str(worked_minutes / 60))

            # Calculate regular vs overtime (assuming 8 hours is regular)
            regular_limit = 8
            if self.total_hours <= regular_limit:
                self.regular_hours = self.total_hours
                self.overtime_hours = Decimal('0')
            else:
                self.regular_hours = Decimal(str(regular_limit))
                self.overtime_hours = self.total_hours - self.regular_hours

            self.save(update_fields=['total_hours', 'regular_hours', 'overtime_hours', 'break_hours'])

    def approve_attendance(self, approved_by_user):
        """Approve attendance record"""
        self.is_approved = True
        self.approved_by = approved_by_user
        self.approval_date = timezone.now()
        self.save()

    def __str__(self):
        return f"{self.staff.full_name} - {self.date} ({self.get_status_display()})"

    class Meta:
        db_table = 'staff_attendance'
        unique_together = ['staff', 'date']
        ordering = ['-date', 'staff__full_name']

class PayrollRecord(models.Model):
    """Monthly payroll processing"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('calculated', 'Calculated'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
        ('upi', 'UPI'),
    ]

    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='payroll_records')
    month = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    year = models.IntegerField()

    # Pay period
    payroll_period_start = models.DateField()
    payroll_period_end = models.DateField()

    # Basic salary components
    base_salary = models.DecimalField(max_digits=10, decimal_places=2)

    # Hours and rates
    regular_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    overtime_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    night_shift_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    regular_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    overtime_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    night_shift_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Allowances
    house_rent_allowance = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    transport_allowance = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    medical_allowance = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    special_allowance = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    performance_bonus = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    # Deductions
    provident_fund = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    professional_tax = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    income_tax = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    advance_deduction = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    loan_deduction = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    # Calculated totals
    gross_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Processing information
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    calculated_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='calculated_payrolls')
    calculation_date = models.DateTimeField(null=True, blank=True)

    approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_payrolls')
    approval_date = models.DateTimeField(null=True, blank=True)

    paid_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='paid_payrolls')
    payment_date = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)

    # System fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Additional information
    notes = models.TextField(blank=True)

    def calculate_payroll(self):
        """Calculate complete payroll"""
        # Get attendance for the period
        attendance_records = AttendanceRecord.objects.filter(
            staff=self.staff,
            date__range=[self.payroll_period_start, self.payroll_period_end],
            status__in=['present', 'late', 'half_day']
        )

        # Calculate hours
        self.regular_hours = sum(record.regular_hours for record in attendance_records)
        self.overtime_hours = sum(record.overtime_hours for record in attendance_records)
        self.night_shift_hours = sum(
            record.total_hours for record in attendance_records if record.is_night_shift
        )

        # Calculate amounts based on employment type
        if self.staff.employment_type in ['hourly', 'part_time'] and self.staff.hourly_rate:
            self.regular_amount = self.regular_hours * self.staff.hourly_rate
            self.overtime_amount = self.overtime_hours * (self.staff.overtime_rate or self.staff.hourly_rate * Decimal('1.5'))
        else:
            # Monthly salary calculation
            working_days = 26  # Standard working days
            present_days = attendance_records.filter(status__in=['present', 'late']).count()
            half_days = attendance_records.filter(status='half_day').count()
            effective_days = present_days + (half_days * 0.5)

            self.regular_amount = (self.base_salary / working_days) * Decimal(str(effective_days))
            self.overtime_amount = self.overtime_hours * (self.staff.overtime_rate or Decimal('50'))

        # Night shift allowance
        self.night_shift_amount = self.night_shift_hours * self.staff.night_shift_allowance

        # Copy allowances from staff profile
        self.house_rent_allowance = self.staff.house_rent_allowance
        self.transport_allowance = self.staff.transport_allowance
        self.medical_allowance = self.staff.medical_allowance
        self.special_allowance = self.staff.special_allowance

        # Calculate deductions
        self.calculate_deductions()

        # Calculate totals
        self.gross_salary = (
            self.regular_amount + self.overtime_amount + self.night_shift_amount +
            self.house_rent_allowance + self.transport_allowance + 
            self.medical_allowance + self.special_allowance + self.performance_bonus
        )

        self.total_deductions = (
            self.provident_fund + self.professional_tax + self.income_tax +
            self.advance_deduction + self.loan_deduction + self.other_deductions
        )

        self.net_salary = self.gross_salary - self.total_deductions

        self.status = 'calculated'
        self.calculation_date = timezone.now()
        self.save()

    def calculate_deductions(self):
        """Calculate automatic deductions"""
        # PF calculation (12% of basic salary)
        if self.gross_salary > 15000:  # PF limit
            self.provident_fund = min(self.base_salary * Decimal('0.12'), Decimal('1800'))  # Max PF

        # Professional tax (state-specific, this is a sample)
        if self.gross_salary > 10000:
            self.professional_tax = Decimal('200')

        # Calculate advance payment deductions
        advance_deduction = Decimal('0')
        active_advances = AdvancePayment.objects.filter(
            staff=self.staff,
            status='disbursed',
            is_active=True
        )

        for advance in active_advances:
            if advance.monthly_deduction_amount:
                advance_deduction += advance.monthly_deduction_amount

                # Update advance payment record
                advance.total_deducted += advance.monthly_deduction_amount
                if advance.total_deducted >= advance.amount:
                    advance.is_active = False
                advance.save()

        self.advance_deduction = advance_deduction

    def approve_payroll(self, approved_by_user):
        """Approve payroll record"""
        if self.status == 'calculated':
            self.status = 'approved'
            self.approved_by = approved_by_user
            self.approval_date = timezone.now()
            self.save()
            return True
        return False

    def mark_as_paid(self, paid_by_user, payment_reference=""):
        """Mark payroll as paid"""
        if self.status == 'approved':
            self.status = 'paid'
            self.paid_by = paid_by_user
            self.payment_date = timezone.now()
            self.payment_reference = payment_reference
            self.save()
            return True
        return False

    @property
    def can_be_approved(self):
        return self.status == 'calculated'

    @property
    def can_be_paid(self):
        return self.status == 'approved'

    def __str__(self):
        return f"{self.staff.full_name} - {self.month:02d}/{self.year} - {self.get_status_display()}"

    class Meta:
        db_table = 'staff_payroll'
        unique_together = ['staff', 'month', 'year']
        ordering = ['-year', '-month', 'staff__full_name']

class AdvancePayment(models.Model):
    """Employee advance payment management"""
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('disbursed', 'Disbursed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    URGENCY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='advance_payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    urgency_level = models.CharField(max_length=10, choices=URGENCY_CHOICES, default='medium')

    request_date = models.DateField(auto_now_add=True)
    required_date = models.DateField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Approval information
    approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_advances')
    approval_date = models.DateTimeField(null=True, blank=True)
    approval_notes = models.TextField(blank=True)

    # Disbursement information
    disbursed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='disbursed_advances')
    disbursement_date = models.DateTimeField(null=True, blank=True)
    disbursement_method = models.CharField(max_length=50, blank=True)

    # Repayment tracking
    deduction_months = models.IntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(12)])
    monthly_deduction_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    total_deducted = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    remaining_balance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=False)

    # System fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.monthly_deduction_amount:
            self.monthly_deduction_amount = self.amount / self.deduction_months

        self.remaining_balance = self.amount - self.total_deducted
        super().save(*args, **kwargs)

    def approve_advance(self, approved_by_user, notes=""):
        """Approve advance payment"""
        if self.status == 'pending':
            self.status = 'approved'
            self.approved_by = approved_by_user
            self.approval_date = timezone.now()
            self.approval_notes = notes
            self.save()
            return True
        return False

    def disburse_advance(self, disbursed_by_user, method="bank_transfer"):
        """Disburse approved advance"""
        if self.status == 'approved':
            self.status = 'disbursed'
            self.disbursed_by = disbursed_by_user
            self.disbursement_date = timezone.now()
            self.disbursement_method = method
            self.is_active = True
            self.save()
            return True
        return False

    def __str__(self):
        return f"{self.staff.full_name} - ₹{self.amount} ({self.get_status_display()})"

    class Meta:
        db_table = 'staff_advance_payments'
        ordering = ['-created_at']

class LeaveRequest(models.Model):
    """Employee leave request management"""
    LEAVE_TYPE_CHOICES = [
        ('casual', 'Casual Leave'),
        ('sick', 'Sick Leave'),
        ('annual', 'Annual Leave'),
        ('maternity', 'Maternity Leave'),
        ('paternity', 'Paternity Leave'),
        ('emergency', 'Emergency Leave'),
        ('unpaid', 'Unpaid Leave'),
        ('compensatory', 'Compensatory Leave'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.IntegerField(null=True, blank=True)

    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Application details
    applied_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='applied_leaves')
    application_date = models.DateTimeField(auto_now_add=True)

    # Approval information
    approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_leaves')
    approval_date = models.DateTimeField(null=True, blank=True)
    approval_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)

    # Emergency contact during leave
    emergency_contact = models.CharField(max_length=100, blank=True)
    emergency_phone = models.CharField(max_length=15, blank=True)

    # System fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.start_date and self.end_date:
            self.total_days = (self.end_date - self.start_date).days + 1
        super().save(*args, **kwargs)

    def approve_leave(self, approved_by_user, notes=""):
        """Approve leave request"""
        if self.status == 'pending':
            self.status = 'approved'
            self.approved_by = approved_by_user
            self.approval_date = timezone.now()
            self.approval_notes = notes
            self.save()

            # Create attendance records for leave period
            current_date = self.start_date
            while current_date <= self.end_date:
                AttendanceRecord.objects.update_or_create(
                    staff=self.staff,
                    date=current_date,
                    defaults={
                        'status': 'leave',
                        'is_approved': True,
                        'approved_by': approved_by_user,
                        'approval_date': timezone.now(),
                        'notes': f"{self.get_leave_type_display()} - {self.reason[:100]}"
                    }
                )
                current_date += timedelta(days=1)

            return True
        return False

    def reject_leave(self, rejected_by_user, reason=""):
        """Reject leave request"""
        if self.status == 'pending':
            self.status = 'rejected'
            self.approved_by = rejected_by_user
            self.approval_date = timezone.now()
            self.rejection_reason = reason
            self.save()
            return True
        return False

    def __str__(self):
        return f"{self.staff.full_name} - {self.get_leave_type_display()} ({self.start_date} to {self.end_date})"

    class Meta:
        db_table = 'staff_leave_requests'
        ordering = ['-created_at']

class StaffPerformance(models.Model):
    """Staff performance evaluation"""
    REVIEW_PERIOD_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('half_yearly', 'Half Yearly'),
        ('annual', 'Annual'),
    ]

    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='performance_reviews')
    review_period = models.CharField(max_length=20, choices=REVIEW_PERIOD_CHOICES)
    review_start_date = models.DateField()
    review_end_date = models.DateField()
    review_date = models.DateField(auto_now_add=True)

    # Performance metrics (1-5 scale)
    punctuality = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], default=3)
    quality_of_work = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], default=3)
    productivity = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], default=3)
    teamwork = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], default=3)
    communication = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], default=3)
    initiative = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], default=3)
    customer_service = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], default=3)

    # Calculated overall rating
    overall_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)

    # Comments and feedback
    strengths = models.TextField(blank=True)
    areas_for_improvement = models.TextField(blank=True)
    goals_for_next_period = models.TextField(blank=True)
    additional_comments = models.TextField(blank=True)

    # Employee self-assessment
    employee_self_assessment = models.TextField(blank=True)
    employee_goals = models.TextField(blank=True)

    # Review completion
    is_final = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)

    # System fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def calculate_overall_rating(self):
        """Calculate overall performance rating"""
        ratings = [
            self.punctuality,
            self.quality_of_work,
            self.productivity,
            self.teamwork,
            self.communication,
            self.initiative,
            self.customer_service,
        ]
        self.overall_rating = Decimal(str(sum(ratings) / len(ratings)))
        self.save(update_fields=['overall_rating'])

    def __str__(self):
        return f"{self.staff.full_name} - {self.get_review_period_display()} Review ({self.review_date})"

    class Meta:
        db_table = 'staff_performance'
        ordering = ['-review_date']

