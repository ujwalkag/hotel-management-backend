from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.users.models import CustomUser
from datetime import datetime, timedelta

class StaffProfile(models.Model):
    """Staff Profile separate from User authentication"""
    DEPARTMENT_CHOICES = [
        ('kitchen', 'Kitchen'),
        ('service', 'Service'),
        ('management', 'Management'),
        ('housekeeping', 'Housekeeping'),
        ('reception', 'Reception'),
        ('billing', 'Billing'),
    ]

    EMPLOYMENT_TYPE_CHOICES = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('casual', 'Casual'),
    ]

    # Basic Information
    name = models.CharField(max_length=100)
    employee_id = models.CharField(max_length=20, unique=True)
    department = models.CharField(max_length=20, choices=DEPARTMENT_CHOICES)
    position = models.CharField(max_length=50)
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES)

    # Salary Information
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    # Personal Information
    hire_date = models.DateField()
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    address = models.TextField()
    emergency_contact = models.CharField(max_length=100, blank=True)
    emergency_phone = models.CharField(max_length=15, blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'staff_profiles'
        verbose_name = 'Staff Profile'
        verbose_name_plural = 'Staff Profiles'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.employee_id}"

class Attendance(models.Model):
    """Daily attendance tracking"""
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('half_day', 'Half Day'),
        ('late', 'Late'),
        ('holiday', 'Holiday'),
        ('sick_leave', 'Sick Leave'),
        ('vacation', 'Vacation'),
    ]

    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    break_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    total_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    overtime_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')
    notes = models.TextField(blank=True)
    approved_by = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'staff_attendance'
        unique_together = ['staff', 'date']
        verbose_name = 'Attendance Record'
        verbose_name_plural = 'Attendance Records'
        ordering = ['-date']

    def __str__(self):
        return f"{self.staff.name} - {self.date} - {self.status}"

    def calculate_hours(self):
        """Calculate working hours automatically"""
        if self.check_in and self.check_out:
            from datetime import datetime, timedelta
            check_in_dt = datetime.combine(self.date, self.check_in)
            check_out_dt = datetime.combine(self.date, self.check_out)

            if check_out_dt < check_in_dt:
                check_out_dt += timedelta(days=1)

            total_time = check_out_dt - check_in_dt
            self.total_hours = max(0, (total_time.total_seconds() / 3600) - float(self.break_hours))

            # Calculate overtime (more than 8 hours)
            regular_hours = 8
            if self.total_hours > regular_hours:
                self.overtime_hours = self.total_hours - regular_hours
            else:
                self.overtime_hours = 0

            self.save()

class Payroll(models.Model):
    """Monthly payroll records"""
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='payrolls')
    month = models.IntegerField()
    year = models.IntegerField()
    days_worked = models.IntegerField(default=0)
    total_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    overtime_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    basic_amount = models.DecimalField(max_digits=10, decimal_places=2)
    overtime_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_deducted = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=[
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('check', 'Check'),
    ], default='bank_transfer')
    is_paid = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'staff_payroll'
        unique_together = ['staff', 'month', 'year']
        verbose_name = 'Payroll Record'
        verbose_name_plural = 'Payroll Records'
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{self.staff.name} - {self.month}/{self.year} - ${self.net_amount}"

    def calculate_payroll(self):
        """Calculate payroll based on attendance"""
        from django.db.models import Sum

        # Get attendance for the month
        attendances = Attendance.objects.filter(
            staff=self.staff,
            date__month=self.month,
            date__year=self.year,
            status__in=['present', 'half_day', 'late']
        )

        self.days_worked = attendances.count()
        self.total_hours = attendances.aggregate(Sum('total_hours'))['total_hours__sum'] or 0
        self.overtime_hours = attendances.aggregate(Sum('overtime_hours'))['overtime_hours__sum'] or 0

        # Calculate amounts
        if self.staff.employment_type in ['full_time', 'part_time']:
            self.basic_amount = self.staff.basic_salary
        else:
            hourly_rate = self.staff.hourly_rate or 0
            self.basic_amount = float(self.total_hours) * float(hourly_rate)

        # Overtime calculation
        if self.overtime_hours > 0 and self.staff.hourly_rate:
            overtime_rate = float(self.staff.hourly_rate) * 1.5
            self.overtime_amount = float(self.overtime_hours) * overtime_rate

        # Calculate net amount
        gross_amount = self.basic_amount + self.overtime_amount + self.bonus + self.allowances
        self.net_amount = gross_amount - self.deductions - self.tax_deducted

        self.save()
