
# apps/kitchen/views.py - UPDATED WITH FULL AUDIO ALERT SYSTEM
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny  # Kitchen display is public
from django.shortcuts import get_object_or_404
from django.db.models import Q
from datetime import datetime, date
from django.utils import timezone

from .models import KitchenOrder, KitchenItemStatus, AudioAlert
from .serializers import KitchenOrderSerializer, KitchenItemStatusSerializer, AudioAlertSerializer
from apps.tables.models import TableOrder, OrderItem

class KitchenDisplayViewSet(viewsets.ModelViewSet):
    """
    UPDATED Kitchen Display System with Enhanced Audio Alerts
    Shows orders from mobile ordering system with audio notifications
    """
    queryset = KitchenOrder.objects.all()
    serializer_class = KitchenOrderSerializer
    permission_classes = [AllowAny]  # Kitchen display accessible without auth

    def get_queryset(self):
        """Get kitchen orders with filtering options"""
        queryset = KitchenOrder.objects.exclude(status='served')
        status_filter = self.request.query_params.get('status')
        priority = self.request.query_params.get('priority')
        table_number = self.request.query_params.get('table')

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if priority:
            queryset = queryset.filter(priority=priority)
        if table_number:
            queryset = queryset.filter(
                table_order__table__table_number=table_number
            )

        return queryset.order_by('priority', 'received_at')

    @action(detail=False, methods=['get'])
    def active_orders_with_audio(self, request):
        """
        GET /api/kitchen/active_orders_with_audio/
        Get all active kitchen orders with audio alert information
        This is the main kitchen display endpoint
        """
        # Get active table orders that need kitchen attention
        table_orders = TableOrder.objects.filter(
            status__in=['pending', 'in_progress'],
            is_in_enhanced_billing=True
        ).select_related('table', 'waiter').prefetch_related('items__menu_item').order_by('created_at')

        kitchen_orders_data = []
        audio_alerts = []

        for table_order in table_orders:
            # Get order items that need kitchen preparation
            pending_items = table_order.items.filter(
                status__in=['pending', 'preparing']
            )

            if not pending_items.exists():
                continue  # Skip orders with no pending items

            # Calculate time since order
            time_since_order = (timezone.now() - table_order.created_at).total_seconds() / 60

            # Determine priority based on time and customer count
            if time_since_order > 30:
                priority = 4  # Urgent
                priority_color = 'red'
            elif time_since_order > 20:
                priority = 3  # High
                priority_color = 'orange'
            else:
                priority = 2  # Normal
                priority_color = 'green'

            # Prepare items list
            items_data = []
            for item in pending_items:
                items_data.append({
                    'id': item.id,
                    'name_en': item.menu_item.name_en,
                    'name_hi': item.menu_item.name_hi,
                    'quantity': item.quantity,
                    'status': item.status,
                    'special_instructions': item.special_instructions,
                    'kitchen_notes': item.kitchen_notes,
                    'estimated_prep_time': item.estimated_prep_time,
                    'time_since_ordered': int((timezone.now() - item.order_time).total_seconds() / 60)
                })

            order_data = {
                'id': table_order.id,
                'order_number': table_order.order_number,
                'table_number': table_order.table.table_number,
                'table_capacity': table_order.table.capacity,
                'customer_name': table_order.customer_name,
                'customer_count': table_order.customer_count,
                'waiter_name': table_order.waiter.email if table_order.waiter else 'System',
                'status': table_order.status,
                'priority': priority,
                'priority_color': priority_color,
                'time_since_order': int(time_since_order),
                'special_instructions': table_order.special_instructions,
                'created_at': table_order.created_at.isoformat(),
                'items': items_data,
                'total_items': len(items_data)
            }

            kitchen_orders_data.append(order_data)

            # Check if this order needs audio alert
            if not hasattr(table_order, '_audio_played'):
                # New order - needs audio alert
                audio_alerts.append({
                    'type': 'new_order',
                    'order_id': table_order.id,
                    'table_number': table_order.table.table_number,
                    'priority': priority,
                    'message': f"New order for Table {table_order.table.table_number}",
                    'sound_file': 'new_order_alert.mp3',
                    'repeat_count': 2 if priority >= 3 else 1
                })

        return Response({
            'status': 'success',
            'kitchen_orders': kitchen_orders_data,
            'total_active_orders': len(kitchen_orders_data),
            'audio_alerts': audio_alerts,
            'timestamp': timezone.now().isoformat(),
            'kitchen_stats': {
                'pending_orders': len([o for o in kitchen_orders_data if o['status'] == 'pending']),
                'in_progress_orders': len([o for o in kitchen_orders_data if o['status'] == 'in_progress']),
                'urgent_orders': len([o for o in kitchen_orders_data if o['priority'] >= 4]),
                'high_priority_orders': len([o for o in kitchen_orders_data if o['priority'] == 3])
            }
        })

    @action(detail=False, methods=['post'])
    def update_item_status(self, request):
        """
        POST /api/kitchen/update_item_status/
        Update individual item status from kitchen interface
        Body: {
            "order_item_id": 123,
            "new_status": "preparing",  // pending, preparing, ready, served
            "chef_name": "Chef John",
            "kitchen_notes": "Extra spicy"
        }
        """
        order_item_id = request.data.get('order_item_id')
        new_status = request.data.get('new_status')
        chef_name = request.data.get('chef_name', '')
        kitchen_notes = request.data.get('kitchen_notes', '')

        if not all([order_item_id, new_status]):
            return Response({
                'error': 'order_item_id and new_status are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        valid_statuses = ['pending', 'preparing', 'ready', 'served', 'cancelled']
        if new_status not in valid_statuses:
            return Response({
                'error': f'Invalid status. Must be one of: {valid_statuses}'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            order_item = OrderItem.objects.get(id=order_item_id)
            old_status = order_item.status

            # Update item status using model methods
            if new_status == 'preparing':
                order_item.start_preparation()
            elif new_status == 'ready':
                order_item.mark_ready()
            elif new_status == 'served':
                order_item.mark_served()
            else:
                order_item.status = new_status
                order_item.save()

            # Update kitchen notes if provided
            if kitchen_notes:
                order_item.kitchen_notes = kitchen_notes
                order_item.save()

            # Check if all items in the order are ready/served
            table_order = order_item.table_order
            all_items = table_order.items.all()
            all_ready = all(item.status in ['ready', 'served'] for item in all_items)

            if all_ready and table_order.status == 'in_progress':
                table_order.status = 'ready'
                table_order.save()
            elif new_status == 'preparing' and table_order.status == 'pending':
                table_order.status = 'in_progress'
                table_order.save()

            # Prepare audio alert if item is ready
            audio_alert = None
            if new_status == 'ready':
                # Check if all items for this table are ready
                pending_items = table_order.items.filter(status__in=['pending', 'preparing']).count()
                if pending_items == 0:
                    audio_alert = {
                        'type': 'order_ready',
                        'order_id': table_order.id,
                        'table_number': table_order.table.table_number,
                        'message': f"Order ready for Table {table_order.table.table_number}",
                        'sound_file': 'order_ready_alert.mp3'
                    }

            return Response({
                'status': 'success',
                'message': f'Item status updated from {old_status} to {new_status}',
                'order_item': {
                    'id': order_item.id,
                    'name': order_item.menu_item.name_en,
                    'status': order_item.status,
                    'kitchen_notes': order_item.kitchen_notes
                },
                'table_order_status': table_order.status,
                'audio_alert': audio_alert
            })

        except OrderItem.DoesNotExist:
            return Response({
                'error': 'Order item not found'
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def mark_order_complete(self, request):
        """
        POST /api/kitchen/mark_order_complete/
        Mark entire table order as complete
        Body: {
            "table_order_id": 123,
            "chef_name": "Chef John"
        }
        """
        table_order_id = request.data.get('table_order_id')
        chef_name = request.data.get('chef_name', '')

        if not table_order_id:
            return Response({
                'error': 'table_order_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            table_order = TableOrder.objects.get(id=table_order_id)

            # Mark all items as ready
            for item in table_order.items.filter(status__in=['pending', 'preparing']):
                item.mark_ready()

            # Mark order as completed
            table_order.mark_completed()

            return Response({
                'status': 'success',
                'message': f'Order {table_order.order_number} marked as complete',
                'order': {
                    'id': table_order.id,
                    'order_number': table_order.order_number,
                    'table_number': table_order.table.table_number,
                    'status': table_order.status,
                    'completed_at': table_order.completed_at.isoformat()
                },
                'audio_alert': {
                    'type': 'order_complete',
                    'order_id': table_order.id,
                    'table_number': table_order.table.table_number,
                    'message': f"Order complete for Table {table_order.table.table_number}",
                    'sound_file': 'order_complete_alert.mp3'
                }
            })

        except TableOrder.DoesNotExist:
            return Response({
                'error': 'Table order not found'
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def acknowledge_audio_alert(self, request):
        """
        POST /api/kitchen/acknowledge_audio_alert/
        Acknowledge audio alert to stop repeating
        Body: {
            "order_id": 123,
            "alert_type": "new_order"
        }
        """
        order_id = request.data.get('order_id')
        alert_type = request.data.get('alert_type')

        if not order_id:
            return Response({
                'error': 'order_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            table_order = TableOrder.objects.get(id=order_id)

            # Mark audio as acknowledged (you can implement this in your model)
            # For now, we'll just return success

            return Response({
                'status': 'success',
                'message': f'Audio alert acknowledged for order {table_order.order_number}'
            })

        except TableOrder.DoesNotExist:
            return Response({
                'error': 'Order not found'
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def kitchen_performance_stats(self, request):
        """
        GET /api/kitchen/kitchen_performance_stats/
        Get kitchen performance statistics for today
        """
        today = date.today()

        # Get today's orders
        today_orders = TableOrder.objects.filter(
            created_at__date=today,
            status__in=['completed', 'billed']
        )

        # Calculate stats
        total_orders = today_orders.count()
        total_items = sum(order.items.count() for order in today_orders)

        # Calculate average preparation time
        completed_items = []
        for order in today_orders:
            for item in order.items.filter(actual_prep_time__isnull=False):
                completed_items.append(item.actual_prep_time)

        avg_prep_time = sum(completed_items) / len(completed_items) if completed_items else 0

        # Current active orders
        active_orders = TableOrder.objects.filter(
            status__in=['pending', 'in_progress'],
            is_in_enhanced_billing=True
        ).count()

        # Orders by status
        status_counts = {}
        for status_choice, _ in TableOrder.STATUS_CHOICES:
            count = TableOrder.objects.filter(
                created_at__date=today,
                status=status_choice
            ).count()
            status_counts[status_choice] = count

        return Response({
            'status': 'success',
            'date': today.isoformat(),
            'stats': {
                'total_orders_today': total_orders,
                'total_items_prepared': total_items,
                'active_orders': active_orders,
                'average_prep_time_minutes': round(avg_prep_time, 2),
                'orders_by_status': status_counts
            },
            'timestamp': timezone.now().isoformat()
        })

    @action(detail=False, methods=['get'])
    def audio_alerts_config(self, request):
        """
        GET /api/kitchen/audio_alerts_config/
        Get audio alert configuration
        """
        alerts = AudioAlert.objects.filter(is_active=True).order_by('-priority')

        config = {
            'alerts': [],
            'global_settings': {
                'audio_enabled': True,
                'default_volume': 80,
                'repeat_interval_seconds': 5,
                'max_repeat_count': 3
            }
        }

        for alert in alerts:
            config['alerts'].append({
                'type': alert.alert_type,
                'name': alert.name,
                'description': alert.description,
                'audio_file': alert.audio_file.url if alert.audio_file else None,
                'text_to_speech': alert.text_to_speech,
                'volume': alert.volume,
                'repeat_count': alert.repeat_count,
                'repeat_interval': alert.repeat_interval,
                'priority': alert.priority
            })

        return Response(config)

    @action(detail=False, methods=['post'])
    def update_audio_settings(self, request):
        """
        POST /api/kitchen/update_audio_settings/
        Update audio alert settings
        Body: {
            "audio_enabled": true,
            "default_volume": 80,
            "alert_type": "new_order",
            "volume": 90,
            "repeat_count": 2
        }
        """
        audio_enabled = request.data.get('audio_enabled')
        default_volume = request.data.get('default_volume')
        alert_type = request.data.get('alert_type')

        if alert_type:
            # Update specific alert settings
            try:
                alert = AudioAlert.objects.get(alert_type=alert_type)
                if 'volume' in request.data:
                    alert.volume = request.data['volume']
                if 'repeat_count' in request.data:
                    alert.repeat_count = request.data['repeat_count']
                if 'repeat_interval' in request.data:
                    alert.repeat_interval = request.data['repeat_interval']
                alert.save()

                return Response({
                    'status': 'success',
                    'message': f'Updated settings for {alert_type} alerts'
                })
            except AudioAlert.DoesNotExist:
                return Response({
                    'error': 'Alert type not found'
                }, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'status': 'success',
            'message': 'Audio settings updated'
        })

