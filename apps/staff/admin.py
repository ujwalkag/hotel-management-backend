# apps/staff/admin.py
from django.contrib import admin
from django.utils import timezone
from .models import StaffProfile, Attendance, PaymentRecord, AdvancePayment

@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'user', 'position', 'salary_per_day', 'joining_date', 'is_active', 'pending_salary']
    list_filter = ['position', 'is_active', 'joining_date']
    search_fields = ['employee_id', 'user__email', 'phone']
    readonly_fields = ['total_worked_days', 'total_earned', 'total_paid', 'pending_salary', 
                      'current_month_attendance', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'employee_id', 'phone', 'position')
        }),
        ('Employment Details', {
            'fields': ('salary_per_day', 'joining_date', 'is_active')
        }),
        ('Contact Information', {
            'fields': ('address', 'emergency_contact', 'emergency_contact_name')
        }),
        ('Banking Details', {
            'fields': ('bank_account_number', 'bank_name', 'aadhar_number')
        }),
        ('Summary', {
            'fields': ('total_worked_days', 'total_earned', 'total_paid', 'pending_salary', 'current_month_attendance'),
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
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} staff members activated.')
    activate_staff.short_description = "Activate selected staff"

    def deactivate_staff(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} staff members deactivated.')
    deactivate_staff.short_description = "Deactivate selected staff"

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['staff', 'employee_id', 'date', 'status', 'check_in_time', 'check_out_time', 'salary_amount', 'marked_by']
    list_filter = ['status', 'date', 'staff__position']
    search_fields = ['staff__employee_id', 'staff__user__email']
    date_hierarchy = 'date'
    readonly_fields = ['salary_amount', 'created_at', 'updated_at']

    fieldsets = (
        ('Attendance Details', {
            'fields': ('staff', 'date', 'status')
        }),
        ('Timing', {
            'fields': ('check_in_time', 'check_out_time', 'total_hours', 'overtime_hours')
        }),
        ('Calculation', {
            'fields': ('salary_amount',),
            'classes': ('collapse',)
        }),
        ('Additional Info', {
            'fields': ('notes', 'marked_by'),
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
        return super().get_queryset(request).select_related('staff__user', 'marked_by')

    actions = ['mark_as_present', 'mark_as_absent']

    def mark_as_present(self, request, queryset):
        updated = queryset.update(status='present', marked_by=request.user)
        self.message_user(request, f'{updated} records marked as present.')
    mark_as_present.short_description = "Mark selected as present"

    def mark_as_absent(self, request, queryset):
        updated = queryset.update(status='absent', marked_by=request.user)
        self.message_user(request, f'{updated} records marked as absent.')
    mark_as_absent.short_description = "Mark selected as absent"

@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = ['staff', 'employee_id', 'payment_date', 'amount_paid', 'payment_type', 'payment_method', 'paid_by']
    list_filter = ['payment_type', 'payment_method', 'payment_date', 'staff__position']
    search_fields = ['staff__employee_id', 'staff__user__email', 'reference_number']
    date_hierarchy = 'payment_date'
    readonly_fields = ['created_at']

    fieldsets = (
        ('Payment Information', {
            'fields': ('staff', 'payment_date', 'amount_paid', 'payment_type', 'payment_method')
        }),
        ('Reference Details', {
            'fields': ('reference_number', 'description')
        }),
        ('Period Details', {
            'fields': ('from_date', 'to_date'),
            'description': 'For salary payments, specify the period'
        }),
        ('Audit Trail', {
            'fields': ('paid_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    def employee_id(self, obj):
        return obj.staff.employee_id
    employee_id.short_description = 'Employee ID'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('staff__user', 'paid_by')

@admin.register(AdvancePayment)
class AdvancePaymentAdmin(admin.ModelAdmin):
    list_display = ['staff', 'employee_id', 'advance_date', 'amount', 'status', 'remaining_amount', 'adjustment_progress', 'approved_by']
    list_filter = ['status', 'advance_date', 'staff__position']
    search_fields = ['staff__employee_id', 'staff__user__email', 'reason']
    readonly_fields = ['remaining_amount', 'adjustment_progress', 'created_at', 'updated_at']

    fieldsets = (
        ('Advance Information', {
            'fields': ('staff', 'advance_date', 'amount', 'reason', 'status')
        }),
        ('Adjustment Details', {
            'fields': ('adjustment_start_date', 'adjustment_amount_per_day', 'total_adjusted', 
                      'remaining_amount', 'adjustment_progress')
        }),
        ('Additional Information', {
            'fields': ('notes', 'approved_by'),
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

    actions = ['approve_advances', 'adjust_advances']

    def approve_advances(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='pending',  # Keep as pending but mark as approved
            approved_by=request.user
        )
        self.message_user(request, f'{updated} advances approved.')
    approve_advances.short_description = "Approve selected advances"

    def adjust_advances(self, request, queryset):
        # This is a complex operation, so just change status
        updated = queryset.filter(status='pending').update(status='adjusting')
        self.message_user(request, f'{updated} advances marked for adjustment.')
    adjust_advances.short_description = "Mark for adjustment"
