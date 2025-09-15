# apps/restaurant/utils.py - Utility functions for real-time updates
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()

def broadcast_order_update(order, old_status=None):
    """Broadcast order updates to all connected clients"""
    try:
        from .serializers import OrderKDSSerializer, OrderSerializer

        # Prepare order data
        kds_data = OrderKDSSerializer(order).data
        full_data = OrderSerializer(order).data

        timestamp = timezone.now().isoformat()

        # Determine update type
        if old_status is None:
            update_type = 'new_order'
            audio_enabled = True  # New orders should trigger audio
        else:
            update_type = 'order_updated'
            audio_enabled = False  # Status updates don't need audio

        # Broadcast to Kitchen Display System
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                'kds_kitchen_display',
                {
                    'type': 'new_order_notification' if update_type == 'new_order' else 'order_status_updated',
                    'order': kds_data,
                    'order_id': str(order.id),
                    'status': order.status,
                    'old_status': old_status,
                    'audio_enabled': audio_enabled,
                    'timestamp': timestamp
                }
            )

            # Broadcast to ordering interface
            async_to_sync(channel_layer.group_send)(
                'ordering_ordering',
                {
                    'type': 'order_confirmed',
                    'order_id': str(order.id),
                    'table_id': str(order.table.id),
                    'order_data': full_data,
                    'timestamp': timestamp
                }
            )

            # Broadcast to table management
            async_to_sync(channel_layer.group_send)(
                'table_mgmt_table_management',
                {
                    'type': 'new_order_placed',
                    'table_id': str(order.table.id),
                    'order_count': order.table.get_active_orders().count(),
                    'timestamp': timestamp
                }
            )

        logger.info(f"Broadcasted order update: {order.order_number} - {update_type}")

    except Exception as e:
        logger.error(f"Error broadcasting order update: {e}")

def broadcast_table_update(table, old_status=None):
    """Broadcast table status updates to all connected clients"""
    try:
        from .serializers import TableSerializer

        table_data = TableSerializer(table).data
        timestamp = timezone.now().isoformat()

        if channel_layer:
            # Broadcast to all relevant channels
            channels = [
                'kds_kitchen_display',
                'ordering_ordering',
                'table_mgmt_table_management'
            ]

            for channel in channels:
                async_to_sync(channel_layer.group_send)(
                    channel,
                    {
                        'type': 'table_status_updated',
                        'table': table_data,
                        'table_id': str(table.id),
                        'old_status': old_status,
                        'new_status': table.status,
                        'timestamp': timestamp
                    }
                )

        logger.info(f"Broadcasted table update: {table.table_number} - {old_status} -> {table.status}")

    except Exception as e:
        logger.error(f"Error broadcasting table update: {e}")

def broadcast_menu_update(menu_item, update_type='updated'):
    """Broadcast menu item updates to ordering clients"""
    try:
        from .serializers import MenuItemSerializer

        item_data = MenuItemSerializer(menu_item).data
        timestamp = timezone.now().isoformat()

        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                'ordering_ordering',
                {
                    'type': 'menu_item_updated',
                    'item': item_data,
                    'update_type': update_type,
                    'timestamp': timestamp
                }
            )

        logger.info(f"Broadcasted menu update: {menu_item.name} - {update_type}")

    except Exception as e:
        logger.error(f"Error broadcasting menu update: {e}")

def broadcast_settings_update(settings_data):
    """Broadcast KDS settings updates"""
    try:
        timestamp = timezone.now().isoformat()

        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                'kds_kitchen_display',
                {
                    'type': 'settings_updated',
                    'settings': settings_data,
                    'timestamp': timestamp
                }
            )

        logger.info("Broadcasted KDS settings update")

    except Exception as e:
        logger.error(f"Error broadcasting settings update: {e}")

