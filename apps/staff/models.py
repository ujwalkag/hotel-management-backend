
# apps/staff/models.py - Complete Staff Management Models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from apps.users.models import CustomUser
from django.utils import timezone
from decimal import Decimal
import uuid

class StaffProfile(models.Model):
    DEPARTMENT_CHOICES = (
        ('kitchen', 'Kitchen'),
        ('service', 'Service'),
        ('housekeeping', 'Housekeeping'),
        ('management', 'Management'),
        ('billing', 'Billing'),
    )

    EMPLOYMENT_STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('terminated', 'Terminated'),
        ('on_leave', 'On Leave'),
    )

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='staff_profile')
    employee_id = models.CharField(max_length=20, unique=True, blank=True)
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15)
    address = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    hire_date = models.DateField(default=timezone.now)
    department = models.CharField(max_length=20, choices=DEPARTMENT_CHOICES)
    position = models.CharField(max_length=100)
    base_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    employment_status = models.CharField(max_length=20, choices=EMPLOYMENT_STATUS_CHOICES, default='active')
    emergency_contact_name = models.CharField(max_length=255, blank=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.employee_id:
            self.employee_id = f"EMP{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} ({self.employee_id})"

    @property
    def current_month_attendance(self):
        now = timezone.now()
        return self.attendance_records.filter(
            date__year=now.year,
            date__month=now.month
        ).count()

    class Meta:
        db_table = 'staff_profile'
        verbose_name = 'Staff Profile'
        verbose_name_plural = 'Staff Profiles'

class AttendanceRecord(models.Model):
    STATUS_CHOICES = (
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('half_day', 'Half Day'),
        ('late', 'Late'),
        ('on_leave', 'On Leave'),
    )

    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    check_in_time = models.TimeField(null=True, blank=True)
    check_out_time = models.TimeField(null=True, blank=True)
    break_duration = models.DurationField(default=timezone.timedelta(minutes=0))
    total_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def calculate_hours(self):
        if self.check_in_time and self.check_out_time:
            from datetime import datetime, timedelta
            check_in = datetime.combine(self.date, self.check_in_time)
            check_out = datetime.combine(self.date, self.check_out_time)

            if check_out < check_in:
                check_out += timedelta(days=1)

            total_time = check_out - check_in
            total_time -= self.break_duration

            self.total_hours = Decimal(str(total_time.total_seconds() / 3600))

            if self.total_hours > 8:
                self.overtime_hours = self.total_hours - 8
            else:
                self.overtime_hours = 0

            self.save(update_fields=['total_hours', 'overtime_hours'])

    def __str__(self):
        return f"{self.staff.full_name} - {self.date} - {self.status}"

    class Meta:
        db_table = 'staff_attendance'
        unique_together = ['staff', 'date']
        ordering = ['-date']

class AdvancePayment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
    )

    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='advance_payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    request_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    approved_date = models.DateTimeField(null=True, blank=True)
    paid_date = models.DateTimeField(null=True, blank=True)
    remaining_amount = models.DecimalField(max_digits=10, decimal_places=2)
    monthly_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if not self.pk:
            self.remaining_amount = self.amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.staff.full_name} - ₹{self.amount} - {self.status}"

    class Meta:
        db_table = 'staff_advance_payment'
        ordering = ['-request_date']

