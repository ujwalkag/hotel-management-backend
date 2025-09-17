# apps/restaurant/utils.py - Enhanced utility functions with offline support
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
from django.core.cache import cache
import logging
import json
import requests
from decimal import Decimal

logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()

def broadcast_order_update(order, old_status=None):
    """Enhanced broadcast order updates with offline handling"""
    try:
        from .serializers import OrderKDSSerializer, OrderSerializer

        # Prepare order data
        kds_data = OrderKDSSerializer(order).data
        full_data = OrderSerializer(order).data

        timestamp = timezone.now().isoformat()

        # Determine update type
        if old_status is None:
            update_type = 'new_order'
            audio_enabled = True
        else:
            update_type = 'order_updated'
            audio_enabled = False

        # Store in cache for offline clients
        cache_key = f"order_update_{order.id}_{timestamp}"
        cache.set(cache_key, {
            'type': update_type,
            'order': kds_data,
            'timestamp': timestamp
        }, timeout=3600)  # 1 hour

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
    """Enhanced broadcast table status updates"""
    try:
        from .serializers import TableSerializer

        table_data = TableSerializer(table).data
        timestamp = timezone.now().isoformat()

        # Store in cache
        cache_key = f"table_update_{table.id}_{timestamp}"
        cache.set(cache_key, {
            'type': 'table_updated',
            'table': table_data,
            'timestamp': timestamp
        }, timeout=3600)

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

def is_kds_connected():
    """Check if Kitchen Display System is connected"""
    try:
        # Check if there are active WebSocket connections for KDS
        connection_count = cache.get('kds_connection_count', 0)
        last_heartbeat = cache.get('kds_last_heartbeat')
        
        if connection_count > 0 and last_heartbeat:
            # Check if last heartbeat was within last 60 seconds
            heartbeat_time = timezone.datetime.fromisoformat(last_heartbeat.replace('Z', '+00:00'))
            time_diff = (timezone.now() - heartbeat_time).total_seconds()
            return time_diff < 60
            
        return False
    except Exception as e:
        logger.error(f"Error checking KDS connection: {e}")
        return False

def update_kds_heartbeat():
    """Update KDS heartbeat timestamp"""
    cache.set('kds_last_heartbeat', timezone.now().isoformat(), timeout=120)

def increment_kds_connections():
    """Increment KDS connection count"""
    current_count = cache.get('kds_connection_count', 0)
    cache.set('kds_connection_count', current_count + 1, timeout=None)
    update_kds_heartbeat()

def decrement_kds_connections():
    """Decrement KDS connection count"""
    current_count = cache.get('kds_connection_count', 0)
    new_count = max(0, current_count - 1)
    cache.set('kds_connection_count', new_count, timeout=None)

def create_order_backup(order):
    """Create backup for order when KDS is offline"""
    try:
        from .models import OfflineOrderBackup
        from .serializers import OrderSerializer
        
        order_data = OrderSerializer(order).data
        
        OfflineOrderBackup.objects.create(
            order_data=order_data,
            table_number=order.table.table_number
        )
        
        logger.info(f"Created offline backup for order: {order.order_number}")
        
    except Exception as e:
        logger.error(f"Error creating order backup: {e}")

def process_offline_orders():
    """Process orders that were created when KDS was offline"""
    try:
        from .models import OfflineOrderBackup
        
        # Get unprocessed offline orders
        offline_orders = OfflineOrderBackup.objects.filter(is_processed=False)
        
        processed_count = 0
        for backup in offline_orders:
            try:
                # Broadcast the order to KDS if now connected
                if is_kds_connected():
                    # Simulate order broadcast
                    order_data = backup.order_data
                    
                    if channel_layer:
                        async_to_sync(channel_layer.group_send)(
                            'kds_kitchen_display',
                            {
                                'type': 'new_order_notification',
                                'order': order_data,
                                'audio_enabled': True,
                                'timestamp': timezone.now().isoformat(),
                                'offline_order': True
                            }
                        )
                    
                    # Mark as processed
                    backup.is_processed = True
                    backup.processed_at = timezone.now()
                    backup.save()
                    
                    processed_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing offline order {backup.id}: {e}")
        
        logger.info(f"Processed {processed_count} offline orders")
        return processed_count
        
    except Exception as e:
        logger.error(f"Error processing offline orders: {e}")
        return 0

