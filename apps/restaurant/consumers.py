# apps/restaurant/consumers.py - WebSocket Consumers for Real-time Updates
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import Order, Table, KitchenDisplaySettings
from .serializers import OrderSerializer, TableSerializer
import logging

logger = logging.getLogger(__name__)

class KitchenDisplayConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for Kitchen Display System"""

    async def connect(self):
        """Handle WebSocket connection"""
        self.room_name = 'kitchen_display'
        self.room_group_name = f'kds_{self.room_name}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Send initial data
        await self.send_initial_data()
        logger.info(f"KDS WebSocket connected: {self.channel_name}")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        logger.info(f"KDS WebSocket disconnected: {self.channel_name}")

    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')

            if message_type == 'update_order_status':
                await self.handle_order_status_update(text_data_json)
            elif message_type == 'request_refresh':
                await self.send_initial_data()
            elif message_type == 'toggle_audio':
                await self.handle_audio_toggle(text_data_json)
            else:
                logger.warning(f"Unknown message type: {message_type}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")

    async def handle_order_status_update(self, data):
        """Handle order status updates from kitchen staff"""
        order_id = data.get('order_id')
        new_status = data.get('status')
        user_id = data.get('user_id')

        if not all([order_id, new_status]):
            return

        try:
            # Update order status
            await self.update_order_status(order_id, new_status, user_id)

            # Broadcast update to all KDS clients
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'order_status_updated',
                    'order_id': order_id,
                    'status': new_status,
                    'timestamp': await self.get_current_timestamp()
                }
            )

        except Exception as e:
            logger.error(f"Error updating order status: {e}")

    async def handle_audio_toggle(self, data):
        """Handle audio notification toggle"""
        enabled = data.get('enabled', True)

        # Update settings
        await self.update_audio_settings(enabled)

        # Broadcast to all KDS clients
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'audio_settings_updated',
                'enabled': enabled
            }
        )

    async def send_initial_data(self):
        """Send initial data when client connects"""
        try:
            orders = await self.get_active_orders()
            tables = await self.get_tables_status()
            settings = await self.get_kds_settings()

            await self.send(text_data=json.dumps({
                'type': 'initial_data',
                'orders': orders,
                'tables': tables,
                'settings': settings,
                'timestamp': await self.get_current_timestamp()
            }))

        except Exception as e:
            logger.error(f"Error sending initial data: {e}")

    # WebSocket event handlers
    async def new_order_notification(self, event):
        """Handle new order notifications"""
        await self.send(text_data=json.dumps({
            'type': 'new_order',
            'order': event['order'],
            'audio_enabled': event.get('audio_enabled', True),
            'timestamp': event['timestamp']
        }))

    async def order_status_updated(self, event):
        """Handle order status update notifications"""
        await self.send(text_data=json.dumps({
            'type': 'order_updated',
            'order_id': event['order_id'],
            'status': event['status'],
            'timestamp': event['timestamp']
        }))

    async def order_cancelled(self, event):
        """Handle order cancellation notifications"""
        await self.send(text_data=json.dumps({
            'type': 'order_cancelled',
            'order_id': event['order_id'],
            'timestamp': event['timestamp']
        }))

    async def table_status_updated(self, event):
        """Handle table status update notifications"""
        await self.send(text_data=json.dumps({
            'type': 'table_updated',
            'table': event['table'],
            'timestamp': event['timestamp']
        }))

    async def audio_settings_updated(self, event):
        """Handle audio settings update notifications"""
        await self.send(text_data=json.dumps({
            'type': 'audio_updated',
            'enabled': event['enabled']
        }))

    # Database operations
    @database_sync_to_async
    def get_active_orders(self):
        """Get all active orders for KDS"""
        from .serializers import OrderKDSSerializer

        orders = Order.objects.select_related(
            'table', 'menu_item', 'menu_item__category', 'created_by'
        ).filter(
            status__in=['pending', 'confirmed', 'preparing', 'ready']
        ).order_by('created_at')

        return OrderKDSSerializer(orders, many=True).data

    @database_sync_to_async
    def get_tables_status(self):
        """Get current table status"""
        tables = Table.objects.filter(is_active=True).order_by('table_number')
        return TableSerializer(tables, many=True).data

    @database_sync_to_async
    def get_kds_settings(self):
        """Get KDS settings"""
        try:
            settings = KitchenDisplaySettings.objects.first()
            if settings:
                return {
                    'audio_enabled': settings.audio_enabled,
                    'auto_refresh_interval': settings.auto_refresh_interval,
                    'display_completed_orders': settings.display_completed_orders,
                    'priority_color_coding': settings.priority_color_coding,
                    'show_preparation_time': settings.show_preparation_time
                }
        except Exception:
            pass

        return {
            'audio_enabled': True,
            'auto_refresh_interval': 30,
            'display_completed_orders': False,
            'priority_color_coding': True,
            'show_preparation_time': True
        }

    @database_sync_to_async
    def update_order_status(self, order_id, new_status, user_id=None):
        """Update order status in database"""
        try:
            order = Order.objects.get(id=order_id)
            old_status = order.status

            if user_id:
                from apps.users.models import CustomUser
                user = CustomUser.objects.get(id=user_id)
                order.update_status(new_status, user)
            else:
                order.update_status(new_status)

            return True
        except Exception as e:
            logger.error(f"Error updating order status: {e}")
            return False

    @database_sync_to_async
    def update_audio_settings(self, enabled):
        """Update audio settings"""
        try:
            settings, created = KitchenDisplaySettings.objects.get_or_create(
                name='default',
                defaults={'audio_enabled': enabled}
            )
            if not created:
                settings.audio_enabled = enabled
                settings.save()
            return True
        except Exception as e:
            logger.error(f"Error updating audio settings: {e}")
            return False

    @database_sync_to_async
    def get_current_timestamp(self):
        """Get current timestamp"""
        from django.utils import timezone
        return timezone.now().isoformat()


class OrderingConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for mobile ordering interface"""

    async def connect(self):
        """Handle WebSocket connection"""
        self.room_name = 'ordering'
        self.room_group_name = f'ordering_{self.room_name}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Send initial data
        await self.send_initial_ordering_data()
        logger.info(f"Ordering WebSocket connected: {self.channel_name}")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        logger.info(f"Ordering WebSocket disconnected: {self.channel_name}")

    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')

            if message_type == 'request_tables':
                await self.send_tables_update()
            elif message_type == 'request_menu':
                await self.send_menu_update()
            else:
                logger.warning(f"Unknown ordering message type: {message_type}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")
        except Exception as e:
            logger.error(f"Error handling ordering WebSocket message: {e}")

    async def send_initial_ordering_data(self):
        """Send initial data for ordering interface"""
        try:
            tables = await self.get_available_tables()
            menu = await self.get_menu_items()

            await self.send(text_data=json.dumps({
                'type': 'initial_ordering_data',
                'tables': tables,
                'menu': menu,
                'timestamp': await self.get_current_timestamp()
            }))

        except Exception as e:
            logger.error(f"Error sending initial ordering data: {e}")

    async def send_tables_update(self):
        """Send table status update"""
        try:
            tables = await self.get_available_tables()
            await self.send(text_data=json.dumps({
                'type': 'tables_update',
                'tables': tables,
                'timestamp': await self.get_current_timestamp()
            }))
        except Exception as e:
            logger.error(f"Error sending tables update: {e}")

    async def send_menu_update(self):
        """Send menu update"""
        try:
            menu = await self.get_menu_items()
            await self.send(text_data=json.dumps({
                'type': 'menu_update',
                'menu': menu,
                'timestamp': await self.get_current_timestamp()
            }))
        except Exception as e:
            logger.error(f"Error sending menu update: {e}")

    # WebSocket event handlers
    async def table_status_changed(self, event):
        """Handle table status changes"""
        await self.send(text_data=json.dumps({
            'type': 'table_status_changed',
            'table': event['table'],
            'timestamp': event['timestamp']
        }))

    async def menu_item_updated(self, event):
        """Handle menu item updates"""
        await self.send(text_data=json.dumps({
            'type': 'menu_item_updated',
            'item': event['item'],
            'timestamp': event['timestamp']
        }))

    async def order_confirmed(self, event):
        """Handle order confirmation"""
        await self.send(text_data=json.dumps({
            'type': 'order_confirmed',
            'order_id': event['order_id'],
            'table_id': event['table_id'],
            'timestamp': event['timestamp']
        }))

    # Database operations
    @database_sync_to_async
    def get_available_tables(self):
        """Get available tables"""
        tables = Table.objects.filter(is_active=True).order_by('table_number')
        return TableSerializer(tables, many=True).data

    @database_sync_to_async
    def get_menu_items(self):
        """Get menu items grouped by category"""
        from .serializers import MenuItemSerializer, MenuCategorySerializer
        from .models import MenuCategory

        categories = MenuCategory.objects.filter(is_active=True).prefetch_related('items')

        menu_data = []
        for category in categories:
            items = category.items.filter(is_active=True, availability='available')
            menu_data.append({
                'category': MenuCategorySerializer(category).data,
                'items': MenuItemSerializer(items, many=True).data
            })

        return menu_data

    @database_sync_to_async
    def get_current_timestamp(self):
        """Get current timestamp"""
        from django.utils import timezone
        return timezone.now().isoformat()


class TableManagementConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for table management dashboard"""

    async def connect(self):
        """Handle WebSocket connection"""
        self.room_name = 'table_management'
        self.room_group_name = f'table_mgmt_{self.room_name}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Send initial data
        await self.send_table_status()
        logger.info(f"Table Management WebSocket connected: {self.channel_name}")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        logger.info(f"Table Management WebSocket disconnected: {self.channel_name}")

    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')

            if message_type == 'request_refresh':
                await self.send_table_status()
            elif message_type == 'update_table_status':
                await self.handle_table_status_update(text_data_json)
            else:
                logger.warning(f"Unknown table management message type: {message_type}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")
        except Exception as e:
            logger.error(f"Error handling table management WebSocket message: {e}")

    async def handle_table_status_update(self, data):
        """Handle manual table status updates"""
        table_id = data.get('table_id')
        new_status = data.get('status')

        if not all([table_id, new_status]):
            return

        try:
            await self.update_table_status(table_id, new_status)

            # Broadcast update to all clients
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'table_status_updated',
                    'table_id': table_id,
                    'status': new_status,
                    'timestamp': await self.get_current_timestamp()
                }
            )

        except Exception as e:
            logger.error(f"Error updating table status: {e}")

    async def send_table_status(self):
        """Send current table status"""
        try:
            tables = await self.get_tables_with_orders()

            await self.send(text_data=json.dumps({
                'type': 'table_status',
                'tables': tables,
                'timestamp': await self.get_current_timestamp()
            }))

        except Exception as e:
            logger.error(f"Error sending table status: {e}")

    # WebSocket event handlers
    async def table_status_updated(self, event):
        """Handle table status updates"""
        await self.send(text_data=json.dumps({
            'type': 'table_updated',
            'table_id': event['table_id'],
            'status': event['status'],
            'timestamp': event['timestamp']
        }))

    async def new_order_placed(self, event):
        """Handle new order notifications"""
        await self.send(text_data=json.dumps({
            'type': 'new_order',
            'table_id': event['table_id'],
            'order_count': event['order_count'],
            'timestamp': event['timestamp']
        }))

    # Database operations
    @database_sync_to_async
    def get_tables_with_orders(self):
        """Get tables with their order information"""
        from .serializers import TableWithOrdersSerializer

        tables = Table.objects.filter(is_active=True).prefetch_related(
            'orders__menu_item'
        ).order_by('table_number')

        return TableWithOrdersSerializer(tables, many=True).data

    @database_sync_to_async
    def update_table_status(self, table_id, new_status):
        """Update table status"""
        try:
            table = Table.objects.get(id=table_id)
            table.status = new_status
            table.save()
            return True
        except Exception as e:
            logger.error(f"Error updating table status: {e}")
            return False

    @database_sync_to_async
    def get_current_timestamp(self):
        """Get current timestamp"""
        from django.utils import timezone
        return timezone.now().isoformat()

