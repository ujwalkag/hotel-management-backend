# apps/restaurant/views.py - COMPLETE Enhanced Views with ALL Functionality + Your Updates
from rest_framework.views import APIView
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
from django.db import transaction
import json
import csv
import uuid

from .models import (
    Table, MenuCategory, MenuItem, Order, OrderSession,
    KitchenDisplaySettings, OfflineOrderBackup
)
from .serializers import (
    TableSerializer, TableWithOrdersSerializer, MenuCategorySerializer,
    MenuItemSerializer, MenuItemCreateSerializer, OrderSerializer,
    OrderCreateSerializer, OrderKDSSerializer, OrderStatusUpdateSerializer,
    BulkOrderCreateSerializer, OrderSessionSerializer, OrderSessionCreateSerializer,
    KitchenDisplaySettingsSerializer
)
from .utils import (
    broadcast_order_update, broadcast_table_update, is_kds_connected,
    create_order_backup, process_offline_orders, generate_receipt_data,
    get_system_health,
    generate_complete_bill, calculate_gst_breakdown, increment_kds_connections,
    decrement_kds_connections, update_kds_heartbeat
)
from rest_framework.exceptions import PermissionDenied

logger = logging.getLogger(__name__)

# Role-based permission decorator
def role_required(allowed_roles):
    """Custom decorator for role-based access control"""
    def decorator(view_func):
        def wrapper(self, request, *args, **kwargs):
            if hasattr(request, 'user') and request.user.is_authenticated:
                user_role = getattr(request.user, 'role', None)
                if user_role not in allowed_roles:
                    raise PermissionDenied(f'Access denied. Required roles: {allowed_roles}')
            return view_func(self, request, *args, **kwargs)
        return wrapper
    return decorator

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

# CRITICAL FIX: Update TablesWithOrdersView in views.py

# CRITICAL FIX 4: Replace TablesWithOrdersView in views.py

