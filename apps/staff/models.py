# apps/staff/models.py
from django.db import models
from apps.users.models import CustomUser
from decimal import Decimal
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.db.models import Sum

class StaffProfile(models.Model):
    POSITION_CHOICES = (
        ('waiter', 'Waiter'),
        ('cook', 'Cook'),
        ('chef', 'Chef'),
        ('kitchen_helper', 'Kitchen Helper'),
        ('manager', 'Manager'),
        ('cleaner', 'Cleaner'),
        ('receptionist', 'Receptionist'),
        ('accountant', 'Accountant'),
        ('security', 'Security Guard'),
    )

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='staff_profile')
    employee_id = models.CharField(max_length=20, unique=True)
    phone = models.CharField(max_length=15)
    position = models.CharField(max_length=20, choices=POSITION_CHOICES)
    salary_per_day = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    joining_date = models.DateField()
    is_active = models.BooleanField(default=True)
    address = models.TextField(blank=True)
    emergency_contact = models.CharField(max_length=15, blank=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    bank_account_number = models.CharField(max_length=20, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    aadhar_number = models.CharField(max_length=12, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.employee_id}"

    @property
    def total_worked_days(self):
        """Total days worked (present status)"""
        return self.attendance_records.filter(status='present').count()
    
    @property
    def total_earned(self):
        """Total salary earned based on attendance"""
        return self.attendance_records.aggregate(
            total=Sum('salary_amount')
        )['total'] or Decimal('0.00')
    
    @property
    def total_paid(self):
        """Total amount paid to staff"""
        return self.payment_records.aggregate(
            total=Sum('amount_paid')
        )['total'] or Decimal('0.00')
    
    @property
    def total_advances(self):
        """Total advance payments (pending adjustment)"""
        return self.advance_payments.filter(
            status='pending'
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

    @property
    def pending_salary(self):
        """Salary pending to be paid"""
        return self.total_earned - self.total_paid - self.total_advances

    @property
    def current_month_attendance(self):
        """Current month attendance count"""
        current_month = timezone.now().replace(day=1)
        return self.attendance_records.filter(
            date__gte=current_month,
            status='present'
        ).count()

    class Meta:
        db_table = 'staff_profile'
        verbose_name = 'Staff Profile'
        verbose_name_plural = 'Staff Profiles'

class Attendance(models.Model):
    STATUS_CHOICES = (
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('half_day', 'Half Day'),
        ('overtime', 'Overtime'),
        ('leave', 'Leave'),
        ('holiday', 'Holiday'),
    )

    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    check_in_time = models.TimeField(null=True, blank=True)
    check_out_time = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')
    total_hours = models.DecimalField(max_digits=5, decimal_places=2, default=8, validators=[MinValueValidator(0)])
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    salary_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    marked_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='marked_attendance')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['staff', 'date']
        db_table = 'staff_attendance'
        ordering = ['-date']
        verbose_name = 'Attendance Record'
        verbose_name_plural = 'Attendance Records'

    def save(self, *args, **kwargs):
        # Calculate salary based on status and hours
        if self.status == 'present':
            self.salary_amount = self.staff.salary_per_day
        elif self.status == 'half_day':
            self.salary_amount = self.staff.salary_per_day / 2
        elif self.status == 'overtime':
            # Regular day + overtime at 1.5x rate
            overtime_rate = self.staff.salary_per_day * Decimal('1.5') / 8
            self.salary_amount = self.staff.salary_per_day + (self.overtime_hours * overtime_rate)
        elif self.status == 'holiday':
            # Holiday pay (usually full day)
            self.salary_amount = self.staff.salary_per_day
        else:
            # absent, leave
            self.salary_amount = Decimal('0.00')
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.staff.employee_id} - {self.date} - {self.status}"

class PaymentRecord(models.Model):
    PAYMENT_TYPES = (
        ('salary', 'Regular Salary'),
        ('advance', 'Advance Payment'),
        ('bonus', 'Bonus'),
        ('overtime', 'Overtime Payment'),
        ('adjustment', 'Adjustment'),
        ('deduction', 'Deduction'),
    )

    PAYMENT_METHODS = (
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('upi', 'UPI'),
        ('cheque', 'Cheque'),
    )

    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='payment_records')
    payment_date = models.DateField(default=timezone.now)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash')
    reference_number = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    from_date = models.DateField(null=True, blank=True)  # For salary periods
    to_date = models.DateField(null=True, blank=True)
    paid_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='payments_made')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.staff.employee_id} - ₹{self.amount_paid} - {self.payment_date}"

    class Meta:
        db_table = 'staff_payment_record'
        ordering = ['-payment_date']
        verbose_name = 'Payment Record'
        verbose_name_plural = 'Payment Records'

class AdvancePayment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Adjustment'),
        ('adjusting', 'Being Adjusted'),
        ('adjusted', 'Fully Adjusted'),
        ('written_off', 'Written Off')
    )

    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='advance_payments')
    advance_date = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    reason = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    adjustment_start_date = models.DateField(null=True, blank=True)
    adjustment_amount_per_day = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_adjusted = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='advances_approved')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def remaining_amount(self):
        """Remaining advance amount to be adjusted"""
        return self.amount - self.total_adjusted

    @property
    def adjustment_progress(self):
        """Adjustment progress percentage"""
        if self.amount > 0:
            return (self.total_adjusted / self.amount) * 100
        return 0

    def __str__(self):
        return f"{self.staff.employee_id} - Advance ₹{self.amount} - {self.status}"

    class Meta:
        db_table = 'staff_advance_payment'
        ordering = ['-advance_date']
        verbose_name = 'Advance Payment'
        verbose_name_plural = 'Advance Payments'

class StaffShift(models.Model):
    SHIFT_CHOICES = (
        ('morning', 'Morning Shift'),
        ('afternoon', 'Afternoon Shift'),
        ('evening', 'Evening Shift'),
        ('night', 'Night Shift'),
        ('full_day', 'Full Day'),
    )

    name = models.CharField(max_length=50, unique=True)
    shift_type = models.CharField(max_length=20, choices=SHIFT_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    break_duration = models.PositiveIntegerField(default=30)  # minutes
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.start_time} - {self.end_time})"

    class Meta:
        db_table = 'staff_shift'
        verbose_name = 'Staff Shift'
        verbose_name_plural = 'Staff Shifts'

class StaffShiftAssignment(models.Model):
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='shift_assignments')
    shift = models.ForeignKey(StaffShift, on_delete=models.CASCADE)
    assigned_date = models.DateField()
    is_active = models.BooleanField(default=True)
    assigned_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['staff', 'assigned_date']
        db_table = 'staff_shift_assignment'
        ordering = ['-assigned_date']
        verbose_name = 'Shift Assignment'
        verbose_name_plural = 'Shift Assignments'
