
# WAITER MOBILE API

# apps/tables/mobile_views.py - Mobile Waiter API Views
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import RestaurantTable, TableOrder, OrderItem
from .serializers import MobileTableSerializer, MobileOrderSerializer
from apps.menu.models import MenuItem

class MobileWaiterViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def tables_layout(self, request):
        """Get all tables with their current status for mobile layout"""
        tables = RestaurantTable.objects.all().order_by('table_number')
        serializer = MobileTableSerializer(tables, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def table_details(self, request, pk=None):
        """Get specific table details including current orders"""
        table = get_object_or_404(RestaurantTable, pk=pk)
        current_order = table.current_order

        data = {
            'table': MobileTableSerializer(table).data,
            'current_order': MobileOrderSerializer(current_order).data if current_order else None,
        }
        return Response(data)

    @action(detail=False, methods=['post'])
    def create_order(self, request):
        """Create new order for a table"""
        data = request.data
        table_id = data.get('table_id')
        items = data.get('items', [])

        if not items:
            return Response({'error': 'No items provided'}, status=status.HTTP_400_BAD_REQUEST)

        table = get_object_or_404(RestaurantTable, pk=table_id)

        # Create order
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
            menu_item = get_object_or_404(MenuItem, pk=item_data['menu_item_id'])

            order_item = OrderItem.objects.create(
                table_order=order,
                menu_item=menu_item,
                quantity=item_data['quantity'],
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
            'order': MobileOrderSerializer(order).data,
            'message': 'Order created successfully'
        })

    @action(detail=False, methods=['post'])
    def add_items_to_order(self, request):
        """Add additional items to existing order"""
        data = request.data
        order_id = data.get('order_id')
        items = data.get('items', [])

        order = get_object_or_404(TableOrder, pk=order_id)

        for item_data in items:
            menu_item = get_object_or_404(MenuItem, pk=item_data['menu_item_id'])

            OrderItem.objects.create(
                table_order=order,
                menu_item=menu_item,
                quantity=item_data['quantity'],
                price=menu_item.price,
                special_instructions=item_data.get('special_instructions', '')
            )

        # Recalculate total
        order.calculate_total()

        return Response({
            'success': True,
            'order': MobileOrderSerializer(order).data,
            'message': 'Items added successfully'
        })

    @action(detail=False, methods=['get'])
    def my_orders(self, request):
        """Get orders assigned to current waiter"""
        orders = TableOrder.objects.filter(
            waiter=request.user,
            status__in=['pending', 'in_progress']
        ).order_by('-created_at')

        serializer = MobileOrderSerializer(orders, many=True)
        return Response(serializer.data)

