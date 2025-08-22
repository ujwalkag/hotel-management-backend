# apps/inventory/views.py - Updated with admin-only permissions
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta

from .models import (
    InventoryCategory, InventoryItem, Supplier, 
    PurchaseOrder, PurchaseOrderItem, StockMovement, LowStockAlert
)
from .serializers import (
    InventoryCategorySerializer, InventoryItemSerializer, SupplierSerializer,
    PurchaseOrderSerializer, PurchaseOrderItemSerializer, StockMovementSerializer,
    LowStockAlertSerializer
)
from .permissions import IsAdminOnly

class InventoryCategoryViewSet(viewsets.ModelViewSet):
    queryset = InventoryCategory.objects.all()
    serializer_class = InventoryCategorySerializer
    permission_classes = [IsAdminOnly]  # 🔒 ADMIN ONLY
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset.order_by('name')

class InventoryItemViewSet(viewsets.ModelViewSet):
    queryset = InventoryItem.objects.all()
    serializer_class = InventoryItemSerializer
    permission_classes = [IsAdminOnly]  # 🔒 ADMIN ONLY
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Search functionality
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(sku__icontains=search) |
                Q(description__icontains=search)
            )
        
        # Category filter
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category_id=category)
            
        # Stock status filter
        stock_status = self.request.query_params.get('stock_status', None)
        if stock_status == 'low':
            queryset = queryset.filter(current_stock__lte=models.F('min_stock_level'))
        elif stock_status == 'out':
            queryset = queryset.filter(current_stock=0)
        elif stock_status == 'over':
            queryset = queryset.filter(current_stock__gte=models.F('max_stock_level'))
            
        return queryset.select_related('category').order_by('name')
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get items with low stock"""
        items = self.queryset.filter(
            current_stock__lte=models.F('min_stock_level'),
            is_active=True
        )
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get inventory statistics"""
        total_items = self.queryset.filter(is_active=True).count()
        low_stock = self.queryset.filter(
            current_stock__lte=models.F('min_stock_level'),
            current_stock__gt=0,
            is_active=True
        ).count()
        out_of_stock = self.queryset.filter(current_stock=0, is_active=True).count()
        total_value = self.queryset.filter(is_active=True).aggregate(
            total=Sum(models.F('current_stock') * models.F('cost_per_unit'))
        )['total'] or 0
        
        return Response({
            'total_items': total_items,
            'low_stock_count': low_stock,
            'out_of_stock_count': out_of_stock,
            'total_inventory_value': float(total_value)
        })

class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAdminOnly]  # 🔒 ADMIN ONLY
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(contact_person__icontains=search) |
                Q(phone__icontains=search) |
                Q(email__icontains=search)
            )
        return queryset.order_by('name')

class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAdminOnly]  # 🔒 ADMIN ONLY
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            
        supplier = self.request.query_params.get('supplier', None)
        if supplier:
            queryset = queryset.filter(supplier_id=supplier)
            
        return queryset.select_related('supplier').order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class StockMovementViewSet(viewsets.ModelViewSet):
    queryset = StockMovement.objects.all()
    serializer_class = StockMovementSerializer
    permission_classes = [IsAdminOnly]  # 🔒 ADMIN ONLY
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        item = self.request.query_params.get('item', None)
        if item:
            queryset = queryset.filter(item_id=item)
            
        movement_type = self.request.query_params.get('type', None)
        if movement_type:
            queryset = queryset.filter(movement_type=movement_type)
            
        # Date range filter
        date_from = self.request.query_params.get('date_from', None)
        date_to = self.request.query_params.get('date_to', None)
        
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
            
        return queryset.select_related('item').order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user)

class LowStockAlertViewSet(viewsets.ModelViewSet):
    queryset = LowStockAlert.objects.all()
    serializer_class = LowStockAlertSerializer
    permission_classes = [IsAdminOnly]  # 🔒 ADMIN ONLY
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        resolved = self.request.query_params.get('resolved', None)
        if resolved is not None:
            is_resolved = resolved.lower() == 'true'
            queryset = queryset.filter(is_resolved=is_resolved)
            
        return queryset.select_related('item').order_by('-alert_date')
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve a low stock alert"""
        alert = self.get_object()
        alert.resolve_alert(user=request.user, notes=request.data.get('notes', ''))
        return Response({'status': 'resolved'})
