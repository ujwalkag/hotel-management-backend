# apps/tables/views.py - COMPLETE UPDATED VERSION
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
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
# FIXED: Import existing permission classes from the current permissions.py
from .permissions import (
    IsAdminOrStaff, 
    CanViewKitchenDisplay,
    CanAccessKitchen,
    CanGenerateBills,
    CanCreateOrders,
    IsKitchenStaffOrAdmin,
    IsManagerOrAdmin
)


class RestaurantTableViewSet(viewsets.ModelViewSet):
    """ViewSet for managing restaurant tables"""
    queryset = RestaurantTable.objects.all()
    serializer_class = RestaurantTableSerializer
    permission_classes = [IsAuthenticated, IsAdminOrStaff]

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

    @action(detail=True, methods=['post'])
    def create_order(self, request, pk=None):
        """Create a new order for this table"""
        table = self.get_object()

        # Check if table is already occupied
        if table.is_occupied and hasattr(table, 'current_order') and table.current_order:
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
    """ViewSet for managing table orders"""
    queryset = TableOrder.objects.all()
    permission_classes = [IsAuthenticated, IsAdminOrStaff]

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, CanAccessKitchen])
    def kitchen_display_live(self, request):
        """Real-time kitchen display data"""
        kitchen_items = KitchenDisplayItem.objects.filter(
            order_item__status__in=['pending', 'preparing']
        ).select_related(
            'order_item__table_order__table',
            'order_item__menu_item'
        ).order_by('-is_priority', 'display_time')

        serializer = KitchenDisplaySerializer(kitchen_items, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, CanGenerateBills])
    def biller_dashboard(self, request):
        """Get orders ready for billing grouped by table"""
        orders = TableOrder.objects.filter(
            status__in=['completed']
        ).select_related('table').prefetch_related('items')

        # Group by table
        orders_by_table = {}
        for order in orders:
            table_num = order.table.table_number
            if table_num not in orders_by_table:
                orders_by_table[table_num] = {
                    'table': RestaurantTableSerializer(order.table).data,
                    'orders': []
                }
            orders_by_table[table_num]['orders'].append(
                TableOrderSerializer(order).data
            )

        return Response(orders_by_table)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, CanCreateOrders])
    def waiter_orders(self, request):
        """Get orders for current waiter"""
        if hasattr(request.user, 'role') and request.user.role == 'waiter':
            orders = TableOrder.objects.filter(waiter=request.user)
        else:  # admin and staff can see all orders
            orders = TableOrder.objects.all()

        orders = orders.filter(
            status__in=['pending', 'in_progress', 'completed']
        ).order_by('-created_at')

        serializer = TableOrderSerializer(orders, many=True)
        return Response(serializer.data)

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return TableOrderCreateSerializer
        return TableOrderSerializer

    def get_queryset(self):
        """Filter and search orders"""
        queryset = TableOrder.objects.select_related(
            'table', 'waiter'
        ).prefetch_related('items__menu_item')

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
        """Set waiter when creating order"""
        serializer.save(waiter=self.request.user)

    @action(detail=True, methods=['post'])
    def add_items(self, request, pk=None):
        """Add items to existing order"""
        order = self.get_object()

        if order.status not in ['pending', 'in_progress']:
            return Response(
                {'error': 'Cannot add items to completed order'},
                status=status.HTTP_400_BAD_REQUEST
            )

        items_data = request.data.get('items', [])
        if not items_data:
            return Response(
                {'error': 'No items provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

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
            return Response(
                {'errors': errors}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Recalculate order total
        if hasattr(order, 'calculate_total'):
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
        pending_items = order.items.exclude(
            status__in=['served', 'cancelled']
        ).count()

        if pending_items > 0:
            return Response({
                'error': f'Cannot complete order with {pending_items} pending items'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Mark order as completed
        if hasattr(order, 'mark_completed'):
            order.mark_completed()
        else:
            order.status = 'completed'
            order.completed_at = timezone.now()
            order.save()

        return Response({
            'message': 'Order completed successfully',
            'status': order.status,
            'completed_at': order.completed_at if hasattr(order, 'completed_at') else timezone.now()
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
        try:
            from apps.bills.models import Bill, BillItem
        except ImportError:
            return Response({
                'error': 'Billing module not available'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
                item_name=order_item.menu_item.name_en if hasattr(order_item.menu_item, 'name_en') else str(order_item.menu_item),
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
        if hasattr(order.table, 'active_orders_count') and order.table.active_orders_count == 0:
            order.table.is_occupied = False
            order.table.save()

        return Response({
            'message': 'Order cancelled successfully',
            'status': order.status
        })


class KitchenDisplayViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for kitchen display functionality"""
    serializer_class = KitchenDisplaySerializer
    permission_classes = [IsAuthenticated, CanViewKitchenDisplay]

    def get_queryset(self):
        """Get items that need kitchen attention"""
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

        # Update status based on available methods or direct assignment
        if new_status == 'preparing':
            if hasattr(order_item, 'mark_preparing'):
                order_item.mark_preparing()
            else:
                order_item.status = 'preparing'
                order_item.save()
        elif new_status == 'ready':
            if hasattr(order_item, 'mark_ready'):
                order_item.mark_ready()
            else:
                order_item.status = 'ready'
                order_item.save()
        elif new_status == 'served':
            if hasattr(order_item, 'mark_served'):
                order_item.mark_served()
            else:
                order_item.status = 'served'
                order_item.save()

        return Response({
            'message': f'Status updated from {old_status} to {new_status}',
            'status': order_item.status,
            'table_number': kitchen_item.table_number if hasattr(kitchen_item, 'table_number') else 'N/A',
            'order_number': kitchen_item.order_number if hasattr(kitchen_item, 'order_number') else 'N/A'
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
                        if hasattr(order_item, 'mark_preparing'):
                            order_item.mark_preparing()
                        else:
                            order_item.status = 'preparing'
                            order_item.save()
                    elif new_status == 'ready':
                        if hasattr(order_item, 'mark_ready'):
                            order_item.mark_ready()
                        else:
                            order_item.status = 'ready'
                            order_item.save()
                    elif new_status == 'served':
                        if hasattr(order_item, 'mark_served'):
                            order_item.mark_served()
                        else:
                            order_item.status = 'served'
                            order_item.save()

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

        # Calculate overdue items (you may need to adjust this logic based on your models)
        overdue_items = 0
        try:
            overdue_items = len([item for item in queryset if hasattr(item, 'is_overdue') and item.is_overdue])
        except:
            # Fallback if is_overdue method doesn't exist
            overdue_items = 0

        return Response({
            'total_items': total_items,
            'pending_items': pending_items,
            'preparing_items': preparing_items,
            'priority_items': priority_items,
            'overdue_items': overdue_items
        })


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