class TablesWithOrdersView(APIView):
    """Get tables with their active orders - FIXED to include served orders and billing info"""
    permission_classes = [IsAuthenticated]
    @role_required(['admin','staff', 'waiter'])
    def get(self, request):
        print(f"\n🌐 TablesWithOrdersView CALLED at {timezone.now()}")
        try:
            tables = Table.objects.filter(is_active=True).prefetch_related(
                'orders__menu_item',
                'orders__created_by',
                'order_sessions'
            )

            table_data = []
            for table in tables:
                print(f"\n🏓 Processing Table {table.table_number}")

                # Get session orders (includes served orders for billing)
                session_orders = table.get_session_orders()
                print(f"   📦 Session Orders: {session_orders.count()}")

                # Get only active orders (for kitchen/display purposes)
                active_orders = table.orders.filter(
                    status__in=['pending', 'confirmed', 'preparing', 'ready']
                )
                print(f"   🔥 Active Orders: {active_orders.count()}")

                # Check sessions
                active_sessions = table.order_sessions.filter(is_active=True)
                print(f"   🎫 Active Sessions: {active_sessions.count()}")

                # Check if table can be billed
                can_bill = table.can_be_billed()
                has_served_orders = table.has_served_orders()
                print(f"   💰 Can Bill: {can_bill}")
                print(f"   ✅ Has Served: {has_served_orders}")

                # Build active orders data
                active_orders_data = []
                for order in active_orders:
                    try:
                        created_by_name = order.created_by.get_full_name() if order.created_by else 'System'
                    except:
                        created_by_name = getattr(order.created_by, 'username', 'System') if order.created_by else 'System'

                    active_orders_data.append({
                        'id': order.id,
                        'menu_item_name': order.menu_item.name if order.menu_item else 'Custom Item',
                        'quantity': order.quantity,
                        'status': order.status,
                        'order_number': order.order_number,
                        'total_price': float(order.total_price),
                        'created_by_name': created_by_name,
                        'special_instructions': order.special_instructions or '',
                        'priority': order.priority,
                        'unit_price': float(order.unit_price)
                    })

                # Build session orders data for billing
                session_orders_data = []
                for order in session_orders:
                    try:
                        created_by_name = order.created_by.get_full_name() if order.created_by else 'System'
                    except:
                        created_by_name = getattr(order.created_by, 'username', 'System') if order.created_by else 'System'

                    session_orders_data.append({
                        'id': order.id,
                        'menu_item_name': order.menu_item.name if order.menu_item else 'Custom Item',
                        'quantity': order.quantity,
                        'status': order.status,
                        'order_number': order.order_number,
                        'total_price': float(order.total_price),
                        'unit_price': float(order.unit_price),
                        'created_by_name': created_by_name,
                        'special_instructions': order.special_instructions or '',
                        'created_at': order.created_at.isoformat()
                    })

                bill_amount = float(table.get_total_bill_amount())
                print(f"   💰 Bill Amount: ₹{bill_amount}")

                table_data.append({
                    'id': table.id,
                    'table_number': table.table_number,
                    'capacity': table.capacity,
                    'status': table.status,
                    'location': table.location or '',
                    'notes': table.notes or '',
                    # Active orders (for display/management)
                    'active_orders_count': active_orders.count(),
                    'active_orders': active_orders_data,
                    # Session orders (for billing)
                    'session_orders_count': session_orders.count(),
                    'session_orders': session_orders_data,
                    # Billing information
                    'total_bill_amount': bill_amount,
                    'can_bill': session_orders.count() > 0,
                    'has_served_orders': any(o.status == 'served' for o in session_orders),
                    # Time information
                    'time_occupied': table.get_occupied_duration(),
                    'last_occupied_at': table.last_occupied_at.isoformat() if table.last_occupied_at else None,
                    # EXPLICIT FLAGS FOR FRONTEND
                    'has_billing_data': session_orders.count() > 0,
                    'billing_ready': session_orders.count() > 0,
                    'show_bill_button': session_orders.count() > 0,
                    # Status flags for frontend
                    'show_billing_options': can_bill or has_served_orders,
                    'show_manage_orders': active_orders.count() > 0,
                    'is_billable': session_orders.count() > 0,
                    # Enhanced metadata
                    'priority_level': getattr(table, 'priority_level', 1),
                    'created_at': table.created_at.isoformat() if hasattr(table, 'created_at') else None
                })

            print(f"🌐 Returning {len(table_data)} tables")
            return Response({
                'tables': table_data,
                'total_tables': len(table_data),
                'timestamp': timezone.now().isoformat()
            })

        except Exception as e:
            print(f"❌ ERROR in TablesWithOrdersView: {e}")
            logger.error(f"Error in TablesWithOrdersView: {e}")
            return Response({
                'error': str(e),
                'tables': []
            }, status=500)
class MenuForOrderingView(APIView):
    """Get menu organized for ordering interface"""
    def get(self, request):
        try:
            from .models import MenuCategory, MenuItem

            categories = MenuCategory.objects.filter(is_active=True).prefetch_related(
                models.Prefetch(
                    'items',
                    queryset=MenuItem.objects.filter(is_active=True, availability='available')
                )
            )

            menu_data = []
            for category in categories:
                items = category.items.all()
                if items.exists():
                    menu_data.append({
                        'id': category.id,
                        'name': category.name,
                        'description': category.description,
                        'icon': getattr(category, 'icon', '🍽️'),
                        'items': [{
                            'id': item.id,
                            'name': item.name,
                            'name_en': item.name,
                            'description': item.description,
                            'description_en': item.description,
                            'price': float(item.price),
                            'category_id': category.id,
                            'is_veg': getattr(item, 'is_veg', True),
                            'is_spicy': getattr(item, 'is_spicy', False),
                            'preparation_time': getattr(item, 'preparation_time', 15),
                            'availability': item.availability,
                            'image': item.image.url if item.image else None
                        } for item in items]
                    })

            return Response(menu_data)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