def get_kds_summary_data():
    """Get summary data for KDS dashboard"""
    try:
        from .models import Order, Table
        from django.db.models import Count

        # Order status counts
        order_counts = Order.objects.filter(
            status__in=['pending', 'confirmed', 'preparing', 'ready']
        ).values('status').annotate(count=Count('id'))

        status_summary = {}
        for item in order_counts:
            status_summary[item['status']] = item['count']

        # Table status counts
        table_counts = Table.objects.filter(is_active=True).values('status').annotate(
            count=Count('id')
        )

        table_summary = {}
        for item in table_counts:
            table_summary[item['status']] = item['count']

        return {
            'orders': status_summary,
            'tables': table_summary,
            'timestamp': timezone.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting KDS summary data: {e}")
        return {}

def calculate_wait_times():
    """Calculate average wait times for different order statuses"""
    try:
        from .models import Order
        from django.utils import timezone

        now = timezone.now()

        # Orders in different stages
        pending_orders = Order.objects.filter(status='pending')
        preparing_orders = Order.objects.filter(status='preparing')
        ready_orders = Order.objects.filter(status='ready')

        wait_times = {}

        # Calculate average wait time for pending orders
        if pending_orders.exists():
            pending_times = []
            for order in pending_orders:
                wait_time = (now - order.created_at).total_seconds() / 60
                pending_times.append(wait_time)
            wait_times['pending_avg'] = sum(pending_times) / len(pending_times)
        else:
            wait_times['pending_avg'] = 0

        # Calculate average preparation time for preparing orders
        if preparing_orders.exists():
            prep_times = []
            for order in preparing_orders:
                if order.preparation_started_at:
                    prep_time = (now - order.preparation_started_at).total_seconds() / 60
                    prep_times.append(prep_time)
            if prep_times:
                wait_times['preparing_avg'] = sum(prep_times) / len(prep_times)
            else:
                wait_times['preparing_avg'] = 0
        else:
            wait_times['preparing_avg'] = 0

        # Calculate wait time for ready orders
        if ready_orders.exists():
            ready_times = []
            for order in ready_orders:
                if order.ready_at:
                    ready_time = (now - order.ready_at).total_seconds() / 60
                    ready_times.append(ready_time)
            if ready_times:
                wait_times['ready_avg'] = sum(ready_times) / len(ready_times)
            else:
                wait_times['ready_avg'] = 0
        else:
            wait_times['ready_avg'] = 0

        return wait_times

    except Exception as e:
        logger.error(f"Error calculating wait times: {e}")
        return {}

def get_order_priority_color(priority):
    """Get color coding for order priority"""
    colors = {
        'low': '#6B7280',      # Gray
        'normal': '#3B82F6',   # Blue
        'high': '#F59E0B',     # Orange
        'urgent': '#EF4444'    # Red
    }
    return colors.get(priority, '#3B82F6')

def get_order_status_color(status):
    """Get color coding for order status"""
    colors = {
        'pending': '#F59E0B',    # Orange
        'confirmed': '#3B82F6',  # Blue
        'preparing': '#8B5CF6',  # Purple
        'ready': '#10B981',      # Green
        'served': '#6B7280',     # Gray
        'cancelled': '#EF4444'   # Red
    }
    return colors.get(status, '#6B7280')

def format_preparation_time(minutes):
    """Format preparation time for display"""
    if minutes < 1:
        return "< 1m"
    elif minutes < 60:
        return f"{int(minutes)}m"
    else:
        hours = int(minutes // 60)
        remaining_minutes = int(minutes % 60)
        return f"{hours}h {remaining_minutes}m"

def generate_order_notification_sound():
    """Generate audio notification data for new orders"""
    return {
        'play': True,
        'sound_type': 'new_order',
        'volume': 0.8,
        'repeat': 1
    }

def log_order_activity(order, action, user=None):
    """Log order activity for audit trail"""
    try:
        from .models import OrderActivity

        OrderActivity.objects.create(
            order=order,
            action=action,
            performed_by=user,
            details={
                'order_status': order.status,
                'table_number': order.table.table_number,
                'menu_item': order.menu_item.name,
                'timestamp': timezone.now().isoformat()
            }
        )

    except Exception as e:
        logger.error(f"Error logging order activity: {e}")

def check_kitchen_capacity():
    """Check current kitchen capacity and workload"""
    try:
        from .models import Order

        # Count orders in preparation
        preparing_orders = Order.objects.filter(status='preparing').count()
        pending_orders = Order.objects.filter(status='pending').count()

        # Calculate estimated workload
        total_workload = preparing_orders + pending_orders

        # Define capacity levels
        if total_workload < 5:
            capacity_status = 'low'
        elif total_workload < 15:
            capacity_status = 'medium'
        elif total_workload < 25:
            capacity_status = 'high'
        else:
            capacity_status = 'overloaded'

        return {
            'preparing_orders': preparing_orders,
            'pending_orders': pending_orders,
            'total_workload': total_workload,
            'capacity_status': capacity_status
        }

    except Exception as e:
        logger.error(f"Error checking kitchen capacity: {e}")
        return {}

