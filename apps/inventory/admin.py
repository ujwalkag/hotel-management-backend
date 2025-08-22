# apps/inventory/admin.py
from django.contrib import admin
from django.utils import timezone
from .models import (
    InventoryCategory, 
    InventoryItem, 
    StockMovement, 
    LowStockAlert,
    Supplier,
    PurchaseOrder,
    PurchaseOrderItem
)

@admin.register(InventoryCategory)
class InventoryCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'items_count', 'total_value', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['items_count', 'total_value', 'created_at', 'updated_at']

    fieldsets = (
        ('Category Information', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Summary', {
            'fields': ('items_count', 'total_value'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['activate_categories', 'deactivate_categories']

    def activate_categories(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} categories activated.')
    activate_categories.short_description = "Activate selected categories"

    def deactivate_categories(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} categories deactivated.')
    deactivate_categories.short_description = "Deactivate selected categories"

@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'category', 'current_stock', 'unit', 'stock_status', 
                   'cost_per_unit', 'total_value', 'is_active', 'last_updated']
    list_filter = ['category', 'unit', 'is_active', 'created_at']
    search_fields = ['name', 'sku', 'description']
    readonly_fields = ['sku', 'total_value', 'stock_status', 'stock_status_class', 
                      'is_low_stock', 'is_out_of_stock', 'is_overstocked', 
                      'days_until_expiry', 'is_expired', 'is_expiring_soon', 
                      'created_at', 'last_updated']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'name', 'description', 'sku')
        }),
        ('Stock Details', {
            'fields': ('unit', 'current_stock', 'min_stock_level', 'max_stock_level')
        }),
        ('Pricing', {
            'fields': ('cost_per_unit', 'selling_price_per_unit', 'total_value')
        }),
        ('Supplier Information', {
            'fields': ('supplier_name', 'supplier_contact')
        }),
        ('Additional Details', {
            'fields': ('expiry_date', 'location', 'is_active')
        }),
        ('Stock Status', {
            'fields': ('stock_status', 'stock_status_class', 'is_low_stock', 
                      'is_out_of_stock', 'is_overstocked', 'days_until_expiry', 
                      'is_expired', 'is_expiring_soon'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'last_updated'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category')

    actions = ['activate_items', 'deactivate_items', 'mark_low_stock']

    def activate_items(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} items activated.')
    activate_items.short_description = "Activate selected items"

    def deactivate_items(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} items deactivated.')
    deactivate_items.short_description = "Deactivate selected items"

    def mark_low_stock(self, request, queryset):
        count = 0
        for item in queryset:
            if item.is_low_stock and not item.alerts.filter(is_resolved=False).exists():
                LowStockAlert.objects.create(
                    item=item,
                    stock_level_at_alert=item.current_stock,
                    threshold_level=item.min_stock_level
                )
                count += 1
        self.message_user(request, f'{count} low stock alerts created.')
    mark_low_stock.short_description = "Create alerts for low stock items"

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['item', 'movement_type', 'quantity', 'cost_per_unit', 
                   'total_cost', 'supplier_name', 'date', 'recorded_by']
    list_filter = ['movement_type', 'date', 'item__category']
    search_fields = ['item__name', 'supplier_name', 'invoice_number', 'reference']
    readonly_fields = ['total_cost', 'movement_direction', 'created_at']
    date_hierarchy = 'date'

    fieldsets = (
        ('Movement Information', {
            'fields': ('item', 'movement_type', 'quantity', 'cost_per_unit', 'total_cost', 'movement_direction')
        }),
        ('Supplier Details', {
            'fields': ('supplier_name', 'invoice_number', 'batch_number')
        }),
        ('Additional Information', {
            'fields': ('expiry_date', 'date', 'reference', 'notes')
        }),
        ('Audit Trail', {
            'fields': ('recorded_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('item', 'recorded_by')

@admin.register(LowStockAlert)
class LowStockAlertAdmin(admin.ModelAdmin):
    list_display = ['item', 'stock_level_at_alert', 'threshold_level', 'alert_date', 
                   'is_resolved', 'days_since_alert', 'resolved_by']
    list_filter = ['is_resolved', 'alert_date', 'item__category']
    search_fields = ['item__name', 'item__sku']
    readonly_fields = ['days_since_alert', 'alert_date']

    fieldsets = (
        ('Alert Information', {
            'fields': ('item', 'stock_level_at_alert', 'threshold_level', 'alert_date', 'days_since_alert')
        }),
        ('Resolution', {
            'fields': ('is_resolved', 'resolved_date', 'resolved_by', 'notes')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('item', 'resolved_by')

    actions = ['resolve_selected_alerts', 'mark_as_unresolved']
    
    def resolve_selected_alerts(self, request, queryset):
        updated = queryset.filter(is_resolved=False).update(
            is_resolved=True,
            resolved_date=timezone.now(),
            resolved_by=request.user
        )
        self.message_user(request, f'{updated} alerts marked as resolved.')
    resolve_selected_alerts.short_description = "Resolve selected alerts"

    def mark_as_unresolved(self, request, queryset):
        updated = queryset.update(
            is_resolved=False,
            resolved_date=None,
            resolved_by=None
        )
        self.message_user(request, f'{updated} alerts marked as unresolved.')
    mark_as_unresolved.short_description = "Mark as unresolved"

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_person', 'phone', 'email', 'is_active', 'total_purchase_amount']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'contact_person', 'phone', 'email']
    readonly_fields = ['total_purchase_amount', 'created_at', 'updated_at']

    fieldsets = (
        ('Supplier Information', {
            'fields': ('name', 'contact_person', 'phone', 'email')
        }),
        ('Address & Details', {
            'fields': ('address', 'gst_number', 'payment_terms')
        }),
        ('Status & Summary', {
            'fields': ('is_active', 'total_purchase_amount')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['activate_suppliers', 'deactivate_suppliers']

    def activate_suppliers(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} suppliers activated.')
    activate_suppliers.short_description = "Activate selected suppliers"

    def deactivate_suppliers(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} suppliers deactivated.')
    deactivate_suppliers.short_description = "Deactivate selected suppliers"

class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 0
    readonly_fields = ['total_amount', 'pending_quantity', 'is_fully_received']
    fields = ['item', 'quantity_ordered', 'quantity_received', 'unit_price', 
              'total_amount', 'pending_quantity', 'is_fully_received']

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'supplier', 'order_date', 'status', 'total_amount', 'created_by']
    list_filter = ['status', 'order_date', 'supplier']
    search_fields = ['order_number', 'supplier__name']
    readonly_fields = ['order_number', 'total_amount', 'created_at', 'updated_at']
    inlines = [PurchaseOrderItemInline]
    date_hierarchy = 'order_date'

    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'supplier', 'order_date', 'expected_delivery_date')
        }),
        ('Status & Amount', {
            'fields': ('status', 'total_amount')
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('supplier', 'created_by')

    actions = ['mark_as_confirmed', 'mark_as_completed', 'calculate_totals']

    def mark_as_confirmed(self, request, queryset):
        updated = queryset.filter(status='draft').update(status='confirmed')
        self.message_user(request, f'{updated} orders marked as confirmed.')
    mark_as_confirmed.short_description = "Mark as confirmed"

    def mark_as_completed(self, request, queryset):
        updated = queryset.filter(status__in=['confirmed', 'partial']).update(status='completed')
        self.message_user(request, f'{updated} orders marked as completed.')
    mark_as_completed.short_description = "Mark as completed"

    def calculate_totals(self, request, queryset):
        updated = 0
        for order in queryset:
            order.calculate_total()
            updated += 1
        self.message_user(request, f'{updated} order totals recalculated.')
    calculate_totals.short_description = "Recalculate order totals"