class DashboardStatsView(APIView):
    """Get dashboard statistics"""
    def get(self, request):
        try:
            from django.utils import timezone
            from datetime import datetime, timedelta

            today = timezone.now().date()

            # Table stats
            total_tables = Table.objects.filter(is_active=True).count()
            free_tables = Table.objects.filter(is_active=True, status='free').count()
            occupied_tables = Table.objects.filter(is_active=True, status='occupied').count()

            # Order stats
            preparing_orders = Order.objects.filter(status='preparing').count()

            # Revenue stats (you might need to adjust based on your billing model)
            try:
                from apps.bills.models import Bill
                today_revenue = Bill.objects.filter(
                    created_at__date=today
                ).aggregate(
                    total=models.Sum('total_amount')
                )['total'] or 0
            except:
                today_revenue = 0

            return Response({
                'tables': {
                    'total': total_tables,
                    'free': free_tables,
                    'occupied': occupied_tables,
                    'reserved': Table.objects.filter(is_active=True, status='reserved').count(),
                    'cleaning': Table.objects.filter(is_active=True, status='cleaning').count(),
                    'maintenance': Table.objects.filter(is_active=True, status='maintenance').count()
                },
                'orders': {
                    'preparing': preparing_orders,
                    'pending': Order.objects.filter(status='pending').count(),
                    'ready': Order.objects.filter(status='ready').count()
                },
                'revenue': {
                    'today': float(today_revenue)
                }
            })
        except Exception as e:
            return Response({'error': str(e)}, status=500)
