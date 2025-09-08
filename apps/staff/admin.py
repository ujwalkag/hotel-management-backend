# apps/tables/admin.py - COMPLETE WORKING VERSION
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    RestaurantTable, 
    MobileOrder, 
    MobileOrderItem, 
    KitchenDisplayOrder, 
    EnhancedBillingSession,
    # Legacy models for backward compatibility
    TableOrder,
    OrderItem,
    KitchenDisplayItem
)

@admin.register(RestaurantTable)
class RestaurantTableAdmin(admin.ModelAdmin):
    list_display = [
        'table_number', 
        'table_name', 
        'capacity', 
        'table_type', 
        'status_badge', 
        'location', 
        'current_session_display',
        'active_orders_count',
        'current_bill_total',
        'is_active'
    ]
    list_filter = ['status', 'table_type', 'location', 'is_active']
    search_fields = ['table_number', 'table_name', 'location']
    readonly_fields = [
        'current_session_id', 
        'session_start_time', 
        'estimated_end_time',
        'last_occupied_at', 
        'last_available_at', 
        'qr_code_data',
        'created_at', 
        'updated_at'
    ]

    fieldsets = (
        ('Basic Information', {
            'fields': ('table_number', 'table_name', 'capacity', 'table_type', 'location')
        }),
        ('Status & Availability', {
            'fields': ('status', 'is_active', 'mobile_order_enabled')
        }),
        ('Current Session', {
            'fields': ('current_session_id', 'session_start_time', 'estimated_end_time'),
            'classes': ('collapse',)
        }),
        ('Analytics', {
            'fields': ('average_dining_duration', 'last_occupied_at', 'last_available_at'),
            'classes': ('collapse',)
        }),
        ('System', {
            'fields': ('qr_code_data', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def status_badge(self, obj):
        colors = {
            'available': 'green',
            'occupied': 'orange',
            'reserved': 'blue',
            'cleaning': 'gray',
            'maintenance': 'red',
            'billing': 'purple'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def current_session_display(self, obj):
        if obj.current_session_id:
            return format_html(
                '<strong>{}</strong><br/><small>Started: {}</small>',
                obj.current_session_id,
                obj.session_start_time.strftime('%H:%M') if obj.session_start_time else 'N/A'
            )
        return 'No active session'
    current_session_display.short_description = 'Current Session'

    actions = ['make_available', 'mark_for_cleaning', 'start_maintenance']

    def make_available(self, request, queryset):
        count = queryset.update(status='available')
        self.message_user(request, f'{count} tables marked as available.')
    make_available.short_description = 'Mark selected tables as available'

    def mark_for_cleaning(self, request, queryset):
        count = queryset.update(status='cleaning')
        self.message_user(request, f'{count} tables marked for cleaning.')
    mark_for_cleaning.short_description = 'Mark selected tables for cleaning'

    def start_maintenance(self, request, queryset):
        count = queryset.update(status='maintenance')
        self.message_user(request, f'{count} tables marked for maintenance.')
    start_maintenance.short_description = 'Mark selected tables for maintenance'

@admin.register(MobileOrder)
class MobileOrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number',
        'table_link',
        'waiter_link',
        'customer_name',
        'customer_count',
        'status_badge',
        'priority_badge',
        'total_amount',
        'created_at',
        'is_in_enhanced_billing'
    ]
    list_filter = [
        'status', 
        'priority', 
        'is_takeaway', 
        'is_in_enhanced_billing',
        'created_at',
        'table__table_type'
    ]
    search_fields = [
        'order_number', 
        'customer_name', 
        'customer_phone', 
        'table__table_number',
        'waiter__email'
    ]
    readonly_fields = [
        'order_number',
        'total_amount',
        'created_at',
        'confirmed_at',
        'kitchen_start_time',
        'ready_time',
        'served_time',
        'completed_at',
        'billed_at',
        'actual_preparation_time'
    ]

    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'table', 'session_id', 'waiter')
        }),
        ('Customer Details', {
            'fields': ('customer_name', 'customer_phone', 'customer_count')
        }),
        ('Order Management', {
            'fields': ('status', 'priority', 'special_instructions', 'is_takeaway')
        }),
        ('Kitchen Integration', {
            'fields': ('kitchen_notes', 'estimated_preparation_time', 'actual_preparation_time'),
            'classes': ('collapse',)
        }),
        ('Billing', {
            'fields': ('total_amount', 'discount_percentage', 'discount_amount', 'is_in_enhanced_billing', 'can_be_billed'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'confirmed_at', 'kitchen_start_time', 'ready_time', 'served_time', 'completed_at', 'billed_at'),
            'classes': ('collapse',)
        })
    )

    def table_link(self, obj):
        url = reverse('admin:tables_restauranttable_change', args=[obj.table.pk])
        return format_html('<a href="{}">{}</a>', url, obj.table.table_number)
    table_link.short_description = 'Table'

    def waiter_link(self, obj):
        if obj.waiter:
            url = reverse('admin:users_customuser_change', args=[obj.waiter.pk])
            return format_html('<a href="{}">{}</a>', url, obj.waiter.email)
        return 'No waiter assigned'
    waiter_link.short_description = 'Waiter'

    def status_badge(self, obj):
        colors = {
            'draft': 'gray',
            'pending': 'orange',
            'confirmed': 'blue',
            'in_progress': 'purple',
            'ready': 'green',
            'served': 'teal',
            'completed': 'darkgreen',
            'billed': 'black',
            'cancelled': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def priority_badge(self, obj):
        colors = {
            'low': 'gray',
            'normal': 'blue',
            'high': 'orange',
            'urgent': 'red'
        }
        color = colors.get(obj.priority, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'

    actions = ['confirm_orders', 'mark_as_ready', 'mark_as_served']

    def confirm_orders(self, request, queryset):
        count = 0
        for order in queryset:
            if order.confirm_order():
                count += 1
        self.message_user(request, f'{count} orders confirmed and sent to kitchen.')
    confirm_orders.short_description = 'Confirm selected orders'

    def mark_as_ready(self, request, queryset):
        count = 0
        for order in queryset:
            if order.status == 'in_progress':
                order.mark_ready()
                count += 1
        self.message_user(request, f'{count} orders marked as ready.')
    mark_as_ready.short_description = 'Mark selected orders as ready'

    def mark_as_served(self, request, queryset):
        count = 0
        for order in queryset:
            if order.status == 'ready':
                order.mark_served()
                count += 1
        self.message_user(request, f'{count} orders marked as served.')
    mark_as_served.short_description = 'Mark selected orders as served'

class MobileOrderItemInline(admin.TabularInline):
    model = MobileOrderItem
    extra = 0
    readonly_fields = ['total_price', 'order_time', 'preparation_started', 'ready_time', 'served_time']
    fields = [
        'menu_item', 
        'quantity', 
        'unit_price', 
        'total_price', 
        'status', 
        'special_instructions',
        'assigned_to_cook'
    ]

# Add inline to MobileOrder admin
MobileOrderAdmin.inlines = [MobileOrderItemInline]

@admin.register(MobileOrderItem)
class MobileOrderItemAdmin(admin.ModelAdmin):
    list_display = [
        'display_name',
        'mobile_order_link',
        'quantity',
        'unit_price',
        'total_price',
        'status_badge',
        'assigned_to_cook'
    ]
    list_filter = ['status', 'menu_item__category', 'order_time']
    search_fields = [
        'mobile_order__order_number',
        'menu_item__name_en',
        'special_instructions',
        'assigned_to_cook'
    ]
    readonly_fields = ['total_price', 'order_time', 'preparation_started', 'ready_time', 'served_time']

    def mobile_order_link(self, obj):
        url = reverse('admin:tables_mobileorder_change', args=[obj.mobile_order.pk])
        return format_html('<a href="{}">{}</a>', url, obj.mobile_order.order_number)
    mobile_order_link.short_description = 'Order'

    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'preparing': 'blue',
            'ready': 'green',
            'served': 'darkgreen',
            'cancelled': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

@admin.register(KitchenDisplayOrder)
class KitchenDisplayOrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number',
        'table_number',
        'customer_count',
        'status_badge',
        'priority_badge',
        'assigned_cook',
        'wait_time_display',
        'is_overdue',
        'received_at'
    ]
    list_filter = ['status', 'priority', 'assigned_cook', 'received_at']
    search_fields = [
        'mobile_order__order_number',
        'mobile_order__table__table_number',
        'assigned_cook',
        'kitchen_notes'
    ]
    readonly_fields = [
        'mobile_order',
        'received_at',
        'preparation_started',
        'ready_at',
        'completed_at',
        'wait_time_minutes',
        'is_overdue'
    ]

    def wait_time_display(self, obj):
        minutes = obj.wait_time_minutes
        if obj.is_overdue:
            return format_html('<span style="color: red; font-weight: bold;">{} min (OVERDUE)</span>', minutes)
        return f'{minutes} min'
    wait_time_display.short_description = 'Wait Time'

    def status_badge(self, obj):
        colors = {
            'pending': 'red',
            'preparing': 'orange',
            'ready': 'green',
            'completed': 'gray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def priority_badge(self, obj):
        colors = {
            'low': 'gray',
            'normal': 'blue',
            'high': 'orange',
            'urgent': 'red'
        }
        color = colors.get(obj.priority, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'

    actions = ['start_preparation', 'mark_ready', 'mark_completed']

    def start_preparation(self, request, queryset):
        count = 0
        for order in queryset:
            if order.status == 'pending':
                order.start_preparation()
                count += 1
        self.message_user(request, f'{count} orders started preparation.')
    start_preparation.short_description = 'Start preparation for selected orders'

    def mark_ready(self, request, queryset):
        count = 0
        for order in queryset:
            if order.status == 'preparing':
                order.mark_ready()
                count += 1
        self.message_user(request, f'{count} orders marked as ready.')
    mark_ready.short_description = 'Mark selected orders as ready'

    def mark_completed(self, request, queryset):
        count = 0
        for order in queryset:
            if order.status == 'ready':
                order.mark_completed()
                count += 1
        self.message_user(request, f'{count} orders marked as completed.')
    mark_completed.short_description = 'Mark selected orders as completed'

@admin.register(EnhancedBillingSession)
class EnhancedBillingSessionAdmin(admin.ModelAdmin):
    list_display = [
        'session_id',
        'table_link',
        'customer_name',
        'customer_count',
        'status_badge',
        'subtotal',
        'total_amount',
        'payment_method',
        'duration_minutes',
        'order_count',
        'created_at'
    ]
    list_filter = ['status', 'payment_method', 'payment_status', 'created_at']
    search_fields = [
        'session_id',
        'customer_name',
        'customer_phone',
        'table__table_number'
    ]
    readonly_fields = [
        'session_id',
        'session_start',
        'actual_end_time',
        'duration_minutes',
        'order_count',
        'created_at',
        'updated_at'
    ]

    fieldsets = (
        ('Session Information', {
            'fields': ('session_id', 'table', 'status')
        }),
        ('Customer Information', {
            'fields': ('customer_name', 'customer_phone', 'customer_count')
        }),
        ('Timing', {
            'fields': ('session_start', 'estimated_end_time', 'actual_end_time', 'duration_minutes'),
            'classes': ('collapse',)
        }),
        ('Billing Details', {
            'fields': ('subtotal', 'discount_amount', 'tax_amount', 'service_charge', 'total_amount')
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'payment_status', 'cash_amount', 'card_amount', 'upi_amount'),
            'classes': ('collapse',)
        }),
        ('System', {
            'fields': ('billed_by', 'order_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def table_link(self, obj):
        url = reverse('admin:tables_restauranttable_change', args=[obj.table.pk])
        return format_html('<a href="{}">{}</a>', url, obj.table.table_number)
    table_link.short_description = 'Table'

    def status_badge(self, obj):
        colors = {
            'active': 'blue',
            'ready_to_bill': 'orange',
            'billing_in_progress': 'purple',
            'billed': 'green',
            'completed': 'darkgreen',
            'cancelled': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    actions = ['prepare_for_billing', 'calculate_totals']

    def prepare_for_billing(self, request, queryset):
        count = 0
        for session in queryset:
            if session.status == 'active':
                session.prepare_for_billing()
                count += 1
        self.message_user(request, f'{count} sessions prepared for billing.')
    prepare_for_billing.short_description = 'Prepare selected sessions for billing'

    def calculate_totals(self, request, queryset):
        count = 0
        for session in queryset:
            session.calculate_totals()
            count += 1
        self.message_user(request, f'{count} session totals recalculated.')
    calculate_totals.short_description = 'Recalculate totals for selected sessions'

# Legacy model admin - for backward compatibility and data migration
@admin.register(TableOrder)
class TableOrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'table', 'customer_name', 'waiter', 'status', 'total_amount', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order_number', 'customer_name']
    readonly_fields = ['created_at']

    def has_add_permission(self, request):
        return False  # Prevent adding new legacy orders

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            return qs.none()  # Hide from non-superusers
        return qs

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'menu_item', 'quantity', 'unit_price']
    list_filter = ['order__created_at']
    search_fields = ['order__order_number', 'menu_item__name_en']

    def has_add_permission(self, request):
        return False  # Prevent adding new legacy items

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            return qs.none()  # Hide from non-superusers
        return qs

@admin.register(KitchenDisplayItem)
class KitchenDisplayItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order__order_number']
    readonly_fields = ['created_at']

    def has_add_permission(self, request):
        return False  # Prevent adding new legacy items

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            return qs.none()  # Hide from non-superusers
        return qs

# Custom admin site configuration
admin.site.site_header = 'Hotel Management System'
admin.site.site_title = 'Hotel Admin'
admin.site.index_title = 'Hotel Management Administration'

