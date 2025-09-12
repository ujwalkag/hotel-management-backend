from django.db import models
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, date

class Designation(models.Model):
    name = models.CharField(max_length=100, unique=True)
    daily_wage = models.DecimalField(max_digits=8, decimal_places=2)
    monthly_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class Employee(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField()
    aadhar_number = models.CharField(max_length=12, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    designation = models.ForeignKey(Designation, on_delete=models.CASCADE)
    date_of_joining = models.DateField()
    monthly_salary = models.DecimalField(max_digits=10, decimal_places=2)  # Individual monthly salary
    daily_wage = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)  # Override designation daily wage if needed
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # If daily_wage is not set, use designation's daily_wage
        if not self.daily_wage:
            self.daily_wage = self.designation.daily_wage
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} - {self.designation.name}"
    
    def get_effective_daily_wage(self):
        """Get the effective daily wage (employee specific or designation default)"""
        return self.daily_wage or self.designation.daily_wage
    
    def get_total_pay(self):
        """Calculate total pay from date of joining based on attendance"""
        total_present_days = self.attendance_set.filter(is_present=True).count()
        return total_present_days * self.get_effective_daily_wage()
    
    def get_monthly_present(self, year, month):
        """Get present days for a specific month"""
        return self.attendance_set.filter(
            date__year=year,
            date__month=month,
            is_present=True
        ).count()
    
    def get_monthly_absent(self, year, month):
        """Get absent days for a specific month"""
        return self.attendance_set.filter(
            date__year=year,
            date__month=month,
            is_present=False
        ).count()
    
    def get_monthly_pay_by_attendance(self, year, month):
        """Calculate monthly pay based on attendance (daily wage * present days)"""
        present_days = self.get_monthly_present(year, month)
        return present_days * self.get_effective_daily_wage()
    
    def get_fixed_monthly_salary(self):
        """Get the fixed monthly salary"""
        return self.monthly_salary
    
    def get_total_monthly_earnings(self, year, month):
        """Get total monthly earnings (can be overridden for different payment models)"""
        # For now, we'll use attendance-based calculation
        # This can be modified to use fixed monthly salary if needed
        return self.get_monthly_pay_by_attendance(year, month)

class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField()
    is_present = models.BooleanField(default=False)
    remarks = models.TextField(blank=True, null=True)
    marked_by = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('employee', 'date')
    
    def __str__(self):
        return f"{self.employee.name} - {self.date} - {'Present' if self.is_present else 'Absent'}"

class MonthlyPayment(models.Model):
    """Track monthly payments made to employees"""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    year = models.IntegerField()
    month = models.IntegerField()  # 1-12
    base_salary = models.DecimalField(max_digits=10, decimal_places=2)  # Fixed monthly salary
    attendance_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Extra for perfect attendance
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Any deductions
    total_paid = models.DecimalField(max_digits=10, decimal_places=2)  # Actual amount paid
    payment_date = models.DateField()
    present_days = models.IntegerField(default=0)
    working_days = models.IntegerField(default=30)  # Total working days in month
    remarks = models.TextField(blank=True, null=True)
    paid_by = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('employee', 'year', 'month')
    
    def __str__(self):
        return f"{self.employee.name} - {self.year}/{self.month:02d} - ₹{self.total_paid}"

