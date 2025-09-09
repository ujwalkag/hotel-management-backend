# apps/staff/admin.py - COMPLETE AND CORRECT STAFF ADMIN

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    StaffDepartment, 
    StaffEmployee, 
    StaffAttendance, 
    StaffPayroll, 
    StaffAdvancePayment
)

@admin.register(StaffDepartment)
class StaffDepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'head_of_department', 'employee_count', 'budget_allocation', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'head_of_department']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Department Information', {
            'fields': ('name', 'description', 'head_of_department')
        }),
        ('Budget & Status', {
            'fields': ('budget_allocation', 'is_active')
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def employee_count(self, obj):
        count = obj.staffemployee_set.filter(is_active=True).count()
        if count > 0:
            url = reverse('admin:staff_staffemployee_changelist') + f'?department__id={obj.id}'
            return format_html('<a href="{}">{} employees</a>', url, count)
        return '0 employees'
    employee_count.short_description = 'Active Employees'

@admin.register(StaffEmployee)
class StaffEmployeeAdmin(admin.ModelAdmin):
    list_display = [
        'employee_id', 'full_name', 'department', 'position', 
        'employment_status', 'base_salary', 'hire_date', 'is_active'
    ]
    list_filter = [
        'employment_status', 'employment_type', 'department', 
        'shift_type', 'is_active', 'hire_date'
    ]
    search_fields = ['employee_id', 'full_name', 'email', 'phone']
    readonly_fields = ['employee_id', 'age', 'years_of_service', 'current_monthly_salary', 'created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('employee_id', 'full_name', 'email', 'phone', 'date_of_birth')
        }),
        ('Address', {
            'fields': ('address', 'city', 'state', 'pincode')
        }),
        ('Employment Details', {
            'fields': (
                'department', 'position', 'employment_status', 'employment_type', 
                'shift_type', 'hire_date', 'probation_end_date', 'termination_date'
            )
        }),
        ('Salary Information', {
            'fields': (
                'base_salary', 'hourly_rate', 'overtime_rate',
                'night_shift_allowance', 'weekend_allowance'
            )
        }),
        ('Monthly Allowances', {
            'fields': ('house_rent_allowance', 'transport_allowance', 'medical_allowance')
        }),
        ('Bank Details', {
            'fields': ('bank_name', 'account_number', 'ifsc_code'),
            'classes': ('collapse',)
        }),
        ('System User Link', {
            'fields': ('system_user',),
            'description': 'Link to system user account if employee needs app access'
        }),
        ('Calculated Fields', {
            'fields': ('age', 'years_of_service', 'current_monthly_salary'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('is_active', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(self.readonly_fields)
        if obj:  # editing an existing object
            readonly_fields.append('employee_id')
        return readonly_fields

    def save_model(self, request, obj, form, change):
        if not change:  # creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(StaffAttendance)
class StaffAttendanceAdmin(admin.ModelAdmin):
    list_display = [
        'employee', 'date', 'status', 'check_in_time', 'check_out_time', 
        'total_hours', 'is_approved'
    ]
    list_filter = [
        'status', 'date', 'is_approved', 'is_night_shift', 
        'is_weekend', 'is_holiday', 'employee__department'
    ]
    search_fields = ['employee__full_name', 'employee__employee_id']
    readonly_fields = [
        'total_hours', 'regular_hours', 'overtime_hours', 'break_hours',
        'session_duration_minutes', 'created_at', 'modified_at'
    ]
    date_hierarchy = 'date'

    fieldsets = (
        ('Basic Information', {
            'fields': ('employee', 'date', 'status')
        }),
        ('Time Tracking', {
            'fields': (
                'check_in_time', 'check_out_time', 
                'break_start_time', 'break_end_time'
            )
        }),
        ('Location Information', {
            'fields': ('check_in_location', 'check_out_location', 'ip_address'),
            'classes': ('collapse',)
        }),
        ('Shift Information', {
            'fields': ('is_night_shift', 'is_weekend', 'is_holiday')
        }),
        ('Calculated Hours (Auto-calculated)', {
            'fields': ('total_hours', 'regular_hours', 'overtime_hours', 'break_hours'),
            'classes': ('collapse',)
        }),
        ('Approval', {
            'fields': ('is_approved', 'approved_by', 'approval_date')
        }),
        ('Additional Information', {
            'fields': ('notes', 'device_info'),
            'classes': ('collapse',)
        })
    )

    actions = ['approve_attendance', 'calculate_hours_bulk']

    def approve_attendance(self, request, queryset):
        updated = queryset.update(is_approved=True, approved_by=request.user)
        self.message_user(request, f'{updated} attendance records approved.')
    approve_attendance.short_description = 'Approve selected attendance records'

    def calculate_hours_bulk(self, request, queryset):
        count = 0
        for attendance in queryset:
            attendance.calculate_hours()
            count += 1
        self.message_user(request, f'Calculated hours for {count} attendance records.')
    calculate_hours_bulk.short_description = 'Calculate hours for selected records'

    def session_duration_minutes(self, obj):
        return f"{obj.session_duration_minutes} minutes" if obj.session_duration_minutes else "—"
    session_duration_minutes.short_description = 'Session Duration'

@admin.register(StaffPayroll)
class StaffPayrollAdmin(admin.ModelAdmin):
    list_display = [
        'employee', 'month_year', 'status', 'regular_hours_worked',
        'overtime_hours_worked', 'gross_pay', 'net_pay', 'payment_date'
    ]
    list_filter = [
        'status', 'month', 'year', 'employee__department'
    ]
    search_fields = ['employee__full_name', 'employee__employee_id']
    readonly_fields = [
        'regular_hours_worked', 'overtime_hours_worked', 'night_shift_hours',
        'weekend_hours', 'holiday_hours', 'base_pay', 'overtime_pay',
        'night_shift_pay', 'weekend_pay', 'holiday_pay', 'advance_deduction',
        'gross_pay', 'total_deductions', 'net_pay', 'created_at', 'updated_at'
    ]

    fieldsets = (
        ('Basic Information', {
            'fields': ('employee', 'month', 'year', 'pay_period_start', 'pay_period_end')
        }),
        ('Hours Worked (Auto-calculated)', {
            'fields': (
                'regular_hours_worked', 'overtime_hours_worked', 
                'night_shift_hours', 'weekend_hours', 'holiday_hours'
            ),
            'classes': ('collapse',)
        }),
        ('Earnings (Auto-calculated)', {
            'fields': (
                'base_pay', 'overtime_pay', 'night_shift_pay', 
                'weekend_pay', 'holiday_pay'
            ),
            'classes': ('collapse',)
        }),
        ('Allowances', {
            'fields': ('hra', 'transport_allowance', 'medical_allowance', 'performance_bonus')
        }),
        ('Deductions (Auto-calculated)', {
            'fields': (
                'advance_deduction', 'loan_deduction', 'provident_fund', 
                'professional_tax', 'income_tax', 'other_deductions'
            ),
            'classes': ('collapse',)
        }),
        ('Totals (Auto-calculated)', {
            'fields': ('gross_pay', 'total_deductions', 'net_pay')
        }),
        ('Status & Processing', {
            'fields': (
                'status', 'calculated_by', 'calculation_date',
                'approved_by', 'approval_date'
            )
        }),
        ('Payment Information', {
            'fields': ('payment_date', 'payment_method', 'payment_reference')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        })
    )

    actions = ['calculate_payroll_bulk', 'approve_payroll_bulk']

    def calculate_payroll_bulk(self, request, queryset):
        count = 0
        for payroll in queryset.filter(status='draft'):
            payroll.calculated_by = request.user
            payroll.calculate_payroll()
            count += 1
        self.message_user(request, f'Calculated {count} payroll records.')
    calculate_payroll_bulk.short_description = 'Calculate selected payroll records'

    def approve_payroll_bulk(self, request, queryset):
        updated = queryset.filter(status='calculated').update(
            status='approved', 
            approved_by=request.user
        )
        self.message_user(request, f'Approved {updated} payroll records.')
    approve_payroll_bulk.short_description = 'Approve selected payroll records'

    def month_year(self, obj):
        months = [
            'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
            'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
        ]
        return f"{months[obj.month-1]} {obj.year}"
    month_year.short_description = 'Pay Period'

@admin.register(StaffAdvancePayment)
class StaffAdvancePaymentAdmin(admin.ModelAdmin):
    list_display = [
        'employee', 'amount', 'status', 'urgency_level', 
        'remaining_balance', 'monthly_deduction_amount', 'created_at'
    ]
    list_filter = [
        'status', 'urgency_level', 'created_at', 'employee__department'
    ]
    search_fields = ['employee__full_name', 'employee__employee_id', 'reason']
    readonly_fields = [
        'monthly_deduction_amount', 'remaining_balance', 
        'created_at', 'updated_at'
    ]

    fieldsets = (
        ('Employee & Request', {
            'fields': ('employee', 'amount', 'reason', 'urgency_level', 'required_by_date')
        }),
        ('Repayment Plan', {
            'fields': ('deduction_months', 'monthly_deduction_amount', 'remaining_balance')
        }),
        ('Status & Approval', {
            'fields': ('status', 'approved_by', 'approval_date', 'approval_notes')
        }),
        ('Disbursement', {
            'fields': ('disbursed_by', 'disbursement_date', 'disbursement_method')
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    actions = ['approve_advances', 'disburse_advances']

    def approve_advances(self, request, queryset):
        updated = 0
        for advance in queryset.filter(status='pending'):
            if advance.approve_advance(request.user):
                updated += 1
        self.message_user(request, f'Approved {updated} advance payment requests.')
    approve_advances.short_description = 'Approve selected advance payments'

    def disburse_advances(self, request, queryset):
        updated = 0
        for advance in queryset.filter(status='approved'):
            if advance.disburse_advance(request.user):
                updated += 1
        self.message_user(request, f'Disbursed {updated} advance payments.')
    disburse_advances.short_description = 'Disburse selected advance payments'

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(self.readonly_fields)
        if obj and obj.status in ['approved', 'disbursed', 'completed']:
            # Make most fields readonly for processed advances
            readonly_fields.extend(['employee', 'amount', 'reason', 'deduction_months'])
        return readonly_fields

# Custom admin site configuration
admin.site.site_header = "Hotel Management - Staff Administration"
admin.site.site_title = "Staff Management"
admin.site.index_title = "Staff Management Administration"
