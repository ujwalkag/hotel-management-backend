# apps/inventory/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Sum, Count, F
from datetime import datetime, timedelta
from .models import (
    InventoryCategory, 
    InventoryItem, 
    StockMovement, 
    LowStockAlert,
    Supplier,
    PurchaseOrder
)
from .serializers import (
    InventoryCategorySerializer,
    InventoryItemSerializer,
    StockMovementSerializer,
    StockMovementCreateSerializer,
    LowStockAlertSerializer,
    SupplierSerializer,
    PurchaseOrderSerializer,
    PurchaseOrderCreateSerializer,
    InventoryDashboardSerializer
)
from .permissions import IsAdminOnly, IsAdminOrStaffReadOnly

class InventoryCategoryViewSet(viewsets.ModelViewSet):
    queryset = InventoryCategory.objects.filter(is_active=True)
    serializer_class = InventoryCategorySerializer
    permission_classes = [IsAuthenticated, IsAdminOnly]  # Admin only
    
    def get_queryset(self):
        queryset = InventoryCategory.objects.all()
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
            
        return queryset.order_by('name')

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get category summary with item counts"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        total_categories = queryset.count()
        total_items = sum(category.items_count for category in queryset)
        total_value = sum(category.total_value for category in queryset)
        
        return Response({
            'categories': serializer.data,
            'summary': {
                'total_categories': total_categories,
                'total_items': total_items,
                'total_value': float(total_value)
            }
        })

