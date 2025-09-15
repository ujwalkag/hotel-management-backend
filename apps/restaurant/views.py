# apps/restaurant/views.py - Views for Restaurant/KDS System
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Q, Avg, F
from django.db.models.functions import TruncHour, TruncDate
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from .models import (
    Table, MenuCategory, MenuItem, Order, OrderSession, KitchenDisplaySettings
)
from .serializers import (
    TableSerializer, TableWithOrdersSerializer, MenuCategorySerializer,
    MenuItemSerializer, MenuItemCreateSerializer, OrderSerializer,
    OrderCreateSerializer, OrderKDSSerializer, OrderStatusUpdateSerializer,
    BulkOrderCreateSerializer, OrderSessionSerializer, KitchenDisplaySettingsSerializer,
    OrderAnalyticsSerializer, TableAnalyticsSerializer
)
from .utils import broadcast_order_update, broadcast_table_update

logger = logging.getLogger(__name__)

class TableViewSet(viewsets.ModelViewSet):
    """ViewSet for table management"""
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

        return queryset.order_by('table_number')

    def get_serializer_class(self):
        if self.action == 'with_orders':
            return TableWithOrdersSerializer
        return TableSerializer

    @action(detail=False, methods=['get'])
    def with_orders(self, request):
        """Get tables with their order details"""
        tables = self.get_queryset().prefetch_related(
            'orders__menu_item',
            'orders__created_by'
        )
        serializer = TableWithOrdersSerializer(tables, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """Change table status manually"""
        table = self.get_object()
        new_status = request.data.get('status')

        if not new_status or new_status not in dict(Table.STATUS_CHOICES):
            return Response(
                {'error': 'Invalid status'},
                status=status.HTTP_400_BAD_REQUEST
            )

        old_status = table.status
        table.status = new_status
        table.save()

        # Broadcast update
        broadcast_table_update(table, old_status)

        serializer = self.get_serializer(table)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def current_bill(self, request, pk=None):
        """Get current bill for table"""
        table = self.get_object()

        # Get active order session or create one
        session = table.order_sessions.filter(is_active=True).first()
        if not session:
            session = OrderSession.objects.create(
                table=table,
                created_by=request.user
            )

        # Calculate totals
        session.calculate_totals()

        serializer = OrderSessionSerializer(session)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def complete_billing(self, request, pk=None):
        """Complete billing and free the table"""
        table = self.get_object()

        # Get active session
        session = table.order_sessions.filter(is_active=True).first()
        if not session:
            return Response(
                {'error': 'No active session found'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Apply any discounts or adjustments
        discount = request.data.get('discount_amount', 0)
        notes = request.data.get('notes', '')

        session.discount_amount = Decimal(str(discount))
        session.notes = notes
        session.complete_session()

        # Broadcast table status update
        broadcast_table_update(table, 'occupied')

        return Response({
            'message': 'Billing completed successfully',
            'final_amount': float(session.final_amount),
            'table_status': table.status
        })

    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Get table analytics"""
        try:
            # Basic stats
            total_tables = Table.objects.filter(is_active=True).count()
            occupied_tables = Table.objects.filter(status='occupied', is_active=True).count()
            free_tables = Table.objects.filter(status='free', is_active=True).count()

            # Calculate average occupancy time
            occupied_duration = Table.objects.filter(
                status='occupied',
                last_occupied_at__isnull=False
            ).aggregate(
                avg_duration=Avg(
                    timezone.now() - F('last_occupied_at')
                )
            )['avg_duration']

            avg_occupancy_time = 0
            if occupied_duration:
                avg_occupancy_time = occupied_duration.total_seconds() / 60

            # Revenue per table (last 24 hours)
            yesterday = timezone.now() - timedelta(days=1)
            revenue_per_table = Table.objects.filter(is_active=True).annotate(
                revenue=Sum(
                    'orders__total_price',
                    filter=Q(orders__created_at__gte=yesterday)
                )
            ).values('table_number', 'revenue')

            analytics_data = {
                'total_tables': total_tables,
                'occupied_tables': occupied_tables,
                'free_tables': free_tables,
                'average_occupancy_time': avg_occupancy_time,
                'table_turnover_rate': 0,  # Can be calculated based on historical data
                'revenue_per_table': list(revenue_per_table)
            }

            serializer = TableAnalyticsSerializer(analytics_data)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Error generating table analytics: {e}")
            return Response(
                {'error': 'Failed to generate analytics'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class MenuCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for menu category management"""
    queryset = MenuCategory.objects.filter(is_active=True)
    serializer_class = MenuCategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MenuCategory.objects.filter(is_active=True).order_by('display_order', 'name')

    @action(detail=True, methods=['get'])
    def items(self, request, pk=None):
        """Get all items in this category"""
        category = self.get_object()
        items = category.items.filter(is_active=True)

        # Filter by availability
        available_only = request.query_params.get('available_only')
        if available_only == 'true':
            items = items.filter(availability='available')

        serializer = MenuItemSerializer(items, many=True)
        return Response(serializer.data)

class MenuItemViewSet(viewsets.ModelViewSet):
    """ViewSet for menu item management"""
    queryset = MenuItem.objects.filter(is_active=True)
    serializer_class = MenuItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = MenuItem.objects.filter(is_active=True).select_related('category')

        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category_id=category)

        # Filter by availability
        available_only = self.request.query_params.get('available_only')
        if available_only == 'true':
            queryset = queryset.filter(availability='available')

        # Filter by dietary preferences
        is_veg = self.request.query_params.get('is_veg')
        if is_veg == 'true':
            queryset = queryset.filter(is_veg=True)

        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )

        return queryset.order_by('category__display_order', 'display_order', 'name')

    def get_serializer_class(self):
        if self.action == 'create' or self.action == 'update':
            return MenuItemCreateSerializer
        return MenuItemSerializer

    @action(detail=True, methods=['post'])
    def update_availability(self, request, pk=None):
        """Update item availability"""
        item = self.get_object()
        new_availability = request.data.get('availability')

        if not new_availability or new_availability not in dict(MenuItem.AVAILABILITY_CHOICES):
            return Response(
                {'error': 'Invalid availability status'},
                status=status.HTTP_400_BAD_REQUEST
            )

        item.availability = new_availability
        item.save()

        serializer = self.get_serializer(item)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def popular_items(self, request):
        """Get most popular menu items"""
        # Get items ordered in the last 7 days
        week_ago = timezone.now() - timedelta(days=7)

        popular_items = MenuItem.objects.filter(
            is_active=True
        ).annotate(
            order_count=Count(
                'order',
                filter=Q(order__created_at__gte=week_ago)
            ),
            total_quantity=Sum(
                'order__quantity',
                filter=Q(order__created_at__gte=week_ago)
            )
        ).filter(
            order_count__gt=0
        ).order_by('-order_count')[:10]

        serializer = self.get_serializer(popular_items, many=True)
        return Response(serializer.data)

class OrderViewSet(viewsets.ModelViewSet):
    """ViewSet for order management"""
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Order.objects.select_related(
            'table', 'menu_item', 'menu_item__category', 'created_by'
        ).all()

        # Filter by table
        table = self.request.query_params.get('table')
        if table:
            queryset = queryset.filter(table_id=table)

        # Filter by status
        order_status = self.request.query_params.get('status')
        if order_status:
            queryset = queryset.filter(status=order_status)

        # Filter by date range
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)

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
        """Create order and set created_by"""
        serializer.save(created_by=self.request.user)

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
        """Create multiple orders at once"""
        serializer = BulkOrderCreateSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            orders = serializer.save()

            # Broadcast new orders
            for order in orders:
                broadcast_order_update(order, None)

            response_serializer = OrderSerializer(orders, many=True)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Get order analytics"""
        try:
            # Date range filter
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

            # Basic order stats
            orders = Order.objects.filter(created_at__range=[date_from, date_to])

            total_orders = orders.count()
            status_counts = orders.values('status').annotate(count=Count('id'))

            # Convert to dictionary
            status_breakdown = {}
            for item in status_counts:
                status_breakdown[item['status']] = item['count']

            # Financial metrics
            served_orders = orders.filter(status='served')
            total_revenue = served_orders.aggregate(
                total=Sum('total_price')
            )['total'] or Decimal('0.00')

            # Preparation time analysis
            completed_orders = orders.filter(
                status__in=['ready', 'served'],
                preparation_started_at__isnull=False,
                ready_at__isnull=False
            )

            avg_prep_time = 0
            if completed_orders.exists():
                prep_times = []
                for order in completed_orders:
                    prep_time = (order.ready_at - order.preparation_started_at).total_seconds() / 60
                    prep_times.append(prep_time)
                avg_prep_time = sum(prep_times) / len(prep_times)

            # Popular items and tables
            busiest_table = orders.values('table__table_number').annotate(
                count=Count('id')
            ).order_by('-count').first()

            most_ordered_item = orders.values('menu_item__name').annotate(
                count=Count('id'),
                total_qty=Sum('quantity')
            ).order_by('-total_qty').first()

            # Hourly breakdown
            hourly_orders = orders.extra({
                'hour': "EXTRACT(hour FROM created_at)"
            }).values('hour').annotate(
                count=Count('id')
            ).order_by('hour')

            # Category breakdown
            category_breakdown = orders.values('menu_item__category__name').annotate(
                count=Count('id'),
                revenue=Sum('total_price')
            ).order_by('-revenue')

            analytics_data = {
                'total_orders': total_orders,
                'pending_orders': status_breakdown.get('pending', 0),
                'preparing_orders': status_breakdown.get('preparing', 0),
                'ready_orders': status_breakdown.get('ready', 0),
                'served_orders': status_breakdown.get('served', 0),
                'cancelled_orders': status_breakdown.get('cancelled', 0),
                'average_preparation_time': avg_prep_time,
                'total_revenue': total_revenue,
                'busiest_table': busiest_table['table__table_number'] if busiest_table else 'N/A',
                'most_ordered_item': most_ordered_item['menu_item__name'] if most_ordered_item else 'N/A',
                'hourly_breakdown': list(hourly_orders),
                'status_breakdown': status_breakdown,
                'category_breakdown': list(category_breakdown)
            }

            serializer = OrderAnalyticsSerializer(analytics_data)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Error generating order analytics: {e}")
            return Response(
                {'error': 'Failed to generate analytics'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class OrderSessionViewSet(viewsets.ModelViewSet):
    """ViewSet for order session management"""
    queryset = OrderSession.objects.all()
    serializer_class = OrderSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = OrderSession.objects.select_related('table', 'created_by')

        # Filter by table
        table = self.request.query_params.get('table')
        if table:
            queryset = queryset.filter(table_id=table)

        # Filter by active status
        active_only = self.request.query_params.get('active_only')
        if active_only == 'true':
            queryset = queryset.filter(is_active=True)

        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        """Create session and set created_by"""
        serializer.save(created_by=self.request.user)

class KitchenDisplaySettingsViewSet(viewsets.ModelViewSet):
    """ViewSet for Kitchen Display System settings"""
    queryset = KitchenDisplaySettings.objects.all()
    serializer_class = KitchenDisplaySettingsSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current KDS settings"""
        settings = KitchenDisplaySettings.objects.first()
        if not settings:
            settings = KitchenDisplaySettings.objects.create(name='default')

        serializer = self.get_serializer(settings)
        return Response(serializer.data)

    @action(detail=False, methods=['patch'])
    def update_current(self, request):
        """Update current KDS settings"""
        settings = KitchenDisplaySettings.objects.first()
        if not settings:
            settings = KitchenDisplaySettings.objects.create(name='default')

        serializer = self.get_serializer(settings, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            # Broadcast settings update
            from .utils import broadcast_settings_update
            broadcast_settings_update(serializer.data)

            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Additional API endpoints
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """Get dashboard statistics"""
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

        # Revenue stats
        todays_revenue = todays_orders.filter(status='served').aggregate(
            total=Sum('total_price')
        )['total'] or Decimal('0.00')

        # Active sessions
        active_sessions = OrderSession.objects.filter(is_active=True).count()

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
                'total': occupied_tables + free_tables
            },
            'revenue': {
                'today': float(todays_revenue)
            },
            'sessions': {
                'active': active_sessions
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
def menu_for_ordering(request):
    """Get menu optimized for ordering interface"""
    try:
        categories = MenuCategory.objects.filter(is_active=True).prefetch_related(
            'items'
        ).order_by('display_order', 'name')

        menu_data = []
        for category in categories:
            available_items = category.items.filter(
                is_active=True,
                availability='available'
            ).order_by('display_order', 'name')

            if available_items.exists():
                menu_data.append({
                    'category': MenuCategorySerializer(category).data,
                    'items': MenuItemSerializer(available_items, many=True).data
                })

        return Response(menu_data)

    except Exception as e:
        logger.error(f"Error getting menu for ordering: {e}")
        return Response(
            {'error': 'Failed to load menu'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def quick_order(request):
    """Quick order creation endpoint"""
    try:
        table_id = request.data.get('table_id')
        menu_item_id = request.data.get('menu_item_id')
        quantity = request.data.get('quantity', 1)
        special_instructions = request.data.get('special_instructions', '')
        priority = request.data.get('priority', 'normal')

        if not all([table_id, menu_item_id]):
            return Response(
                {'error': 'Table and menu item are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate table and menu item
        try:
            table = Table.objects.get(id=table_id, is_active=True)
            menu_item = MenuItem.objects.get(
                id=menu_item_id,
                is_active=True,
                availability='available'
            )
        except (Table.DoesNotExist, MenuItem.DoesNotExist):
            return Response(
                {'error': 'Invalid table or menu item'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create order
        order = Order.objects.create(
            table=table,
            menu_item=menu_item,
            quantity=quantity,
            special_instructions=special_instructions,
            priority=priority,
            created_by=request.user
        )

        # Broadcast update
        broadcast_order_update(order, None)

        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error creating quick order: {e}")
        return Response(
            {'error': 'Failed to create order'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

