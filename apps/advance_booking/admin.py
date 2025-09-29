from django.contrib import admin
from django.utils.html import format_html
from .models import AdvanceBooking, BookingPayment, BookingStatusHistory

class BookingPaymentInline(admin.TabularInline):
    model = BookingPayment
    extra = 0
    readonly_fields = ['payment_date', 'recorded_by']
    fields = ['payment_date', 'amount', 'payment_method', 'transaction_reference', 'notes', 'recorded_by']

class BookingStatusHistoryInline(admin.TabularInline):
    model = BookingStatusHistory
    extra = 0
    readonly_fields = ['changed_at', 'changed_by']
    fields = ['old_status', 'new_status', 'changed_at', 'changed_by', 'reason']

@admin.register(AdvanceBooking)
class AdvanceBookingAdmin(admin.ModelAdmin):
    list_display = [
        'booking_reference', 'customer_name', 'customer_phone', 
        'booking_date', 'booking_time', 'party_size', 
        'total_amount', 'advance_paid', 'remaining_amount',
        'payment_status_display', 'status', 'created_by'
    ]
    
    list_filter = [
        'booking_date', 'status', 'created_at', 'party_size',
        ('booking_date', admin.DateFieldListFilter),
    ]
    
    search_fields = [
        'customer_name', 'customer_phone', 'customer_aadhar', 
        'booking_notes', 'booking_reference'
    ]
    
    readonly_fields = [
        'remaining_amount', 'created_at', 'updated_at', 
        'booking_reference', 'payment_status'
    ]
    
    ordering = ['-created_at']
    date_hierarchy = 'booking_date'
    list_per_page = 25
    
    inlines = [BookingPaymentInline, BookingStatusHistoryInline]
    
    fieldsets = (
        ('Booking Reference', {
            'fields': ('booking_reference',),
            'classes': ('wide',)
        }),
        ('Customer Information', {
            'fields': (
                'customer_name', 'customer_phone', 
                'customer_aadhar', 'customer_address'
            )
        }),
        ('Booking Details', {
            'fields': (
                'booking_date', 'booking_time', 
                'party_size', 'booking_notes', 'status'
            )
        }),
        ('Payment Information', {
            'fields': (
                'total_amount', 'advance_paid', 'remaining_amount', 'payment_status'
            ),
            'description': 'Remaining amount is calculated automatically'
        }),
        ('System Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def payment_status_display(self, obj):
        """Display payment status with color coding"""
        status = obj.payment_status
        colors = {
            'paid': 'green',
            'partial': 'orange', 
            'unpaid': 'red'
        }
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(status, 'black'),
            status.title()
        )
    payment_status_display.short_description = 'Payment Status'
    
    def save_model(self, request, obj, form, change):
        """Save with user tracking"""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('created_by')
    
    actions = ['mark_completed', 'mark_cancelled']
    
    def mark_completed(self, request, queryset):
        """Mark bookings as completed"""
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} booking(s) marked as completed.')
    mark_completed.short_description = 'Mark selected bookings as completed'
    
    def mark_cancelled(self, request, queryset):
        """Mark bookings as cancelled"""
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} booking(s) marked as cancelled.')
    mark_cancelled.short_description = 'Mark selected bookings as cancelled'


@admin.register(BookingPayment)
class BookingPaymentAdmin(admin.ModelAdmin):
    list_display = [
        'booking', 'payment_date', 'amount', 'payment_method',
        'transaction_reference', 'recorded_by'
    ]
    list_filter = ['payment_method', 'payment_date']
    search_fields = ['booking__customer_name', 'transaction_reference']
    readonly_fields = ['payment_date']
    ordering = ['-payment_date']

@admin.register(BookingStatusHistory)
class BookingStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['booking', 'old_status', 'new_status', 'changed_at', 'changed_by']
    list_filter = ['old_status', 'new_status', 'changed_at']
    search_fields = ['booking__customer_name', 'reason']
    readonly_fields = ['changed_at']
    ordering = ['-changed_at']