def generate_receipt_data(session):
    """Generate receipt data for printing"""
    try:
        orders = session.get_session_orders()
        
        receipt_data = {
            'restaurant_info': {
                'name': 'Hotel Management Restaurant',
                'address': 'Your Restaurant Address',
                'phone': 'Your Phone Number',
                'gst_number': 'Your GST Number'
            },
            'receipt_details': {
                'receipt_number': session.receipt_number,
                'table_number': session.table.table_number,
                'date': session.created_at.strftime('%Y-%m-%d'),
                'time': session.created_at.strftime('%H:%M:%S'),
                'server': session.created_by.get_full_name() if session.created_by else 'System'
            },
            'items': [
                {
                    'name': order.menu_item.name,
                    'quantity': order.quantity,
                    'unit_price': float(order.unit_price),
                    'total_price': float(order.total_price),
                    'notes': order.special_instructions
                }
                for order in orders
            ],
            'totals': {
                'subtotal': float(session.subtotal_amount),
                'discount': float(session.discount_amount),
                'tax': float(session.tax_amount),
                'service_charge': float(session.service_charge),
                'final_amount': float(session.final_amount)
            },
            'payment': {
                'method': session.payment_method,
                'status': session.payment_status
            },
            'notes': session.notes,
            'admin_notes': session.admin_notes,
            'timestamp': timezone.now().isoformat()
        }
        
        return receipt_data
        
    except Exception as e:
        logger.error(f"Error generating receipt data: {e}")
        return None

def calculate_gst_breakdown(amount, gst_rate=0.05):
    """Calculate GST breakdown for billing"""
    try:
        gst_amount = amount * Decimal(str(gst_rate))
        cgst = gst_amount / 2  # Central GST
        sgst = gst_amount / 2  # State GST
        
        return {
            'total_gst': float(gst_amount),
            'cgst': float(cgst),
            'sgst': float(sgst),
            'gst_rate': float(gst_rate * 100)
        }
    except Exception as e:
        logger.error(f"Error calculating GST: {e}")
        return {
            'total_gst': 0.0,
            'cgst': 0.0,
            'sgst': 0.0,
            'gst_rate': 0.0
        }

def validate_table_operations(table, operation):
    """Validate table operations based on current state"""
    try:
        validations = {
            'occupy': {
                'allowed_statuses': ['free', 'reserved'],
                'message': 'Table must be free or reserved to occupy'
            },
            'free': {
                'allowed_statuses': ['occupied', 'cleaning'],
                'message': 'Can only free occupied or cleaning tables'
            },
            'reserve': {
                'allowed_statuses': ['free'],
                'message': 'Can only reserve free tables'
            },
            'clean': {
                'allowed_statuses': ['free'],
                'message': 'Can only clean free tables'
            },
            'maintenance': {
                'allowed_statuses': ['free', 'cleaning'],
                'message': 'Can only put free or cleaning tables under maintenance'
            },
            'delete': {
                'allowed_statuses': ['free'],
                'additional_checks': lambda t: t.get_active_orders().count() == 0,
                'message': 'Can only delete free tables with no active orders'
            }
        }
        
        validation = validations.get(operation)
        if not validation:
            return False, 'Unknown operation'
        
        if table.status not in validation['allowed_statuses']:
            return False, validation['message']
        
        # Additional checks if specified
        if 'additional_checks' in validation:
            if not validation['additional_checks'](table):
                return False, validation['message']
        
        return True, 'Operation allowed'
        
    except Exception as e:
        logger.error(f"Error validating table operation: {e}")
        return False, 'Validation error'

