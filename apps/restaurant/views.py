# apps/restaurant/views.py - Complete Enhanced Views with All ViewSets
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Q, Avg, F
from django.db.models.functions import TruncHour, TruncDate
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import json
import csv

from .models import (
    Table, MenuCategory, MenuItem, Order, OrderSession, 
    KitchenDisplaySettings, OfflineOrderBackup
)
from .serializers import (
    TableSerializer, TableWithOrdersSerializer, MenuCategorySerializer,
    MenuItemSerializer, MenuItemCreateSerializer, OrderSerializer,
    OrderCreateSerializer, OrderKDSSerializer, OrderStatusUpdateSerializer,
    BulkOrderCreateSerializer, OrderSessionSerializer, OrderSessionCreateSerializer,
    KitchenDisplaySettingsSerializer, OrderAnalyticsSerializer, 
    TableAnalyticsSerializer, AdminBillSerializer
)
from .utils import (
    broadcast_order_update, broadcast_table_update, is_kds_connected,
    create_order_backup, process_offline_orders, generate_receipt_data,
    get_system_health, validate_table_operations, get_order_status_history
)

logger = logging.getLogger(__name__)

class MenuCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for menu categories"""
    queryset = MenuCategory.objects.filter(is_active=True)
    serializer_class = MenuCategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = MenuCategory.objects.filter(is_active=True)
        return queryset.order_by('display_order', 'name')

    def perform_destroy(self, instance):
        """Soft delete - mark as inactive"""
        instance.is_active = False
        instance.save()

class MenuItemViewSet(viewsets.ModelViewSet):
    """ViewSet for menu items"""
    queryset = MenuItem.objects.filter(is_active=True)
    serializer_class = MenuItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = MenuItem.objects.filter(is_active=True).select_related('category')
        
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
            
        availability = self.request.query_params.get('availability')
        if availability:
            queryset = queryset.filter(availability=availability)
            
        return queryset.order_by('category__display_order', 'display_order', 'name')

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return MenuItemCreateSerializer
        return MenuItemSerializer

    def perform_destroy(self, instance):
        """Soft delete - mark as inactive"""
        instance.is_active = False
        instance.save()

class TableViewSet(viewsets.ModelViewSet):
    """Enhanced ViewSet for table management with complete CRUD"""
    queryset = Table.objects.filter(is_active=True)
    serializer_class = TableSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Table.objects.filter(is_active=True)

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by availability
        available_only = self.request.query_params.get('available_only')
        if available_only == 'true':
            queryset = queryset.filter(status='free')

        # Filter by location
        location = self.request.query_params.get('location')
        if location:
            queryset = queryset.filter(location__icontains=location)

        return queryset.order_by('table_number')

    def get_serializer_class(self):
        if self.action == 'with_orders':
            return TableWithOrdersSerializer
        return TableSerializer

    def perform_create(self, serializer):
        """Set created_by when creating table"""
        serializer.save(created_by=self.request.user)

    def perform_destroy(self, instance):
        """Soft delete - mark as inactive instead of deleting"""
        from rest_framework.exceptions import ValidationError
        
        if instance.status == 'occupied':
            raise ValidationError("Cannot delete occupied table")
        if instance.get_active_orders().exists():
            raise ValidationError("Cannot delete table with active orders")
        
        instance.is_active = False
        instance.save()

    @action(detail=False, methods=['get'])
    def with_orders(self, request):
        """Get tables with their order details and enhanced info"""
        tables = self.get_queryset().prefetch_related(
            'orders__menu_item',
            'orders__created_by',
            'order_sessions'
        )
        
        # Add calculated fields
        for table in tables:
            table.active_orders = table.get_active_orders()
            table.active_orders_count = table.active_orders.count()
            table.total_bill_amount = table.get_total_bill_amount()
            table.time_occupied = table.get_occupancy_duration()
            
            # Get active session info
            active_session = table.order_sessions.filter(is_active=True).first()
            if active_session:
                table.session_id = active_session.session_id
                table.can_bill = True
            else:
                table.can_bill = False

        serializer = TableWithOrdersSerializer(tables, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """Change table status with validation"""
        table = self.get_object()
        new_status = request.data.get('status')

        if not new_status or new_status not in dict(Table.STATUS_CHOICES):
            return Response(
                {'error': 'Invalid status'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validation rules
        if table.status == 'occupied' and new_status == 'free':
            if table.get_active_orders().exists():
                return Response(
                    {'error': 'Cannot free table with active orders. Complete billing first.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        old_status = table.status
        table.status = new_status
        
        # Set appropriate timestamps
        if new_status == 'occupied':
            table.last_occupied_at = timezone.now()
        elif new_status == 'free':
            table.last_billed_at = timezone.now()
            
        table.save()

        # Broadcast update
        broadcast_table_update(table, old_status)

        serializer = self.get_serializer(table)
        return Response({
            'message': f'Table status updated to {new_status}',
            'table': serializer.data
        })

    @action(detail=True, methods=['get'])
    def current_bill(self, request, pk=None):
        """Get current bill for table with enhanced details"""
        table = self.get_object()

        # Get or create active session
        session = table.order_sessions.filter(is_active=True).first()
        if not session:
            session = OrderSession.objects.create(
                table=table,
                created_by=request.user
            )

        # Calculate totals
        session.calculate_totals()

        # Add order details
        orders = session.get_session_orders()
        
        response_data = OrderSessionSerializer(session).data
        response_data['orders'] = OrderSerializer(orders, many=True, context={'request': request}).data
        response_data['order_count'] = orders.count()

        return Response(response_data)

    @action(detail=True, methods=['post'])
    def complete_billing(self, request, pk=None):
        """Complete billing with enhanced admin features"""
        table = self.get_object()

        # Get active session
        session = table.order_sessions.filter(is_active=True).first()
        if not session:
            return Response(
                {'error': 'No active session found'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Apply discounts and adjustments
        discount_amount = request.data.get('discount_amount', session.discount_amount)
        discount_percentage = request.data.get('discount_percentage', session.discount_percentage)
        service_charge = request.data.get('service_charge', session.service_charge)
        payment_method = request.data.get('payment_method', session.payment_method)
        notes = request.data.get('notes', session.notes)
        admin_notes = request.data.get('admin_notes', session.admin_notes)

        # Update session
        session.discount_amount = Decimal(str(discount_amount))
        session.discount_percentage = Decimal(str(discount_percentage))
        session.service_charge = Decimal(str(service_charge))
        session.payment_method = payment_method
        session.notes = notes
        session.admin_notes = admin_notes
        
        # Recalculate totals
        session.calculate_totals()
        session.complete_session(request.user)

        # Broadcast table status update
        broadcast_table_update(table, 'occupied')

        return Response({
            'message': 'Billing completed successfully',
            'receipt_number': session.receipt_number,
            'final_amount': float(session.final_amount),
            'table_status': table.status,
            'session_data': OrderSessionSerializer(session).data
        })

    @action(detail=True, methods=['post'])
    def print_bill(self, request, pk=None):
        """Mark bill as printed and return print-ready data"""
        table = self.get_object()
        
        session = table.order_sessions.filter(is_active=True).first()
        if not session:
            # Try to get the most recent completed session
            session = table.order_sessions.filter(is_active=False).first()
            
        if not session:
            return Response(
                {'error': 'No billing session found'},
                status=status.HTTP_400_BAD_REQUEST
            )

        session.print_bill()
        
        # Prepare bill data for printing
        bill_data = generate_receipt_data(session)

        return Response({
            'message': 'Bill data prepared for printing',
            'bill_data': bill_data,
            'printed_at': session.printed_at
        })

class OrderViewSet(viewsets.ModelViewSet):
    """Enhanced ViewSet for order management"""
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Order.objects.select_related(
            'table', 'menu_item', 'menu_item__category', 'created_by'
        ).all()

        # Existing filters...
        table = self.request.query_params.get('table')
        if table:
            queryset = queryset.filter(table_id=table)

        order_status = self.request.query_params.get('status')
        if order_status:
            queryset = queryset.filter(status=order_status)

        # Enhanced filters
        source = self.request.query_params.get('source')
        if source:
            queryset = queryset.filter(source=source)

        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)

        # Filter active orders only
        active_only = self.request.query_params.get('active_only')
        if active_only == 'true':
            queryset = queryset.filter(status__in=['pending', 'confirmed', 'preparing', 'ready'])

        return queryset.order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        elif self.action == 'kds_view':
            return OrderKDSSerializer
        return OrderSerializer

    def perform_create(self, serializer):
        """Enhanced order creation with offline backup"""
        order = serializer.save(created_by=self.request.user)
        
        # Check if KDS is connected, create backup if not
        if not is_kds_connected():
            create_order_backup(order)

    @action(detail=False, methods=['get'])
    def kds_view(self, request):
        """Get orders optimized for Kitchen Display System"""
        orders = Order.objects.select_related(
            'table', 'menu_item', 'menu_item__category', 'created_by'
        ).filter(
            status__in=['pending', 'confirmed', 'preparing', 'ready']
        ).order_by('created_at')

        serializer = OrderKDSSerializer(orders, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        """Update order status"""
        order = self.get_object()
        serializer = OrderStatusUpdateSerializer(order, data=request.data, partial=True)

        if serializer.is_valid():
            new_status = serializer.validated_data['status']
            old_status = order.status

            # Update status with user tracking
            order.update_status(new_status, request.user)

            # Broadcast update
            broadcast_order_update(order, old_status)

            response_serializer = self.get_serializer(order)
            return Response(response_serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='orders/bulk-create')
    def bulk_create_for_table(self, request, pk=None):
        """
        Bulk-create orders for a specific table (pk).
        Expects only `orders` in request.data.
        """
        table = Table.objects.get(pk=pk)
        data = {
            'table': table.id,
            'orders': request.data.get('orders', [])
                 }
        serializer = BulkOrderCreateSerializer(data=data, context={'request': request})
        if not serializer.is_valid():
            return Response({'error': serializer.errors}, status=400)
        orders = serializer.save()
        return Response(OrderSerializer(orders, many=True, context={'request': request}).data, status=201)

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Create multiple orders with enhanced features"""
        serializer = BulkOrderCreateSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            orders = serializer.save()

            # Handle offline backup for bulk orders
            kds_connected = is_kds_connected()
            
            for order in orders:
                if kds_connected:
                    broadcast_order_update(order, None)
                else:
                    create_order_backup(order)

            response_serializer = OrderSerializer(orders, many=True, context={'request': request})
            return Response({
                'message': f'{len(orders)} orders created successfully',
                'orders': response_serializer.data,
                'kds_status': 'connected' if kds_connected else 'offline'
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def process_offline_orders(self, request):
        """Process orders that were created when KDS was offline"""
        try:
            processed_count = process_offline_orders()
            return Response({
                'message': f'Processed {processed_count} offline orders',
                'processed_count': processed_count
            })
        except Exception as e:
            logger.error(f"Error processing offline orders: {e}")
            return Response(
                {'error': 'Failed to process offline orders'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class OrderSessionViewSet(viewsets.ModelViewSet):
    """ViewSet for order sessions"""
    queryset = OrderSession.objects.all()
    serializer_class = OrderSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = OrderSession.objects.select_related('table', 'created_by', 'billed_by')
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
            
        # Filter by table
        table = self.request.query_params.get('table')
        if table:
            queryset = queryset.filter(table_id=table)
            
        return queryset.order_by('-created_at')

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return OrderSessionCreateSerializer
        return OrderSessionSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class KitchenDisplaySettingsViewSet(viewsets.ModelViewSet):
    """ViewSet for kitchen display settings"""
    queryset = KitchenDisplaySettings.objects.all()
    serializer_class = KitchenDisplaySettingsSerializer
    permission_classes = [IsAuthenticated]

# New Admin Billing ViewSet
class AdminBillingViewSet(viewsets.ViewSet):
    """Admin billing functionality"""
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """Only admin and managers can access admin billing"""
        if hasattr(self.request, 'user') and self.request.user.is_authenticated:
            if self.request.user.role not in ['admin', 'manager']:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('Access denied: Admin or Manager role required')
        return super().get_permissions()

    @action(detail=False, methods=['get'])
    def active_sessions(self, request):
        """Get all active billing sessions"""
        sessions = OrderSession.objects.filter(is_active=True).select_related(
            'table', 'created_by'
        ).prefetch_related('table__orders')
        
        session_data = []
        for session in sessions:
            orders = session.get_session_orders()
            session_info = OrderSessionSerializer(session).data
            session_info['orders'] = OrderSerializer(orders, many=True, context={'request': request}).data
            session_info['order_count'] = orders.count()
            session_data.append(session_info)
        
        return Response(session_data)

    @action(detail=False, methods=['post'])
    def modify_bill(self, request):
        """Admin functionality to modify existing bills"""
        session_id = request.data.get('session_id')
        modifications = request.data.get('modifications', {})
        
        try:
            if session_id:
                session = OrderSession.objects.get(session_id=session_id)
            else:
                return Response(
                    {'error': 'Session ID required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Apply modifications
            if 'discount_amount' in modifications:
                session.discount_amount = Decimal(str(modifications['discount_amount']))
            
            if 'discount_percentage' in modifications:
                session.discount_percentage = Decimal(str(modifications['discount_percentage']))
                
            if 'service_charge' in modifications:
                session.service_charge = Decimal(str(modifications['service_charge']))
                
            if 'admin_notes' in modifications:
                session.admin_notes = modifications['admin_notes']

            # Recalculate totals
            session.calculate_totals()
            
            return Response({
                'message': 'Bill modified successfully',
                'session': OrderSessionSerializer(session).data
            })

        except OrderSession.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error modifying bill: {e}")
            return Response(
                {'error': 'Failed to modify bill'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def void_bill(self, request):
        """Admin functionality to void bills"""
        session_id = request.data.get('session_id')
        reason = request.data.get('reason', '')
        
        try:
            session = OrderSession.objects.get(session_id=session_id)
            
            # Mark as cancelled
            session.payment_status = 'cancelled'
            session.admin_notes = f"VOIDED by {request.user.get_full_name()}: {reason}"
            session.is_active = False
            session.completed_at = timezone.now()
            session.save()
            
            # Free the table
            session.table.mark_free()
            
            return Response({
                'message': 'Bill voided successfully',
                'receipt_number': session.receipt_number
            })
            
        except OrderSession.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def billing_reports(self, request):
        """Generate billing reports for admin"""
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        if not date_from:
            date_from = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            date_from = datetime.fromisoformat(date_from)
            
        if not date_to:
            date_to = timezone.now()
        else:
            date_to = datetime.fromisoformat(date_to)

        sessions = OrderSession.objects.filter(
            created_at__range=[date_from, date_to],
            is_active=False
        )

        # Calculate totals
        totals = sessions.aggregate(
            total_revenue=Sum('final_amount'),
            total_discount=Sum('discount_amount'),
            total_tax=Sum('tax_amount'),
            session_count=Count('id')
        )

        # Payment method breakdown
        payment_breakdown = sessions.values('payment_method').annotate(
            count=Count('id'),
            amount=Sum('final_amount')
        )

        # Daily breakdown
        daily_breakdown = sessions.extra({
            'date': "DATE(created_at)"
        }).values('date').annotate(
            session_count=Count('id'),
            revenue=Sum('final_amount')
        ).order_by('date')

        return Response({
            'date_range': {
                'from': date_from.isoformat(),
                'to': date_to.isoformat()
            },
            'summary': {
                'total_sessions': totals['session_count'] or 0,
                'total_revenue': float(totals['total_revenue'] or 0),
                'total_discount': float(totals['total_discount'] or 0),
                'total_tax': float(totals['total_tax'] or 0),
                'average_bill': float(totals['total_revenue'] or 0) / max(totals['session_count'] or 1, 1)
            },
            'payment_breakdown': list(payment_breakdown),
            'daily_breakdown': list(daily_breakdown)
        })

# Enhanced API endpoints
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """Enhanced dashboard statistics"""
    try:
        # Current date stats
        today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Order stats
        todays_orders = Order.objects.filter(created_at__gte=today)
        pending_orders = todays_orders.filter(status='pending').count()
        preparing_orders = todays_orders.filter(status='preparing').count()
        ready_orders = todays_orders.filter(status='ready').count()

        # Table stats
        occupied_tables = Table.objects.filter(status='occupied', is_active=True).count()
        free_tables = Table.objects.filter(status='free', is_active=True).count()
        total_tables = Table.objects.filter(is_active=True).count()

        # Revenue stats
        todays_sessions = OrderSession.objects.filter(
            completed_at__gte=today,
            is_active=False
        )
        
        todays_revenue = todays_sessions.aggregate(
            total=Sum('final_amount')
        )['total'] or Decimal('0.00')

        # Active sessions
        active_sessions = OrderSession.objects.filter(is_active=True).count()

        # System status
        kds_connected = is_kds_connected()
        offline_orders = OfflineOrderBackup.objects.filter(is_processed=False).count()

        stats = {
            'orders': {
                'total_today': todays_orders.count(),
                'pending': pending_orders,
                'preparing': preparing_orders,
                'ready': ready_orders
            },
            'tables': {
                'occupied': occupied_tables,
                'free': free_tables,
                'total': total_tables,
                'occupancy_rate': (occupied_tables / total_tables * 100) if total_tables > 0 else 0
            },
            'revenue': {
                'today': float(todays_revenue),
                'session_count': todays_sessions.count()
            },
            'sessions': {
                'active': active_sessions
            },
            'system': {
                'kds_connected': kds_connected,
                'offline_orders': offline_orders
            },
            'timestamp': timezone.now().isoformat()
        }

        return Response(stats)

    except Exception as e:
        logger.error(f"Error generating dashboard stats: {e}")
        return Response(
            {'error': 'Failed to generate dashboard stats'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def system_health(request):
    """Get system health status"""
    health_data = get_system_health()
    return Response(health_data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def menu_for_ordering(request):
    """Get menu optimized for ordering interface"""
    categories = MenuCategory.objects.filter(is_active=True).prefetch_related('items')
    menu_data = []
    
    for category in categories:
        available_items = category.items.filter(
            is_active=True, 
            availability='available'
        ).order_by('display_order', 'name')
        
        if available_items.exists():
            menu_data.append({
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'icon': category.icon,
                'items': MenuItemSerializer(available_items, many=True).data
            })
    
    return Response(menu_data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def quick_order(request):
    """Create a quick order"""
    try:
        table_id = request.data.get('table_id')
        menu_item_id = request.data.get('menu_item_id')
        quantity = request.data.get('quantity', 1)
        special_instructions = request.data.get('special_instructions', '')

        table = Table.objects.get(id=table_id, is_active=True)
        menu_item = MenuItem.objects.get(id=menu_item_id, is_active=True)

        order = Order.objects.create(
            table=table,
            menu_item=menu_item,
            quantity=quantity,
            special_instructions=special_instructions,
            created_by=request.user
        )

        # Broadcast the order
        if is_kds_connected():
            broadcast_order_update(order, None)
        else:
            create_order_backup(order)

        return Response(
            OrderSerializer(order, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

    except (Table.DoesNotExist, MenuItem.DoesNotExist):
        return Response(
            {'error': 'Invalid table or menu item'},
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def table_orders(request, table_id):
    """Get all orders for a specific table"""
    try:
        table = Table.objects.get(id=table_id, is_active=True)
        orders = table.orders.all().order_by('-created_at')
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            orders = orders.filter(status=status_filter)
        
        serializer = OrderSerializer(orders, many=True, context={'request': request})
        return Response({
            'table': TableSerializer(table).data,
            'orders': serializer.data,
            'total_orders': orders.count()
        })
        
    except Table.DoesNotExist:
        return Response(
            {'error': 'Table not found'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def table_session(request, table_id):
    """Get or create table session"""
    try:
        table = Table.objects.get(id=table_id, is_active=True)
        
        if request.method == 'GET':
            session = table.order_sessions.filter(is_active=True).first()
            if session:
                return Response(OrderSessionSerializer(session).data)
            else:
                return Response({'message': 'No active session'})
        
        elif request.method == 'POST':
            # Create new session
            session = OrderSession.objects.create(
                table=table,
                created_by=request.user
            )
            return Response(
                OrderSessionSerializer(session).data,
                status=status.HTTP_201_CREATED
            )
            
    except Table.DoesNotExist:
        return Response(
            {'error': 'Table not found'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def kds_connection_status(request):
    """Get KDS connection status"""
    offline_orders_count = OfflineOrderBackup.objects.filter(is_processed=False).count()
    
    return Response({
        'connected': is_kds_connected(),
        'offline_orders_count': offline_orders_count,
        'timestamp': timezone.now().isoformat()
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def kds_heartbeat(request):
    """Update KDS heartbeat"""
    from .utils import update_kds_heartbeat
    update_kds_heartbeat()
    return Response({'message': 'Heartbeat updated'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def generate_receipt(request, session_id):
    """Generate receipt data"""
    try:
        session = OrderSession.objects.get(session_id=session_id)
        receipt_data = generate_receipt_data(session)
        
        if receipt_data:
            return Response(receipt_data)
        else:
            return Response(
                {'error': 'Failed to generate receipt'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except OrderSession.DoesNotExist:
        return Response(
            {'error': 'Session not found'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def print_receipt(request, session_id):
    """Mark receipt as printed"""
    try:
        session = OrderSession.objects.get(session_id=session_id)
        session.print_bill()
        
        return Response({
            'message': 'Receipt marked as printed',
            'printed_at': session.printed_at
        })
        
    except OrderSession.DoesNotExist:
        return Response(
            {'error': 'Session not found'},
            status=status.HTTP_404_NOT_FOUND
        )

# Export functions
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_orders_csv(request):
    """Export orders to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="orders.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Order Number', 'Table', 'Item', 'Quantity', 'Unit Price', 
        'Total Price', 'Status', 'Created At', 'Created By'
    ])
    
    orders = Order.objects.select_related(
        'table', 'menu_item', 'created_by'
    ).order_by('-created_at')
    
    for order in orders:
        writer.writerow([
            order.order_number,
            order.table.table_number,
            order.menu_item.name,
            order.quantity,
            float(order.unit_price),
            float(order.total_price),
            order.status,
            order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            order.created_by.get_full_name() if order.created_by else 'System'
        ])
    
    return response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_sessions_csv(request):
    """Export sessions to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sessions.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Receipt Number', 'Table', 'Subtotal', 'Discount', 'Tax', 
        'Service Charge', 'Final Amount', 'Payment Method', 
        'Created At', 'Completed At', 'Created By'
    ])
    
    sessions = OrderSession.objects.select_related(
        'table', 'created_by'
    ).order_by('-created_at')
    
    for session in sessions:
        writer.writerow([
            session.receipt_number,
            session.table.table_number,
            float(session.subtotal_amount),
            float(session.discount_amount),
            float(session.tax_amount),
            float(session.service_charge),
            float(session.final_amount),
            session.payment_method,
            session.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            session.completed_at.strftime('%Y-%m-%d %H:%M:%S') if session.completed_at else '',
            session.created_by.get_full_name() if session.created_by else 'System'
        ])
    
    return response

# Mobile ordering endpoints
@api_view(['GET'])
def mobile_available_tables(request):
    """Get available tables for mobile ordering"""
    tables = Table.objects.filter(
        is_active=True,
        status__in=['free', 'occupied']  # Allow ordering to occupied tables
    ).order_by('table_number')
    
    return Response(TableSerializer(tables, many=True).data)

@api_view(['GET'])
def mobile_menu(request):
    """Get menu for mobile ordering"""
    return menu_for_ordering(request)

@api_view(['POST'])
def mobile_create_order(request):
    """Create order from mobile interface"""
    try:
        serializer = OrderCreateSerializer(data=request.data)
        if serializer.is_valid():
            # Set source as mobile
            order = serializer.save(
                created_by=request.user if request.user.is_authenticated else None,
                source='mobile'
            )
            
            # Handle offline KDS
            if is_kds_connected():
                broadcast_order_update(order, None)
            else:
                create_order_backup(order)
            
            return Response(
                OrderSerializer(order).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Error creating mobile order: {e}")
        return Response(
            {'error': 'Failed to create order'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
def mobile_order_status(request, order_number):
    """Get order status for mobile"""
    try:
        order = Order.objects.get(order_number=order_number)
        return Response({
            'order': OrderSerializer(order).data,
            'estimated_time': order.preparation_time_remaining,
            'status_history': get_order_status_history(order)
        })
        
    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found'},
            status=status.HTTP_404_NOT_FOUND
        )

# Additional API views to add to apps/restaurant/views.py
# Add these functions at the end of your views.py file, before the mobile ordering endpoints

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_update_tables(request):
    """Bulk update table statuses"""
    try:
        updates = request.data.get('updates', [])
        updated_tables = []
        
        for update in updates:
            table_id = update.get('table_id')
            new_status = update.get('status')
            
            try:
                table = Table.objects.get(id=table_id, is_active=True)
                
                # Validate status change
                is_valid, message = validate_table_operations(table, new_status)
                
                if is_valid:
                    old_status = table.status
                    table.status = new_status
                    table.save()
                    
                    broadcast_table_update(table, old_status)
                    updated_tables.append(table.table_number)
                    
            except Table.DoesNotExist:
                continue
        
        return Response({
            'message': f'Updated {len(updated_tables)} tables',
            'updated_tables': updated_tables
        })
        
    except Exception as e:
        logger.error(f"Error in bulk table update: {e}")
        return Response(
            {'error': 'Failed to update tables'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_order_status_update(request):
    """Bulk update order statuses"""
    try:
        order_ids = request.data.get('order_ids', [])
        new_status = request.data.get('status')
        
        if not new_status or new_status not in dict(Order.STATUS_CHOICES):
            return Response(
                {'error': 'Invalid status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        updated_orders = []
        for order_id in order_ids:
            try:
                order = Order.objects.get(id=order_id)
                old_status = order.status
                order.update_status(new_status, request.user)
                updated_orders.append(order.order_number)
                
            except Order.DoesNotExist:
                continue
        
        return Response({
            'message': f'Updated {len(updated_orders)} orders',
            'updated_orders': updated_orders
        })
        
    except Exception as e:
        logger.error(f"Error in bulk order status update: {e}")
        return Response(
            {'error': 'Failed to update orders'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def orders_by_table(request, table_id):
    """Get orders by table ID"""
    try:
        table = Table.objects.get(id=table_id, is_active=True)
        orders = table.orders.all().order_by('-created_at')
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            orders = orders.filter(status=status_filter)
        
        serializer = OrderSerializer(orders, many=True, context={'request': request})
        return Response({
            'table': TableSerializer(table).data,
            'orders': serializer.data,
            'total_orders': orders.count()
        })
        
    except Table.DoesNotExist:
        return Response(
            {'error': 'Table not found'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_status_history(request, order_id):
    """Get order status history"""
    try:
        order = Order.objects.get(id=order_id)
        history = get_order_status_history(order)
        
        return Response({
            'order': OrderSerializer(order, context={'request': request}).data,
            'status_history': history
        })
        
    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_offline_orders(request):
    """Process orders that were created when KDS was offline"""
    try:
        processed_count = process_offline_orders()
        return Response({
            'message': f'Processed {processed_count} offline orders',
            'processed_count': processed_count
        })
    except Exception as e:
        logger.error(f"Error processing offline orders: {e}")
        return Response(
            {'error': 'Failed to process offline orders'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def void_session(request, session_id):
    """Void a billing session"""
    try:
        session = OrderSession.objects.get(session_id=session_id)
        reason = request.data.get('reason', 'Admin void')
        
        # Mark as voided
        session.payment_status = 'cancelled'
        session.admin_notes = f"VOIDED by {request.user.get_full_name()}: {reason}"
        session.is_active = False
        session.completed_at = timezone.now()
        session.save()
        
        # Free the table
        session.table.mark_free()
        
        return Response({
            'message': 'Session voided successfully',
            'receipt_number': session.receipt_number
        })
        
    except OrderSession.DoesNotExist:
        return Response(
            {'error': 'Session not found'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_table_analytics(request):
    """Get table analytics for admin"""
    try:
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        if not date_from:
            date_from = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            date_from = datetime.fromisoformat(date_from)
            
        if not date_to:
            date_to = timezone.now()
        else:
            date_to = datetime.fromisoformat(date_to)

        # Get table utilization stats
        sessions = OrderSession.objects.filter(
            created_at__range=[date_from, date_to]
        ).select_related('table')

        table_stats = {}
        for session in sessions:
            table_number = session.table.table_number
            if table_number not in table_stats:
                table_stats[table_number] = {
                    'sessions': 0,
                    'revenue': 0.0,
                    'avg_session_time': 0
                }
            
            table_stats[table_number]['sessions'] += 1
            table_stats[table_number]['revenue'] += float(session.final_amount)
            
            if session.completed_at:
                session_time = (session.completed_at - session.created_at).total_seconds() / 60
                table_stats[table_number]['avg_session_time'] += session_time

        # Calculate averages
        for table_data in table_stats.values():
            if table_data['sessions'] > 0:
                table_data['avg_session_time'] /= table_data['sessions']

        return Response({
            'date_range': {
                'from': date_from.isoformat(),
                'to': date_to.isoformat()
            },
            'table_stats': table_stats,
            'total_tables': len(table_stats),
            'total_sessions': sessions.count()
        })

    except Exception as e:
        logger.error(f"Error generating table analytics: {e}")
        return Response(
            {'error': 'Failed to generate analytics'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_order_analytics(request):
    """Get order analytics for admin"""
    try:
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        if not date_from:
            date_from = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            date_from = datetime.fromisoformat(date_from)
            
        if not date_to:
            date_to = timezone.now()
        else:
            date_to = datetime.fromisoformat(date_to)

        orders = Order.objects.filter(
            created_at__range=[date_from, date_to]
        ).select_related('menu_item', 'menu_item__category')

        # Status breakdown
        status_breakdown = orders.values('status').annotate(
            count=Count('id'),
            revenue=Sum('total_price')
        )

        # Category breakdown
        category_breakdown = orders.values(
            'menu_item__category__name'
        ).annotate(
            count=Count('id'),
            revenue=Sum('total_price')
        )

        # Most popular items
        popular_items = orders.values(
            'menu_item__name'
        ).annotate(
            count=Count('id'),
            revenue=Sum('total_price')
        ).order_by('-count')[:10]

        return Response({
            'date_range': {
                'from': date_from.isoformat(),
                'to': date_to.isoformat()
            },
            'total_orders': orders.count(),
            'total_revenue': float(orders.aggregate(Sum('total_price'))['total_price__sum'] or 0),
            'status_breakdown': list(status_breakdown),
            'category_breakdown': list(category_breakdown),
            'popular_items': list(popular_items)
        })

    except Exception as e:
        logger.error(f"Error generating order analytics: {e}")
        return Response(
            {'error': 'Failed to generate analytics'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_billing_reports(request):
    """Generate comprehensive billing reports"""
    try:
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        if not date_from:
            date_from = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            date_from = datetime.fromisoformat(date_from)
            
        if not date_to:
            date_to = timezone.now()
        else:
            date_to = datetime.fromisoformat(date_to)

        sessions = OrderSession.objects.filter(
            created_at__range=[date_from, date_to],
            is_active=False
        )

        # Calculate comprehensive totals
        totals = sessions.aggregate(
            total_revenue=Sum('final_amount'),
            total_discount=Sum('discount_amount'),
            total_tax=Sum('tax_amount'),
            total_service_charge=Sum('service_charge'),
            session_count=Count('id'),
            avg_bill=Avg('final_amount')
        )

        # Payment method breakdown
        payment_breakdown = sessions.values('payment_method').annotate(
            count=Count('id'),
            amount=Sum('final_amount')
        )

        # Hourly breakdown
        hourly_breakdown = sessions.extra({
            'hour': "EXTRACT(hour FROM created_at)"
        }).values('hour').annotate(
            session_count=Count('id'),
            revenue=Sum('final_amount')
        ).order_by('hour')

        # Daily breakdown
        daily_breakdown = sessions.extra({
            'date': "DATE(created_at)"
        }).values('date').annotate(
            session_count=Count('id'),
            revenue=Sum('final_amount')
        ).order_by('date')

        return Response({
            'date_range': {
                'from': date_from.isoformat(),
                'to': date_to.isoformat()
            },
            'summary': {
                'total_sessions': totals['session_count'] or 0,
                'total_revenue': float(totals['total_revenue'] or 0),
                'total_discount': float(totals['total_discount'] or 0),
                'total_tax': float(totals['total_tax'] or 0),
                'total_service_charge': float(totals['total_service_charge'] or 0),
                'average_bill': float(totals['avg_bill'] or 0)
            },
            'payment_breakdown': list(payment_breakdown),
            'hourly_breakdown': list(hourly_breakdown),
            'daily_breakdown': list(daily_breakdown)
        })

    except Exception as e:
        logger.error(f"Error generating billing reports: {e}")
        return Response(
            {'error': 'Failed to generate reports'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_system_cleanup(request):
    """Admin system cleanup operations"""
    try:
        from .utils import cleanup_old_data
        
        # Perform cleanup
        cleanup_old_data()
        
        return Response({
            'message': 'System cleanup completed successfully'
        })

    except Exception as e:
        logger.error(f"Error during system cleanup: {e}")
        return Response(
            {'error': 'System cleanup failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def daily_sales_report(request):
    """Generate daily sales report"""
    try:
        date = request.query_params.get('date')
        if not date:
            date = timezone.now().date()
        else:
            date = datetime.fromisoformat(date).date()

        start_of_day = datetime.combine(date, datetime.min.time())
        end_of_day = datetime.combine(date, datetime.max.time())

        sessions = OrderSession.objects.filter(
            created_at__range=[start_of_day, end_of_day],
            is_active=False
        )

        # Calculate daily totals
        totals = sessions.aggregate(
            total_revenue=Sum('final_amount'),
            total_sessions=Count('id'),
            avg_bill=Avg('final_amount')
        )

        # Hourly breakdown
        hourly_sales = sessions.extra({
            'hour': "EXTRACT(hour FROM created_at)"
        }).values('hour').annotate(
            revenue=Sum('final_amount'),
            session_count=Count('id')
        ).order_by('hour')

        return Response({
            'date': date.isoformat(),
            'summary': {
                'total_revenue': float(totals['total_revenue'] or 0),
                'total_sessions': totals['total_sessions'] or 0,
                'average_bill': float(totals['avg_bill'] or 0)
            },
            'hourly_breakdown': list(hourly_sales)
        })

    except Exception as e:
        logger.error(f"Error generating daily sales report: {e}")
        return Response(
            {'error': 'Failed to generate report'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def table_utilization_report(request):
    """Generate table utilization report"""
    try:
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        if not date_from:
            date_from = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            date_from = datetime.fromisoformat(date_from)
            
        if not date_to:
            date_to = timezone.now()
        else:
            date_to = datetime.fromisoformat(date_to)

        # Get all tables with their usage stats
        tables = Table.objects.filter(is_active=True)
        utilization_data = []

        for table in tables:
            sessions = table.order_sessions.filter(
                created_at__range=[date_from, date_to]
            )

            total_sessions = sessions.count()
            total_revenue = sessions.aggregate(Sum('final_amount'))['final_amount__sum'] or 0
            
            # Calculate average session time
            completed_sessions = sessions.filter(completed_at__isnull=False)
            avg_session_time = 0
            if completed_sessions.exists():
                total_time = sum([
                    (session.completed_at - session.created_at).total_seconds() / 60
                    for session in completed_sessions
                ])
                avg_session_time = total_time / completed_sessions.count()

            utilization_data.append({
                'table_number': table.table_number,
                'capacity': table.capacity,
                'total_sessions': total_sessions,
                'total_revenue': float(total_revenue),
                'avg_session_time_minutes': round(avg_session_time, 2),
                'revenue_per_session': float(total_revenue / total_sessions) if total_sessions > 0 else 0
            })

        return Response({
            'date_range': {
                'from': date_from.isoformat(),
                'to': date_to.isoformat()
            },
            'tables': utilization_data
        })

    except Exception as e:
        logger.error(f"Error generating table utilization report: {e}")
        return Response(
            {'error': 'Failed to generate report'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def menu_performance_report(request):
    """Generate menu performance report"""
    try:
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        if not date_from:
            date_from = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            date_from = datetime.fromisoformat(date_from)
            
        if not date_to:
            date_to = timezone.now()
        else:
            date_to = datetime.fromisoformat(date_to)

        orders = Order.objects.filter(
            created_at__range=[date_from, date_to],
            status__in=['served', 'ready']  # Only completed orders
        ).select_related('menu_item', 'menu_item__category')

        # Item performance
        item_performance = orders.values(
            'menu_item__name',
            'menu_item__category__name'
        ).annotate(
            total_orders=Count('id'),
            total_quantity=Sum('quantity'),
            total_revenue=Sum('total_price'),
            avg_price=Avg('unit_price')
        ).order_by('-total_revenue')

        # Category performance
        category_performance = orders.values(
            'menu_item__category__name'
        ).annotate(
            total_orders=Count('id'),
            total_revenue=Sum('total_price')
        ).order_by('-total_revenue')

        return Response({
            'date_range': {
                'from': date_from.isoformat(),
                'to': date_to.isoformat()
            },
            'item_performance': list(item_performance),
            'category_performance': list(category_performance),
            'total_orders': orders.count(),
            'total_revenue': float(orders.aggregate(Sum('total_price'))['total_price__sum'] or 0)
        })

    except Exception as e:
        logger.error(f"Error generating menu performance report: {e}")
        return Response(
            {'error': 'Failed to generate report'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )        