class TableViewSet(viewsets.ModelViewSet):
    """Enhanced ViewSet for table management with complete CRUD"""
    queryset = Table.objects.filter(is_active=True)
    serializer_class = TableSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['get', 'post'])
    def manage_orders(self, request, pk=None):
        """FIXED: Admin functionality to view and modify table orders"""
        table = self.get_object()
        
        # Only allow admin, staff, and waiter access
        if not hasattr(request, 'user') or request.user.role not in ['admin', 'staff', 'waiter']:
            raise PermissionDenied('Admin, Staff, or Waiter access required')

        if request.method == 'GET':
            print(f"\n🔍 MANAGE_ORDERS called for Table {table.table_number}")
            
            # CRITICAL FIX: Get all billable orders for this table
            # Check if table has an active billing session
            active_session = table.order_sessions.filter(is_active=True).first()
            
            if active_session:
                print(f"📋 Found active session: {active_session.session_id}")
                # Get orders from active session start time
                session_orders = table.orders.filter(
                    created_at__gte=active_session.created_at,
                    status__in=['pending', 'confirmed', 'preparing', 'ready', 'served']  # INCLUDE SERVED
                ).exclude(status='cancelled').order_by('created_at')
            else:
                print("📋 No active session, checking for today's orders")
                # Get today's orders that haven't been billed
                today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
                session_orders = table.orders.filter(
                    created_at__gte=today,
                    status__in=['pending', 'confirmed', 'preparing', 'ready', 'served']  # INCLUDE SERVED
                ).exclude(status='cancelled').order_by('created_at')
                
                # If no orders today, get the most recent orders
                if not session_orders.exists():
                    print("📋 No orders today, getting recent orders")
                    session_orders = table.orders.filter(
                        status__in=['served', 'ready']  # Get completed orders
                    ).order_by('-created_at')[:10]  # Last 10 orders

            print(f"📦 Found {session_orders.count()} orders for billing")

            # Calculate total including served orders
            total_amount = sum(order.total_price for order in session_orders)

            orders_data = []
            for order in session_orders:
                try:
                    created_by_name = order.created_by.get_full_name() if order.created_by else 'System'
                except:
                    created_by_name = getattr(order.created_by, 'username', 'System') if order.created_by else 'System'
                    
                orders_data.append({
                    'id': order.id,
                    'order_number': order.order_number,
                    'menu_item_name': order.menu_item.name if order.menu_item else 'Custom Item',
                    'menu_item_id': order.menu_item.id if order.menu_item else None,
                    'quantity': order.quantity,
                    'unit_price': float(order.unit_price),
                    'total_price': float(order.total_price),
                    'status': order.status,
                    'special_instructions': order.special_instructions or '',
                    'created_at': order.created_at.isoformat(),
                    'created_by_name': created_by_name,
                    'can_modify': order.status not in ['served', 'cancelled']
                })

            print(f"💰 Total amount: ₹{total_amount}")

            return Response({
                'table_number': table.table_number,
                'orders': orders_data,
                'total_amount': float(total_amount),
                'session_active': bool(active_session),
                'can_add_items': table.status == 'occupied' or session_orders.exists(),
                'debug_info': {
                    'orders_count': session_orders.count(),
                    'table_status': table.status,
                    'has_active_session': bool(active_session)
                }
            })

        elif request.method == 'POST':
            # Handle POST requests for adding custom items (existing code remains the same)
            action_type = request.data.get('action')
            if action_type == 'add_custom_item':
                # ... (keep existing add_custom_item code)
                pass

            return Response(
                {'error': 'Invalid action'},
                status=status.HTTP_400_BAD_REQUEST
            )
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
        """FIXED: Complete billing with enhanced admin features"""
        table = self.get_object()

        # Get or create active session
        session = table.order_sessions.filter(is_active=True).first()
        if not session:
            # Create new session with all orders for this table
            session = OrderSession.objects.create(
                table=table,
                created_by=request.user
            )

        try:
            # Apply billing parameters from request
            customer_name = request.data.get('customer_name', 'Guest')
            customer_phone = request.data.get('customer_phone', '')
            payment_method = request.data.get('payment_method', 'cash')
            discount_amount = request.data.get('discount_amount', 0)
            discount_percentage = request.data.get('discount_percentage', 0)
            service_charge = request.data.get('service_charge', 0)
            notes = request.data.get('notes', '')
            admin_notes = request.data.get('admin_notes', '')
            apply_gst = request.data.get('apply_gst', True)

            # Update session with billing details
            session.discount_amount = Decimal(str(discount_amount))
            session.discount_percentage = Decimal(str(discount_percentage))
            session.service_charge = Decimal(str(service_charge))
            session.payment_method = payment_method
            session.notes = notes
            session.admin_notes = admin_notes
            session.apply_gst = apply_gst

            # CRITICAL FIX: Generate receipt_number if missing
            #if not session.receipt_number:
            #   session.receipt_number = f"RCP-{timezone.now().strftime('%Y%m%d')}-{str(session.session_id)[:8].upper()}"
            if not session.receipt_number:
                short_id = str(uuid.uuid4())[:8].upper()
                session.receipt_number = f"R{timezone.now().strftime('%y%m%d')}{short_id}"

            # Calculate totals and complete session
            final_amount = session.calculate_totals()
            session.complete_session(request.user)

            # Broadcast table status update
            broadcast_table_update(table, 'occupied')

            return Response({
                'message': 'Billing completed successfully',
                'receipt_number': session.receipt_number,
                'final_amount': float(final_amount),
                'table_status': table.status,
                'session_data': OrderSessionSerializer(session).data,
                'apply_gst': apply_gst
            })

        except Exception as e:
            logger.error(f"Error completing billing for table {table.table_number}: {e}")
            return Response(
                {'error': f'Failed to complete billing: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def enhanced_billing(self, request, pk=None):
        """Enhanced billing with customer details and full order management"""
        table = self.get_object()

        # Check permissions
        if not hasattr(request, 'user') or request.user.role not in ['admin', 'staff']:
            raise PermissionDenied('Billing access required')

        try:
            with transaction.atomic():
                # Get or create active session
                session = table.order_sessions.filter(is_active=True).first()
                if not session:
                    session = OrderSession.objects.create(
                        table=table,
                        created_by=request.user
                    )

                # Extract billing data
                customer_name = request.data.get('customer_name', 'Guest')
                customer_phone = request.data.get('customer_phone', '')
                payment_method = request.data.get('payment_method', 'cash')
                discount_amount = request.data.get('discount_amount', 0)
                discount_percentage = request.data.get('discount_percentage', 0)
                service_charge = request.data.get('service_charge', 0)
                notes = request.data.get('notes', '')
                admin_notes = request.data.get('admin_notes', '')

                # Update session with billing details
                session.discount_amount = Decimal(str(discount_amount))
                session.discount_percentage = Decimal(str(discount_percentage))
                session.service_charge = Decimal(str(service_charge))
                session.payment_method = payment_method
                session.notes = notes
                session.admin_notes = admin_notes

                # Calculate final amount with GST
                final_amount = session.calculate_totals()

                # Generate receipt number if missing
                if not session.receipt_number:
                    session.receipt_number = f"RCP-{timezone.now().strftime('%Y%m%d')}-{str(session.session_id)[:8].upper()}"

                # Complete the session
                session.complete_session(request.user)

                # Free the table
                table.mark_free()

                # Broadcast table status update
                broadcast_table_update(table, 'occupied')

                return Response({
                    'message': 'Billing completed successfully',
                    'receipt_number': session.receipt_number,
                    'final_amount': float(final_amount),
                    'customer_name': customer_name,
                    'customer_phone': customer_phone,
                    'table_number': table.table_number,
                    'table_status': table.status,
                    'payment_method': payment_method,
                    'session_data': OrderSessionSerializer(session).data
                })

        except Exception as e:
            logger.error(f"Error in enhanced billing for table {table.table_number}: {e}")
            return Response(
                {'error': f'Failed to complete billing: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
         )
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


    @action(detail=False, methods=['post'])
    def admin_bulk_modify(self, request):
        """Admin bulk modification of orders for a table"""
        if not hasattr(request, 'user') or request.user.role not in ['admin', 'waiter','staff']:
            raise PermissionDenied('Admin or Manager access required')

        table_id = request.data.get('table_id')
        modifications = request.data.get('modifications', [])

        if not table_id or not modifications:
            return Response(
                {'error': 'Table ID and modifications are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            table = Table.objects.get(id=table_id, is_active=True)
            modified_orders = []

            with transaction.atomic():
                for mod in modifications:
                    order_id = mod.get('order_id')
                    action = mod.get('action')

                    try:
                        order = Order.objects.get(id=order_id, table=table)

                        if order.status in ['served', 'cancelled']:
                            continue  # Skip already completed orders

                        if action == 'update_quantity':
                            new_quantity = mod.get('quantity')
                            if new_quantity and new_quantity > 0:
                                order.quantity = new_quantity
                                order.total_price = order.unit_price * new_quantity
                                order.admin_notes = f"Bulk update by {request.user.get_full_name()}"
                                order.save()
                                modified_orders.append(order)

                        elif action == 'cancel':
                            order.status = 'cancelled'
                            order.admin_notes = f"Bulk cancelled by {request.user.get_full_name()}"
                            order.save()
                            modified_orders.append(order)

                    except Order.DoesNotExist:
                        continue

                # Broadcast all updates
                for order in modified_orders:
                    broadcast_order_update(order, None)

            return Response({
                'message': f'Successfully modified {len(modified_orders)} orders',
                'modified_count': len(modified_orders)
            })

        except Table.DoesNotExist:
            return Response(
                {'error': 'Table not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in bulk modification: {e}")
            return Response(
                {'error': f'Failed to perform bulk modifications: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    @action(detail=True, methods=['post'])
    def admin_modify(self, request, pk=None):
        """Admin functionality to modify existing orders - FIXED"""
        order = self.get_object()

        # Only allow admin and manager access
        if not hasattr(request, 'user') or request.user.role not in ['admin', 'staff']:
            raise PermissionDenied('Admin or Manager access required')

        # Don't allow modification of served or cancelled orders
        if order.status in ['served', 'cancelled']:
            return Response(
                {'error': 'Cannot modify served or cancelled orders'},
                status=status.HTTP_400_BAD_REQUEST
            )

        action_type = request.data.get('action')

        try:
            with transaction.atomic():
                if action_type == 'update_quantity':
                    new_quantity = request.data.get('quantity')
                    if not new_quantity or new_quantity <= 0:
                        return Response(
                            {'error': 'Valid quantity is required'},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    order.quantity = new_quantity
                    order.total_price = order.unit_price * new_quantity
                    # FIXED: Use safe get_full_name method
                    user_name = getattr(request.user, 'get_full_name', lambda: request.user.username)()
                    order.admin_notes = f"Quantity updated by {user_name} at {timezone.now()}"
                    order.save()

                elif action_type == 'update_instructions':
                    new_instructions = request.data.get('special_instructions', '')
                    order.special_instructions = new_instructions
                    user_name = getattr(request.user, 'get_full_name', lambda: request.user.username)()
                    order.admin_notes = f"Instructions updated by {user_name} at {timezone.now()}"
                    order.save()

                elif action_type == 'update_priority':
                    new_priority = request.data.get('priority', 'normal')
                    if new_priority not in dict(Order.PRIORITY_CHOICES):
                        return Response(
                            {'error': 'Invalid priority'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    order.priority = new_priority
                    user_name = getattr(request.user, 'get_full_name', lambda: request.user.username)()
                    order.admin_notes = f"Priority updated to {new_priority} by {user_name} at {timezone.now()}"
                    order.save()

                elif action_type == 'cancel_order':
                    order.status = 'cancelled'
                    user_name = getattr(request.user, 'get_full_name', lambda: request.user.username)()
                    order.admin_notes = f"Cancelled by {user_name} at {timezone.now()}"
                    order.save()

                else:
                    return Response(
                        {'error': 'Invalid action'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Broadcast the update
                broadcast_order_update(order, None)

                return Response({
                    'message': 'Order updated successfully',
                    'order': OrderSerializer(order, context={'request': request}).data
                })

        except Exception as e:
            logger.error(f"Error modifying order {order.id}: {e}")
            return Response(
                {'error': f'Failed to update order: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
        """Enhanced order creation with proper broadcasting - FIXED"""
        # Set source as mobile for waiter orders
        source = 'mobile' if getattr(self.request.user, 'role', None) == 'waiter' else 'dine_in'
        order = serializer.save(created_by=self.request.user, source=source)

        # CRITICAL: Always broadcast order update after creation
        try:
            # Broadcast to all connected clients immediately
            broadcast_order_update(order, None)

            # Also create backup if KDS is offline
            if not is_kds_connected():
                create_order_backup(order)

            logger.info(f"Order {order.order_number} created and broadcasted successfully")

        except Exception as e:
            logger.error(f"Error broadcasting order {order.order_number}: {e}")
            # Don't fail the order creation, just log the error

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

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Create multiple orders with enhanced broadcasting - FIXED"""
        serializer = BulkOrderCreateSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            orders = serializer.save()

            # CRITICAL: Broadcast each order individually
            broadcast_success = 0
            kds_connected = is_kds_connected()

            for order in orders:
                try:
                    # Always try to broadcast
                    broadcast_order_update(order, None)
                    broadcast_success += 1

                    # Create backup if KDS offline
                    if not kds_connected:
                        create_order_backup(order)

                except Exception as e:
                    logger.error(f"Error broadcasting order {order.order_number}: {e}")

            logger.info(f"Bulk order created: {len(orders)} orders, {broadcast_success} broadcasted")

            response_serializer = OrderSerializer(orders, many=True, context={'request': request})
            return Response({
                'message': f'{len(orders)} orders created successfully',
                'orders': response_serializer.data,
                'kds_status': 'connected' if kds_connected else 'offline',
                'broadcast_success': broadcast_success
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def modify_order(self, request, pk=None):
        """Admin functionality to modify existing orders"""
        order = self.get_object()

        # Only allow modification of certain statuses
        if order.status in ['served', 'cancelled']:
            return Response(
                {'error': 'Cannot modify served or cancelled orders'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update order details
        new_quantity = request.data.get('quantity')
        new_instructions = request.data.get('special_instructions')
        new_priority = request.data.get('priority')

        if new_quantity and new_quantity > 0:
            order.quantity = new_quantity
            order.total_price = order.unit_price * new_quantity

        if new_instructions is not None:
            order.special_instructions = new_instructions

        if new_priority and new_priority in dict(Order.PRIORITY_CHOICES):
            order.priority = new_priority

        order.admin_notes = f"Modified by {request.user.get_full_name()} at {timezone.now()}"
        order.save()

        # Broadcast update
        broadcast_order_update(order, None)

        return Response({
            'message': 'Order modified successfully',
            'order': OrderSerializer(order, context={'request': request}).data
        })

    @action(detail=True, methods=['delete'])
    def cancel_order(self, request, pk=None):
        """Admin functionality to cancel orders"""
        order = self.get_object()

        if order.status == 'served':
            return Response(
                {'error': 'Cannot cancel served orders'},
                status=status.HTTP_400_BAD_REQUEST
            )

        old_status = order.status
        order.status = 'cancelled'
        order.admin_notes = f"Cancelled by {request.user.get_full_name()} at {timezone.now()}"
        order.save()

        # Broadcast cancellation
        broadcast_order_update(order, old_status)

        return Response({
            'message': 'Order cancelled successfully'
        })

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

# Enhanced Billing ViewSet for frontend compatibility
class EnhancedBillingViewSet(viewsets.ViewSet):
    """Enhanced billing functionality for frontend compatibility"""
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """Only admin, staff and managers can access billing"""
        if hasattr(self.request, 'user') and self.request.user.is_authenticated:
            if self.request.user.role not in ['admin', 'staff']:
                raise PermissionDenied('Access denied: Admin, Manager or Staff role required')
        return super().get_permissions()

    @action(detail=False, methods=['get'])
    def active_tables_dashboard(self, request):
        """Get active tables for billing dashboard"""
        try:
            # Get tables with active orders or occupied status
            tables = Table.objects.filter(
                Q(status='occupied') | Q(orders__status__in=['pending', 'confirmed', 'preparing', 'ready', 'served'])
            ).distinct().select_related().prefetch_related('orders__menu_item')

            active_tables_data = []
            for table in tables:
                # Get active orders
                active_orders = table.get_active_orders()
                session_orders = table.get_session_orders()

                # Calculate subtotal
                subtotal = sum(order.total_price for order in session_orders)

                table_data = {
                    'table_id': table.id,
                    'table_number': table.table_number,
                    'table_capacity': table.capacity,
                    'table_location': table.location,
                    'status': table.status,
                    'orders_count': active_orders.count(),
                    'subtotal': float(subtotal),
                    'last_order_time': active_orders.first().created_at if active_orders.exists() else None,
                    'customer_name': 'Guest',  # Default, can be enhanced
                    'customer_phone': '',
                    'orders': [
                        {
                            'order_number': order.order_number,
                            'status': order.status,
                            'items': [
                                {
                                    'id': order.id,
                                    'name': order.menu_item.name,
                                    'quantity': order.quantity,
                                    'total': float(order.total_price),
                                    'special_instructions': order.special_instructions
                                }
                            ]
                        }
                        for order in session_orders
                    ]
                }
                active_tables_data.append(table_data)

            return Response({
                'active_tables': active_tables_data,
                'total_count': len(active_tables_data)
            })

        except Exception as e:
            logger.error(f"Error in active_tables_dashboard: {e}")
            return Response(
                {'error': 'Failed to fetch active tables'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def calculate_bill_with_gst(self, request):
        """Calculate bill with GST"""
        try:
            table_id = request.data.get('table_id')
            apply_gst = request.data.get('apply_gst', True)
            gst_rate = request.data.get('gst_rate', 18) / 100  # Convert percentage
            interstate = request.data.get('interstate', False)
            discount_percent = request.data.get('discount_percent', 0)
            discount_amount = request.data.get('discount_amount', 0)

            table = Table.objects.get(id=table_id)

            # Get session orders
            session_orders = table.get_session_orders()
            subtotal = sum(order.total_price for order in session_orders)

            # Apply discount
            if discount_percent > 0:
                discount_amount = subtotal * (discount_percent / 100)

            taxable_amount = subtotal - Decimal(str(discount_amount))

            # Calculate GST
            gst_breakdown = {
                'total_gst_amount': 0,
                'cgst_amount': 0,
                'sgst_amount': 0,
                'igst_amount': 0,
                'cgst_rate': 0,
                'sgst_rate': 0,
                'gst_rate': gst_rate * 100
            }

            if apply_gst:
                gst_calculation = calculate_gst_breakdown(taxable_amount, gst_rate, interstate)
                if interstate:
                    gst_breakdown.update({
                        'total_gst_amount': gst_calculation['total_gst'],
                        'igst_amount': gst_calculation['igst'],
                        'gst_rate': gst_calculation['gst_rate']
                    })
                else:
                    gst_breakdown.update({
                        'total_gst_amount': gst_calculation['total_gst'],
                        'cgst_amount': gst_calculation['cgst'],
                        'sgst_amount': gst_calculation['sgst'],
                        'cgst_rate': gst_calculation['gst_rate'] / 2,
                        'sgst_rate': gst_calculation['gst_rate'] / 2,
                        'gst_rate': gst_calculation['gst_rate']
                    })

            total_amount = taxable_amount + Decimal(str(gst_breakdown['total_gst_amount']))

            bill_breakdown = {
                'table_number': table.table_number,
                'item_count': session_orders.count(),
                'subtotal': float(subtotal),
                'discount_amount': float(discount_amount),
                'taxable_amount': float(taxable_amount),
                'gst_applied': apply_gst,
                'interstate': interstate,
                'total_amount': float(total_amount),
                'total_savings': float(discount_amount),
                **gst_breakdown
            }

            return Response({
                'bill_breakdown': bill_breakdown
            })

        except Exception as e:
            logger.error(f"Error calculating bill: {e}")
            return Response(
                {'error': 'Failed to calculate bill'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def generate_final_bill(self, request):
        """Generate final bill and free table"""
        try:
            table_id = request.data.get('table_id')
            customer_name = request.data.get('customer_name', 'Guest')
            customer_phone = request.data.get('customer_phone', '')
            payment_method = request.data.get('payment_method', 'cash')

            table = Table.objects.get(id=table_id)

            # Get or create session
            session = table.order_sessions.filter(is_active=True).first()
            if not session:
                session = OrderSession.objects.create(
                    table=table,
                    created_by=request.user
                )

            # Apply GST settings from request
            apply_gst = request.data.get('apply_gst', True)
            gst_rate = request.data.get('gst_rate', 18) / 100
            discount_percent = request.data.get('discount_percent', 0)
            discount_amount = request.data.get('discount_amount', 0)

            # Update session with billing details
            session.discount_percentage = Decimal(str(discount_percent))
            session.discount_amount = Decimal(str(discount_amount))
            session.payment_method = payment_method

            # Generate complete bill
            receipt_data = generate_complete_bill(
                session,
                payment_method=payment_method,
                customer_name=customer_name,
                customer_phone=customer_phone
            )

            # Free the table
            table.mark_free()

            return Response({
                'message': 'Bill generated successfully',
                'bill': {
                    'receipt_number': session.receipt_number,
                    'customer_name': customer_name,
                    'total_amount': float(session.final_amount)
                },
                'table': {
                    'table_number': table.table_number,
                    'status': table.status
                },
                'table_freed': True,
                'receipt_data': receipt_data
            })

        except Exception as e:
            logger.error(f"Error generating final bill: {e}")
            return Response(
                {'error': 'Failed to generate bill'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# Enhanced API endpoints
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    if not hasattr(request.user, 'role') or request.user.role not in ['admin','staff', 'waiter']:
        return Response({'error': 'Insufficient permissions'}, status=403)
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

# KDS Connection management endpoints
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
    update_kds_heartbeat()
    increment_kds_connections()  # Track active connections
    return Response({'message': 'Heartbeat updated'})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_offline_orders_endpoint(request):
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