def get_order_status_history(order):
    """Get status change history for an order"""
    try:
        history = []
        
        if order.created_at:
            history.append({
                'status': 'pending',
                'timestamp': order.created_at,
                'user': order.created_by.get_full_name() if order.created_by else 'System'
            })
        
        if order.confirmed_at:
            history.append({
                'status': 'confirmed',
                'timestamp': order.confirmed_at,
                'user': order.confirmed_by.get_full_name() if order.confirmed_by else 'System'
            })
        
        if order.preparation_started_at:
            history.append({
                'status': 'preparing',
                'timestamp': order.preparation_started_at,
                'user': order.prepared_by.get_full_name() if order.prepared_by else 'System'
            })
        
        if order.ready_at:
            history.append({
                'status': 'ready',
                'timestamp': order.ready_at,
                'user': 'Kitchen'
            })
        
        if order.served_at:
            history.append({
                'status': 'served',
                'timestamp': order.served_at,
                'user': order.served_by.get_full_name() if order.served_by else 'System'
            })
        
        return history
        
    except Exception as e:
        logger.error(f"Error getting order status history: {e}")
        return []

def send_notification(notification_type, data, recipients=None):
    """Send notifications to staff"""
    try:
        # This is a placeholder for notification system
        # You can integrate with email, SMS, or push notification services
        
        notification_data = {
            'type': notification_type,
            'data': data,
            'timestamp': timezone.now().isoformat(),
            'recipients': recipients or []
        }
        
        # Store in cache for now
        cache_key = f"notification_{timezone.now().timestamp()}"
        cache.set(cache_key, notification_data, timeout=3600)
        
        logger.info(f"Notification sent: {notification_type}")
        
    except Exception as e:
        logger.error(f"Error sending notification: {e}")

def cleanup_old_data():
    """Cleanup old data periodically"""
    try:
        from .models import OfflineOrderBackup
        
        # Clean up processed offline orders older than 7 days
        cutoff_date = timezone.now() - timezone.timedelta(days=7)
        
        deleted_count = OfflineOrderBackup.objects.filter(
            is_processed=True,
            processed_at__lt=cutoff_date
        ).delete()[0]
        
        # Clear old cache entries
        # This would need to be implemented based on your cache backend
        
        logger.info(f"Cleaned up {deleted_count} old offline order backups")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

def get_system_health():
    """Get system health information"""
    try:
        from .models import Order, Table, OrderSession, OfflineOrderBackup
        
        health_data = {
            'database': {
                'status': 'healthy',
                'active_orders': Order.objects.filter(
                    status__in=['pending', 'preparing', 'ready']
                ).count(),
                'occupied_tables': Table.objects.filter(status='occupied').count(),
                'active_sessions': OrderSession.objects.filter(is_active=True).count()
            },
            'kds': {
                'connected': is_kds_connected(),
                'offline_orders': OfflineOrderBackup.objects.filter(
                    is_processed=False
                ).count()
            },
            'cache': {
                'status': 'healthy' if cache.get('health_check') else 'warning'
            },
            'timestamp': timezone.now().isoformat()
        }
        
        # Set health check cache
        cache.set('health_check', True, timeout=300)  # 5 minutes
        
        return health_data
        
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        return {
            'status': 'error',
            'message': str(e),
            'timestamp': timezone.now().isoformat()
        }

# Utility functions for color coding and formatting
def get_order_priority_color(priority):
    """Get color coding for order priority"""
    colors = {
        'low': '#6B7280',     # Gray
        'normal': '#3B82F6',  # Blue
        'high': '#F59E0B',    # Orange
        'urgent': '#EF4444'   # Red
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

def format_currency(amount):
    """Format currency for display"""
    try:
        return f"₹{float(amount):,.2f}"
    except (ValueError, TypeError):
        return "₹0.00"
