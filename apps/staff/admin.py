# apps/staff/admin.py - EXACT MATCH TO YOUR MODELS
from django.contrib import admin
from django.utils import timezone
from .models import StaffProfile, AttendanceRecord, AdvancePayment

@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'full_name', 'user', 'department', 'position', 'employment_status', 'base_salary']
    list_filter = ['department', 'employment_status', 'position', 'hire_date']
    search_fields = ['employee_id', 'full_name', 'user__email', 'phone']
    readonly_fields = ['employee_id', 'current_month_attendance', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'employee_id', 'full_name', 'phone')
        }),
        ('Employment Details', {
            'fields': ('department', 'position', 'employment_status', 'hire_date')
        }),
        ('Salary Information', {
            'fields': ('base_salary', 'hourly_rate')
        }),
        ('Contact Information', {
            'fields': ('address', 'emergency_contact_name', 'emergency_contact_phone')
        }),
        ('Personal Information', {
            'fields': ('date_of_birth',)
        }),
        ('Summary', {
            'fields': ('current_month_attendance',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

    actions = ['activate_staff', 'deactivate_staff']

    def activate_staff(self, request, queryset):
        updated = queryset.update(employment_status='active')
        self.message_user(request, f'{updated} staff members activated.')
    activate_staff.short_description = "Activate selected staff"

    def deactivate_staff(self, request, queryset):
        updated = queryset.update(employment_status='inactive')
        self.message_user(request, f'{updated} staff members deactivated.')
    deactivate_staff.short_description = "Deactivate selected staff"

@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ['staff', 'employee_id', 'date', 'status', 'check_in_time', 'check_out_time', 'total_hours', 'created_by']
    list_filter = ['status', 'date', 'staff__department']
    search_fields = ['staff__employee_id', 'staff__full_name', 'staff__user__email']
    date_hierarchy = 'date'
    readonly_fields = ['total_hours', 'overtime_hours', 'created_at']

    fieldsets = (
        ('Attendance Details', {
            'fields': ('staff', 'date', 'status')
        }),
        ('Timing', {
            'fields': ('check_in_time', 'check_out_time', 'break_duration')
        }),
        ('Calculation', {
            'fields': ('total_hours', 'overtime_hours'),
            'classes': ('collapse',)
        }),
        ('Additional Info', {
            'fields': ('notes', 'created_by'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def employee_id(self, obj):
        return obj.staff.employee_id
    employee_id.short_description = 'Employee ID'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('staff__user', 'created_by')

    actions = ['mark_as_present', 'mark_as_absent']

    def mark_as_present(self, request, queryset):
        updated = queryset.update(status='present', created_by=request.user)
        self.message_user(request, f'{updated} records marked as present.')
    mark_as_present.short_description = "Mark selected as present"

    def mark_as_absent(self, request, queryset):
        updated = queryset.update(status='absent', created_by=request.user)
        self.message_user(request, f'{updated} records marked as absent.')
    mark_as_absent.short_description = "Mark selected as absent"

@admin.register(AdvancePayment)
class AdvancePaymentAdmin(admin.ModelAdmin):
    list_display = ['staff', 'employee_id', 'request_date', 'amount', 'status', 'remaining_amount', 'approved_by']
    list_filter = ['status', 'request_date', 'staff__department']
    search_fields = ['staff__employee_id', 'staff__full_name', 'staff__user__email', 'reason']
    readonly_fields = ['remaining_amount', 'created_at', 'updated_at']

    fieldsets = (
        ('Advance Information', {
            'fields': ('staff', 'request_date', 'amount', 'reason', 'status')
        }),
        ('Adjustment Details', {
            'fields': ('monthly_deduction', 'remaining_amount')
        }),
        ('Approval Details', {
            'fields': ('approved_by', 'approved_date', 'paid_date')
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def employee_id(self, obj):
        return obj.staff.employee_id
    employee_id.short_description = 'Employee ID'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('staff__user', 'approved_by')

    actions = ['approve_advances', 'reject_advances']

    def approve_advances(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='approved',
            approved_by=request.user,
            approved_date=timezone.now()
        )
        self.message_user(request, f'{updated} advances approved.')
    approve_advances.short_description = "Approve selected advances"

    def reject_advances(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='rejected',
            approved_by=request.user,
            approved_date=timezone.now()
        )
        self.message_user(request, f'{updated} advances rejected.')
    reject_advances.short_description = "Reject selected advances"
