# apps/tables/admin.py
from django.contrib import admin
from .models import RestaurantTable, TableOrder, OrderItem, KitchenDisplayItem

@admin.register(RestaurantTable)
class RestaurantTableAdmin(admin.ModelAdmin):
    list_display = ['table_number', 'capacity', 'location', 'is_active', 'is_occupied', 'active_orders_count', 'created_at']
    list_filter = ['is_active', 'is_occupied', 'capacity', 'location']
    search_fields = ['table_number', 'location']
    ordering = ['table_number']
    readonly_fields = ['active_orders_count', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Table Information', {
            'fields': ('table_number', 'capacity', 'location')
        }),
        ('Status', {
            'fields': ('is_active', 'is_occupied', 'active_orders_count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['total_price', 'preparation_time_minutes', 'order_time']
    fields = ['menu_item', 'quantity', 'price', 'total_price', 'status', 'special_instructions', 
              'order_time', 'preparation_started', 'ready_time', 'served_time']

@admin.register(TableOrder)
class TableOrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'table', 'customer_name', 'waiter', 'status', 'total_amount', 'created_at']
    list_filter = ['status', 'created_at', 'table', 'waiter']
    search_fields = ['order_number', 'customer_name', 'customer_phone']
    readonly_fields = ['order_number', 'total_amount', 'created_at', 'updated_at']
    inlines = [OrderItemInline]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'table', 'waiter')
        }),
        ('Customer Details', {
            'fields': ('customer_name', 'customer_phone', 'customer_count')
        }),
        ('Order Details', {
            'fields': ('status', 'total_amount', 'special_instructions')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('table', 'waiter')

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['menu_item', 'table_order', 'quantity', 'price', 'total_price', 'status', 'order_time']
    list_filter = ['status', 'order_time', 'menu_item__category']
    search_fields = ['menu_item__name_en', 'table_order__order_number', 'table_order__customer_name']
    readonly_fields = ['total_price', 'preparation_time_minutes', 'order_time']
    date_hierarchy = 'order_time'
    
    fieldsets = (
        ('Order Item Details', {
            'fields': ('table_order', 'menu_item', 'quantity', 'price', 'total_price')
        }),
        ('Status & Instructions', {
            'fields': ('status', 'special_instructions')
        }),
        ('Timing', {
            'fields': ('order_time', 'preparation_started', 'ready_time', 'served_time', 'preparation_time_minutes')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('table_order', 'menu_item')

@admin.register(KitchenDisplayItem)
class KitchenDisplayItemAdmin(admin.ModelAdmin):
    list_display = ['order_item', 'estimated_prep_time', 'is_priority', 'is_highlighted', 'time_since_order', 'display_time']
    list_filter = ['is_priority', 'is_highlighted', 'display_time', 'order_item__status']
    search_fields = ['order_item__menu_item__name_en', 'order_item__table_order__order_number']
    readonly_fields = ['time_since_order', 'is_overdue', 'display_time']
    
    fieldsets = (
        ('Kitchen Display Settings', {
            'fields': ('order_item', 'estimated_prep_time', 'is_priority', 'is_highlighted')
        }),
        ('Notes', {
            'fields': ('kitchen_notes',)
        }),
        ('Timing Information', {
            'fields': ('display_time', 'time_since_order', 'is_overdue'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'order_item__table_order__table',
            'order_item__menu_item'
        )
    
    actions = ['mark_as_priority', 'remove_priority', 'highlight_items', 'remove_highlight']
    
    def mark_as_priority(self, request, queryset):
        updated = queryset.update(is_priority=True)
        self.message_user(request, f'{updated} items marked as priority.')
    mark_as_priority.short_description = "Mark selected items as priority"
    
    def remove_priority(self, request, queryset):
        updated = queryset.update(is_priority=False)
        self.message_user(request, f'Priority removed from {updated} items.')
    remove_priority.short_description = "Remove priority from selected items"
    
    def highlight_items(self, request, queryset):
        updated = queryset.update(is_highlighted=True)
        self.message_user(request, f'{updated} items highlighted.')
    highlight_items.short_description = "Highlight selected items"
    
    def remove_highlight(self, request, queryset):
        updated = queryset.update(is_highlighted=False)
        self.message_user(request, f'Highlight removed from {updated} items.')
    remove_highlight.short_description = "Remove highlight from selected items"
