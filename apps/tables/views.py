# apps/tables/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Count, Sum
from datetime import datetime, timedelta
from .models import RestaurantTable, TableOrder, OrderItem, KitchenDisplayItem
from .serializers import (
    RestaurantTableSerializer, 
    TableOrderSerializer, 
    TableOrderCreateSerializer,
    OrderItemSerializer,
    OrderItemCreateSerializer,
    KitchenDisplaySerializer,
    OrderItemUpdateSerializer
)
from .permissions import IsAdminOrStaff, CanViewKitchenDisplay

class RestaurantTableViewSet(viewsets.ModelViewSet):
    queryset = RestaurantTable.objects.all()
    serializer_class = RestaurantTableSerializer
    permission_classes = [IsAuthenticated, IsAdminOrStaff]
    
    def get_queryset(self):
        queryset = RestaurantTable.objects.filter(is_active=True)
        status_filter = self.request.query_params.get('status', None)
        
        if status_filter == 'available':
            queryset = queryset.filter(is_occupied=False)
        elif status_filter == 'occupied':
            queryset = queryset.filter(is_occupied=True)
        
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(table_number__icontains=search) |
                Q(location__icontains=search)
            )
            
        return queryset.order_by('table_number')
    
    @action(detail=True, methods=['post'])
    def create_order(self, request, pk=None):
        """Create a new order for this table"""
        table = self.get_object()
        
        # Check if table is already occupied
        if table.is_occupied and table.current_order:
            return Response({
                'error': 'Table is already occupied',
                'current_order': table.current_order.order_number
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = TableOrderCreateSerializer(data=request.data)
        if serializer.is_valid():
            order = serializer.save(
                table=table,
                waiter=request.user
            )
            
            return Response({
                'message': 'Order created successfully',
                'order_id': order.id,
                'order_number': order.order_number,
                'total_amount': str(order.total_amount)
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def current_orders(self, request, pk=None):
        """Get current active orders for this table"""
        table = self.get_object()
        orders = table.orders.filter(status__in=['pending', 'in_progress'])
        serializer = TableOrderSerializer(orders, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def free_table(self, request, pk=None):
        """Free up the table (mark as not occupied)"""
        table = self.get_object()
        
        # Check if there are any active orders
        active_orders = table.orders.filter(status__in=['pending', 'in_progress']).count()
        if active_orders > 0:
            return Response({
                'error': 'Cannot free table with active orders',
                'active_orders_count': active_orders
            }, status=status.HTTP_400_BAD_REQUEST)
        
        table.is_occupied = False
        table.save()
        
        return Response({
            'message': 'Table freed successfully',
            'table_number': table.table_number
        })
    
    @action(detail=False, methods=['get'])
    def dashboard_summary(self, request):
        """Get table management dashboard summary"""
        queryset = self.get_queryset()
        
        total_tables = queryset.count()
        occupied_tables = queryset.filter(is_occupied=True).count()
        available_tables = total_tables - occupied_tables
        
        # Active orders count
        active_orders = TableOrder.objects.filter(
            status__in=['pending', 'in_progress']
        ).count()
        
        # Today's completed orders
        today = timezone.now().date()
        today_completed = TableOrder.objects.filter(
            status='completed',
            created_at__date=today
        ).count()
        
        return Response({
            'total_tables': total_tables,
            'occupied_tables': occupied_tables,
            'available_tables': available_tables,
            'active_orders': active_orders,
            'today_completed_orders': today_completed
        })

class TableOrderViewSet(viewsets.ModelViewSet):
    queryset = TableOrder.objects.all()
    permission_classes = [IsAuthenticated, IsAdminOrStaff]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TableOrderCreateSerializer
        return TableOrderSerializer
    
    def get_queryset(self):
        queryset = TableOrder.objects.select_related('table', 'waiter').prefetch_related('items__menu_item')
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by table
        table_id = self.request.query_params.get('table', None)
        if table_id:
            queryset = queryset.filter(table_id=table_id)
            
        # Filter by waiter
        waiter_id = self.request.query_params.get('waiter', None)
        if waiter_id:
            queryset = queryset.filter(waiter_id=waiter_id)
            
        # Filter by date
        date_filter = self.request.query_params.get('date', None)
        if date_filter:
            try:
                date_obj = datetime.strptime(date_filter, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date=date_obj)
            except ValueError:
                pass
        
        # Search by customer name or order number
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(customer_name__icontains=search) |
                Q(order_number__icontains=search) |
                Q(customer_phone__icontains=search)
            )
            
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(waiter=self.request.user)
    
    @action(detail=True, methods=['post'])
    def add_items(self, request, pk=None):
        """Add items to existing order"""
        order = self.get_object()
        
        if order.status not in ['pending', 'in_progress']:
            return Response({'error': 'Cannot add items to completed order'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        items_data = request.data.get('items', [])
        if not items_data:
            return Response({'error': 'No items provided'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        created_items = []
        errors = []
        
        for item_data in items_data:
            serializer = OrderItemCreateSerializer(data=item_data)
            if serializer.is_valid():
                menu_item = serializer.validated_data['menu_item']
                order_item = OrderItem.objects.create(
                    table_order=order,
                    menu_item=menu_item,
                    price=menu_item.price,
                    **serializer.validated_data
                )
                created_items.append(order_item)
            else:
                errors.append({
                    'item_data': item_data,
                    'errors': serializer.errors
                })
        
        if errors and not created_items:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
        
        order.calculate_total()
        
        response_data = {
            'message': f'{len(created_items)} items added successfully',
            'total_amount': str(order.total_amount),
            'items_added': len(created_items)
        }
        
        if errors:
            response_data['errors'] = errors
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def complete_order(self, request, pk=None):
        """Mark order as completed"""
        order = self.get_object()
        
        if order.status == 'completed':
            return Response({'message': 'Order is already completed'})
        
        # Check if all items are served
        pending_items = order.items.exclude(status__in=['served', 'cancelled']).count()
        if pending_items > 0:
            return Response({
                'error': f'Cannot complete order with {pending_items} pending items'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        order.mark_completed()
        
        return Response({
            'message': 'Order completed successfully',
            'status': order.status,
            'completed_at': order.completed_at
        })
    
    @action(detail=True, methods=['post'])
    def generate_bill(self, request, pk=None):
        """Generate bill for this order"""
        order = self.get_object()
        
        if order.status != 'completed':
            return Response({
                'error': 'Order must be completed before generating bill'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Import here to avoid circular imports
        from apps.bills.models import Bill, BillItem
        
        # Check if bill already exists
        existing_bill = Bill.objects.filter(
            customer_name=order.customer_name,
            customer_phone=order.customer_phone,
            total_amount=order.total_amount,
            created_at__date=order.created_at.date()
        ).first()
        
        if existing_bill:
            return Response({
                'message': 'Bill already exists',
                'bill_id': existing_bill.id,
                'receipt_number': existing_bill.receipt_number
            })
        
        # Create bill
        bill = Bill.objects.create(
            user=request.user,
            bill_type='restaurant',
            customer_name=order.customer_name or 'Guest',
            customer_phone=order.customer_phone or 'N/A',
            total_amount=order.total_amount,
            payment_method=request.data.get('payment_method', 'cash')
        )
        
        # Add bill items
        for order_item in order.items.all():
            BillItem.objects.create(
                bill=bill,
                item_name=order_item.menu_item.name_en,
                quantity=order_item.quantity,
                price=order_item.price
            )
        
        # Mark order as billed
        order.status = 'billed'
        order.save()
        
        return Response({
            'message': 'Bill generated successfully',
            'bill_id': bill.id,
            'receipt_number': bill.receipt_number,
            'total_amount': str(bill.total_amount),
            'payment_method': bill.payment_method
        })
    
    @action(detail=True, methods=['post'])
    def cancel_order(self, request, pk=None):
        """Cancel an order"""
        order = self.get_object()
        
        if order.status in ['completed', 'billed']:
            return Response({
                'error': 'Cannot cancel completed or billed order'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Cancel all pending items
        order.items.filter(status='pending').update(status='cancelled')
        
        # Update order status
        order.status = 'cancelled'
        order.save()
        
        # Free up table if no other active orders
        if order.table.active_orders_count == 0:
            order.table.is_occupied = False
            order.table.save()
        
        return Response({
            'message': 'Order cancelled successfully',
            'status': order.status
        })

class KitchenDisplayViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = KitchenDisplaySerializer
    permission_classes = [IsAuthenticated, CanViewKitchenDisplay]
    
    def get_queryset(self):
        # Get items that need kitchen attention
        queryset = KitchenDisplayItem.objects.filter(
            order_item__status__in=['pending', 'preparing']
        ).select_related(
            'order_item__table_order__table',
            'order_item__table_order__waiter',
            'order_item__menu_item'
        ).order_by('-is_priority', 'display_time')
        
        # Filter by table if specified
        table_number = self.request.query_params.get('table', None)
        if table_number:
            queryset = queryset.filter(
                order_item__table_order__table__table_number=table_number
            )
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(order_item__status=status_filter)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update order item status from kitchen"""
        kitchen_item = self.get_object()
        new_status = request.data.get('status')
        
        valid_statuses = ['preparing', 'ready', 'served']
        if new_status not in valid_statuses:
            return Response({
                'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        order_item = kitchen_item.order_item
        old_status = order_item.status
        
        if new_status == 'preparing':
            order_item.mark_preparing()
        elif new_status == 'ready':
            order_item.mark_ready()
        elif new_status == 'served':
            order_item.mark_served()
        
        return Response({
            'message': f'Status updated from {old_status} to {new_status}',
            'status': order_item.status,
            'table_number': kitchen_item.table_number,
            'order_number': kitchen_item.order_number
        })
    
    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """Update multiple items status"""
        item_updates = request.data.get('updates', [])
        
        if not item_updates:
            return Response({
                'error': 'No updates provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        updated_count = 0
        errors = []
        
        for update in item_updates:
            try:
                kitchen_item = KitchenDisplayItem.objects.get(id=update['id'])
                new_status = update['status']
                
                if new_status in ['preparing', 'ready', 'served']:
                    order_item = kitchen_item.order_item
                    if new_status == 'preparing':
                        order_item.mark_preparing()
                    elif new_status == 'ready':
                        order_item.mark_ready()
                    elif new_status == 'served':
                        order_item.mark_served()
                    updated_count += 1
                else:
                    errors.append({
                        'id': update['id'],
                        'error': 'Invalid status'
                    })
                    
            except KitchenDisplayItem.DoesNotExist:
                errors.append({
                    'id': update.get('id', 'unknown'),
                    'error': 'Kitchen display item not found'
                })
            except Exception as e:
                errors.append({
                    'id': update.get('id', 'unknown'),
                    'error': str(e)
                })
        
        response_data = {
            'message': f'{updated_count} items updated successfully',
            'updated_count': updated_count
        }
        
        if errors:
            response_data['errors'] = errors
        
        return Response(response_data)
    
    @action(detail=True, methods=['post'])
    def set_priority(self, request, pk=None):
        """Set priority status for kitchen item"""
        kitchen_item = self.get_object()
        is_priority = request.data.get('is_priority', False)
        
        kitchen_item.is_priority = is_priority
        kitchen_item.save()
        
        return Response({
            'message': f'Priority {"set" if is_priority else "removed"}',
            'is_priority': kitchen_item.is_priority
        })
    
    @action(detail=False, methods=['get'])
    def kitchen_summary(self, request):
        """Get kitchen dashboard summary"""
        queryset = self.get_queryset()
        
        total_items = queryset.count()
        pending_items = queryset.filter(order_item__status='pending').count()
        preparing_items = queryset.filter(order_item__status='preparing').count()
        priority_items = queryset.filter(is_priority=True).count()
        overdue_items = len([item for item in queryset if item.is_overdue])
        
        return Response({
            'total_items': total_items,
            'pending_items': pending_items,
            'preparing_items': preparing_items,
            'priority_items': priority_items,
            'overdue_items': overdue_items
        })
