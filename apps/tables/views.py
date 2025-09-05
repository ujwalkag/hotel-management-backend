from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Count, Sum
from datetime import datetime, timedelta
from .models import RestaurantTable, TableOrder, OrderItem, KitchenDisplayItem

# FIXED: Import correct serializer names
from .serializers import (
    TableSerializer,
    OrderSerializer, 
    TableOrderCreateSerializer,
    OrderItemSerializer,
    OrderItemCreateSerializer,
    KitchenDisplaySerializer,
    OrderItemUpdateSerializer,
    MobileTableSerializer,
    MobileOrderSerializer
)

class RestaurantTableViewSet(viewsets.ModelViewSet):
    """ViewSet for managing restaurant tables"""
    queryset = RestaurantTable.objects.all()
    serializer_class = TableSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter and search tables"""
        queryset = RestaurantTable.objects.filter(is_active=True)

        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter == 'available':
            queryset = queryset.filter(is_occupied=False)
        elif status_filter == 'occupied':
            queryset = queryset.filter(is_occupied=True)

        # Search functionality
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(table_number__icontains=search) |
                Q(location__icontains=search)
            )

        return queryset.order_by('table_number')

class TableOrderViewSet(viewsets.ModelViewSet):
    """ViewSet for managing table orders"""
    queryset = TableOrder.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return TableOrderCreateSerializer
        return OrderSerializer

    def get_queryset(self):
        """Filter and search orders"""
        queryset = TableOrder.objects.select_related(
            'table', 'waiter'
        ).prefetch_related('items__menu_item')

        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        """Set waiter when creating order"""
        serializer.save(waiter=self.request.user)

class KitchenDisplayViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for kitchen display functionality"""
    serializer_class = KitchenDisplaySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get items that need kitchen attention"""
        queryset = KitchenDisplayItem.objects.filter(
            order_item__status__in=['pending', 'preparing']
        ).select_related(
            'order_item__table_order__table',
            'order_item__table_order__waiter',
            'order_item__menu_item'
        ).order_by('-is_priority', 'display_time')

        return queryset

# ============================================
# MOBILE WAITER API FUNCTIONS
# ============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_tables_layout(request):
    """Get all tables with current status for mobile waiter interface"""
    tables = RestaurantTable.objects.all().order_by('table_number')

    table_data = []
    for table in tables:
        current_order = table.current_order
        table_data.append({
            'id': table.id,
            'table_number': table.table_number,
            'capacity': table.capacity,
            'location': table.location,
            'is_occupied': table.is_occupied,
            'is_active': table.is_active,
            'current_order': {
                'id': current_order.id,
                'order_number': current_order.order_number,
                'customer_name': current_order.customer_name,
                'status': current_order.status,
                'total_amount': float(current_order.total_amount)
            } if current_order else None
        })

    return Response(table_data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_waiter_order(request):
    """Create order from mobile waiter interface"""
    data = request.data
    table_id = data.get('table_id') or data.get('table')
    items = data.get('items', [])

    if not table_id or not items:
        return Response({'error': 'table_id and items are required'}, 
                       status=status.HTTP_400_BAD_REQUEST)

    try:
        from apps.menu.models import MenuItem

        table = get_object_or_404(RestaurantTable, id=table_id)

        # Create the order
        order = TableOrder.objects.create(
            table=table,
            waiter=request.user,
            customer_name=data.get('customer_name', 'Guest'),
            customer_phone=data.get('customer_phone', ''),
            customer_count=data.get('customer_count', 1),
            special_instructions=data.get('special_instructions', '')
        )

        # Add order items
        total_amount = 0
        for item_data in items:
            menu_item_id = item_data.get('menu_item_id') or item_data.get('menu_item')
            menu_item = get_object_or_404(MenuItem, id=menu_item_id)

            order_item = OrderItem.objects.create(
                table_order=order,
                menu_item=menu_item,
                quantity=item_data.get('quantity', 1),
                price=menu_item.price,
                special_instructions=item_data.get('special_instructions', '')
            )
            total_amount += order_item.total_price

        # Update order total and table status
        order.total_amount = total_amount
        order.save()

        table.is_occupied = True
        table.save()

        return Response({
            'success': True,
            'order_id': order.id,
            'order_number': order.order_number,
            'total_amount': float(order.total_amount),
            'message': 'Order created successfully'
        })

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ============================================
# ENHANCED BILLING API FUNCTIONS
# ============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_active_orders_for_billing(request):
    """Get all active table orders for enhanced billing interface"""
    try:
        # Get orders that are in progress but not yet billed
        orders = TableOrder.objects.filter(
            status__in=['pending', 'in_progress', 'ready', 'completed']
        ).exclude(status='billed').select_related('table', 'waiter').prefetch_related('items__menu_item')

        order_data = []
        for order in orders:
            order_data.append({
                'id': order.id,
                'order_number': order.order_number,
                'table_id': order.table.id,
                'table_number': order.table.table_number,
                'customer_name': order.customer_name or 'Guest',
                'customer_phone': order.customer_phone or '',
                'customer_count': order.customer_count,
                'waiter_name': order.waiter.email if order.waiter else 'System',
                'total_amount': float(order.total_amount or 0),
                'status': order.status,
                'created_at': order.created_at.isoformat(),
                'items': [
                    {
                        'id': item.id,
                        'menu_item': {
                            'id': item.menu_item.id,
                            'name_en': item.menu_item.name_en,
                            'name_hi': getattr(item.menu_item, 'name_hi', ''),
                        },
                        'quantity': item.quantity,
                        'price': float(item.price),
                        'special_instructions': item.special_instructions,
                        'status': item.status
                    }
                    for item in order.items.all()
                ]
            })

        return Response(order_data)

    except Exception as e:
        return Response({'error': f'Failed to fetch orders: {str(e)}'}, 
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ============================================
# KITCHEN API FUNCTIONS
# ============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_kitchen_orders(request):
    """Get all orders for kitchen display"""
    try:
        # Get all active order items that need kitchen attention
        order_items = OrderItem.objects.filter(
            table_order__status__in=['pending', 'in_progress'],
            status__in=['pending', 'preparing']
        ).select_related('table_order__table', 'table_order__waiter', 'menu_item').order_by('order_time')

        kitchen_orders = []
        for item in order_items:
            kitchen_orders.append({
                'id': item.id,
                'table_number': item.table_order.table.table_number,
                'order_number': item.table_order.order_number,
                'customer_name': item.table_order.customer_name,
                'waiter_name': item.table_order.waiter.email if item.table_order.waiter else 'System',
                'status': item.status,
                'created_at': item.order_time.isoformat(),
                'menu_item': {
                    'name_en': item.menu_item.name_en,
                    'name_hi': getattr(item.menu_item, 'name_hi', ''),
                },
                'quantity': item.quantity,
                'special_instructions': item.special_instructions
            })

        return Response(kitchen_orders)

    except Exception as e:
        return Response({'error': f'Kitchen orders error: {str(e)}'}, 
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_kitchen_order_status(request, order_item_id):
    """Update status of a kitchen order item"""
    try:
        order_item = get_object_or_404(OrderItem, id=order_item_id)
        new_status = request.data.get('status')
        
        if new_status not in ['pending', 'preparing', 'ready', 'served']:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        
        order_item.status = new_status
        
        # Set timestamps based on status
        if new_status == 'preparing':
            order_item.preparation_started = timezone.now()
        elif new_status == 'ready':
            order_item.ready_time = timezone.now()
        elif new_status == 'served':
            order_item.served_time = timezone.now()
        
        order_item.save()
        
        # Check if all items in the order are ready/served
        order = order_item.table_order
        all_items = order.items.all()
        
        if all(item.status in ['ready', 'served'] for item in all_items):
            order.status = 'ready'
            order.save()
        
        return Response({
            'success': True,
            'message': f'Order item status updated to {new_status}'
        })

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