class InventoryItemViewSet(viewsets.ModelViewSet):
    queryset = InventoryItem.objects.all()
    serializer_class = InventoryItemSerializer
    permission_classes = [IsAuthenticated, IsAdminOrStaffReadOnly]  # Staff can view, admin can modify
    
    def get_queryset(self):
        queryset = InventoryItem.objects.select_related('category')
        
        # Filter by category
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category_id=category)
        
        # Filter by stock status
        status_filter = self.request.query_params.get('status', None)
        if status_filter == 'low_stock':
            queryset = queryset.filter(current_stock__lte=F('min_stock_level'))
        elif status_filter == 'out_of_stock':
            queryset = queryset.filter(current_stock__lte=0)
        elif status_filter == 'in_stock':
            queryset = queryset.filter(current_stock__gt=F('min_stock_level'))
        elif status_filter == 'overstocked':
            queryset = queryset.filter(current_stock__gte=F('max_stock_level'))
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
            
        # Search by name, SKU, or description
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(sku__icontains=search) |
                Q(description__icontains=search)
            )
            
        return queryset.order_by('name')
    
    @action(detail=False, methods=['get'])
    def low_stock_items(self, request):
        """Get items with low stock"""
        items = self.get_queryset().filter(current_stock__lte=F('min_stock_level'))
        serializer = self.get_serializer(items, many=True)
        return Response({
            'count': items.count(),
            'items': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def out_of_stock_items(self, request):
        """Get items that are out of stock"""
        items = self.get_queryset().filter(current_stock__lte=0)
        serializer = self.get_serializer(items, many=True)
        return Response({
            'count': items.count(),
            'items': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        """Get items expiring soon"""
        days = int(request.query_params.get('days', 7))
        expiry_threshold = timezone.now().date() + timedelta(days=days)
        
        items = self.get_queryset().filter(
            expiry_date__lte=expiry_threshold,
            expiry_date__gte=timezone.now().date()
        )
        serializer = self.get_serializer(items, many=True)
        return Response({
            'count': items.count(),
            'items': serializer.data,
            'threshold_days': days
        })
    
    @action(detail=False, methods=['get'])
    def dashboard_summary(self, request):
        """Get inventory dashboard summary"""
        queryset = self.get_queryset()
        
        total_items = queryset.count()
        active_items = queryset.filter(is_active=True)
        low_stock_count = active_items.filter(current_stock__lte=F('min_stock_level')).count()
        out_of_stock_count = active_items.filter(current_stock__lte=0).count()
        total_value = sum(item.total_value for item in active_items)
        
        # Expiring items
        expiry_threshold = timezone.now().date() + timedelta(days=7)
        expiring_count = active_items.filter(
            expiry_date__lte=expiry_threshold,
            expiry_date__gte=timezone.now().date()
        ).count()
        
        # Recent stock movements
        recent_movements_count = StockMovement.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        # Active low stock alerts
        active_alerts_count = LowStockAlert.objects.filter(is_resolved=False).count()
        
        summary_data = {
            'total_items': total_items,
            'total_categories': InventoryCategory.objects.filter(is_active=True).count(),
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
            'expiring_count': expiring_count,
            'total_inventory_value': total_value,
            'recent_movements_count': recent_movements_count,
            'active_alerts_count': active_alerts_count
        }
        
        serializer = InventoryDashboardSerializer(data=summary_data)
        serializer.is_valid()
        
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def update_stock(self, request, pk=None):
        """Update item stock with movement record"""
        item = self.get_object()
        movement_data = request.data
        
        serializer = StockMovementCreateSerializer(data=movement_data)
        if serializer.is_valid():
            movement = serializer.save(
                item=item,
                recorded_by=request.user
            )
            
            # Stock is updated automatically by signal
            item.refresh_from_db()
            
            return Response({
                'message': 'Stock updated successfully',
                'new_stock_level': float(item.current_stock),
                'movement_id': movement.id,
                'stock_status': item.stock_status
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class StockMovementViewSet(viewsets.ModelViewSet):
    queryset = StockMovement.objects.all()
    permission_classes = [IsAuthenticated, IsAdminOnly]  # Admin only
    
    def get_serializer_class(self):
        if self.action == 'create':
            return StockMovementCreateSerializer
        return StockMovementSerializer
    
    def get_queryset(self):
        queryset = StockMovement.objects.select_related('item', 'recorded_by')
        
        # Filter by item
        item_id = self.request.query_params.get('item', None)
        if item_id:
            queryset = queryset.filter(item_id=item_id)
        
        # Filter by movement type
        movement_type = self.request.query_params.get('type', None)
        if movement_type:
            queryset = queryset.filter(movement_type=movement_type)
            
        # Filter by date range
        from_date = self.request.query_params.get('from_date', None)
        to_date = self.request.query_params.get('to_date', None)
        
        if from_date:
            try:
                from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
                queryset = queryset.filter(date__gte=from_date_obj)
            except ValueError:
                pass
                
        if to_date:
            try:
                to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
                queryset = queryset.filter(date__lte=to_date_obj)
            except ValueError:
                pass
            
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def daily_report(self, request):
        """Get daily stock movement report"""
        date_str = request.query_params.get('date', timezone.now().date())
        
        if isinstance(date_str, str):
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Invalid date format'}, status=400)
        else:
            date = date_str
            
        movements = self.get_queryset().filter(date__date=date)
        
        # Summary by movement type
        summary = {}
        for movement_type, _ in StockMovement.MOVEMENT_TYPES:
            type_movements = movements.filter(movement_type=movement_type)
            summary[movement_type] = {
                'count': type_movements.count(),
                'total_quantity': sum(float(m.quantity) for m in type_movements),
                'total_value': sum(float(m.total_cost) for m in type_movements)
            }
        
        serializer = self.get_serializer(movements, many=True)
        
        return Response({
            'date': date,
            'movements': serializer.data,
            'summary': summary,
            'total_movements': movements.count()
        })

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get stock movement summary"""
        queryset = self.get_queryset()
        
        # Summary by movement type
        movement_summary = queryset.values('movement_type').annotate(
            count=Count('id'),
            total_quantity=Sum('quantity'),
            total_value=Sum(F('quantity') * F('cost_per_unit'))
        ).order_by('movement_type')
        
        total_movements = queryset.count()
        total_value = sum(float(movement.total_cost) for movement in queryset)
        
        return Response({
            'total_movements': total_movements,
            'total_value': total_value,
            'movement_summary': list(movement_summary)
        })

class LowStockAlertViewSet(viewsets.ModelViewSet):
    queryset = LowStockAlert.objects.all()
    serializer_class = LowStockAlertSerializer
    permission_classes = [IsAuthenticated, IsAdminOrStaffReadOnly]  # Staff can view alerts
    
    def get_queryset(self):
        queryset = LowStockAlert.objects.select_related('item', 'resolved_by')
        
        # Filter by resolution status
        is_resolved = self.request.query_params.get('is_resolved', None)
        if is_resolved is not None:
            queryset = queryset.filter(is_resolved=is_resolved.lower() == 'true')
        
        # Filter by item category
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(item__category_id=category)
            
        return queryset.order_by('-alert_date')
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve a low stock alert"""
        if request.user.role != 'admin':
            return Response({'error': 'Only admin can resolve alerts'}, 
                          status=status.HTTP_403_FORBIDDEN)
            
        alert = self.get_object()
        notes = request.data.get('notes', '')
        
        alert.resolve_alert(user=request.user, notes=notes)
        
        return Response({
            'message': 'Alert resolved successfully',
            'resolved_date': alert.resolved_date
        })
    
    @action(detail=False, methods=['post'])
    def resolve_multiple(self, request):
        """Resolve multiple alerts"""
        if request.user.role != 'admin':
            return Response({'error': 'Only admin can resolve alerts'}, 
                          status=status.HTTP_403_FORBIDDEN)
            
        alert_ids = request.data.get('alert_ids', [])
        notes = request.data.get('notes', '')
        
        if not alert_ids:
            return Response({'error': 'No alert IDs provided'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        resolved_count = 0
        for alert_id in alert_ids:
            try:
                alert = LowStockAlert.objects.get(id=alert_id, is_resolved=False)
                alert.resolve_alert(user=request.user, notes=notes)
                resolved_count += 1
            except LowStockAlert.DoesNotExist:
                continue
        
        return Response({
            'message': f'{resolved_count} alerts resolved successfully'
        })

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get low stock alerts summary"""
        queryset = self.get_queryset()
        
        total_alerts = queryset.count()
        active_alerts = queryset.filter(is_resolved=False).count()
        resolved_alerts = queryset.filter(is_resolved=True).count()
        
        # Alerts by category
        category_breakdown = queryset.filter(is_resolved=False).values(
            'item__category__name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')
        
        return Response({
            'total_alerts': total_alerts,
            'active_alerts': active_alerts,
            'resolved_alerts': resolved_alerts,
            'category_breakdown': list(category_breakdown)
        })

class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.filter(is_active=True)
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated, IsAdminOnly]  # Admin only

    def get_queryset(self):
        queryset = Supplier.objects.all()
        
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(contact_person__icontains=search) |
                Q(phone__icontains=search) |
                Q(email__icontains=search)
            )
            
        return queryset.order_by('name')

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get suppliers summary"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        total_suppliers = queryset.count()
        active_suppliers = queryset.filter(is_active=True).count()
        total_purchase_value = sum(supplier.total_purchase_amount for supplier in queryset)
        
        return Response({
            'suppliers': serializer.data,
            'summary': {
                'total_suppliers': total_suppliers,
                'active_suppliers': active_suppliers,
                'inactive_suppliers': total_suppliers - active_suppliers,
                'total_purchase_value': float(total_purchase_value)
            }
        })

class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.all()
    permission_classes = [IsAuthenticated, IsAdminOnly]  # Admin only
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PurchaseOrderCreateSerializer
        return PurchaseOrderSerializer
    
    def get_queryset(self):
        queryset = PurchaseOrder.objects.select_related('supplier', 'created_by').prefetch_related('items')
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by supplier
        supplier_id = self.request.query_params.get('supplier', None)
        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)
        
        # Filter by date range
        from_date = self.request.query_params.get('from_date', None)
        to_date = self.request.query_params.get('to_date', None)
        
        if from_date:
            try:
                from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
                queryset = queryset.filter(order_date__gte=from_date_obj)
            except ValueError:
                pass
                
        if to_date:
            try:
                to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
                queryset = queryset.filter(order_date__lte=to_date_obj)
            except ValueError:
                pass
            
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get purchase orders summary"""
        queryset = self.get_queryset()
        
        total_orders = queryset.count()
        total_amount = sum(float(order.total_amount) for order in queryset)
        
        # Status breakdown
        status_breakdown = queryset.values('status').annotate(
            count=Count('id'),
            total_amount=Sum('total_amount')
        ).order_by('status')
        
        return Response({
            'total_orders': total_orders,
            'total_amount': total_amount,
            'status_breakdown': list(status_breakdown)
        })
