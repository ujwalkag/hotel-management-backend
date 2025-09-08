from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q
from .models import RestaurantTable, TableSession, WaiterOrder, WaiterOrderItem, KitchenOrder
from .serializers import (
    RestaurantTableSerializer, WaiterOrderSerializer, KitchenOrderSerializer, MenuItemSerializer
)
from apps.menu.models import MenuItem

class RestaurantTableViewSet(viewsets.ModelViewSet):
    queryset = RestaurantTable.objects.all()
    serializer_class = RestaurantTableSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def start_session(self, request, pk=None):
        table = self.get_object()
        customer_count = request.data.get('customer_count', 1)
        waiter = request.user if request.user.role == 'waiter' else None

        session_id = table.start_new_session(customer_count, waiter)
        if session_id:
            return Response({
                'success': True,
                'session_id': session_id,
                'message': 'Table session started successfully'
            })
        else:
            return Response({
                'success': False,
                'message': 'Cannot start session - table not available'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def available(self, request):
        tables = RestaurantTable.objects.filter(current_status='available', is_active=True)
        serializer = self.get_serializer(tables, many=True)
        return Response(serializer.data)

class WaiterOrderViewSet(viewsets.ModelViewSet):
    queryset = WaiterOrder.objects.all()
    serializer_class = WaiterOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = WaiterOrder.objects.all()
        if self.request.user.role == 'waiter':
            queryset = queryset.filter(waiter=self.request.user)
        return queryset

    @action(detail=False, methods=['get'])
    def active_orders(self, request):
        orders = self.get_queryset().filter(
            status__in=['pending', 'confirmed', 'preparing', 'ready']
        ).order_by('-created_at')
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_item(self, request, pk=None):
        order = self.get_object()
        menu_item_id = request.data.get('menu_item_id')
        quantity = int(request.data.get('quantity', 1))
        customizations = request.data.get('customizations', {})
        special_instructions = request.data.get('special_instructions', '')

        try:
            menu_item = MenuItem.objects.get(id=menu_item_id, available=True)

            WaiterOrderItem.objects.create(
                waiter_order=order,
                menu_item=menu_item,
                quantity=quantity,
                unit_price=menu_item.price,
                item_customizations=customizations,
                special_instructions=special_instructions
            )

            order.calculate_totals()

            return Response({
                'success': True,
                'message': 'Item added to order successfully'
            })

        except MenuItem.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Menu item not found or not available'
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def confirm_order(self, request, pk=None):
        order = self.get_object()
        if order.confirm_order():
            return Response({
                'success': True,
                'message': 'Order confirmed and sent to kitchen'
            })
        else:
            return Response({
                'success': False,
                'message': 'Cannot confirm order'
            }, status=status.HTTP_400_BAD_REQUEST)

class KitchenOrderViewSet(viewsets.ModelViewSet):
    queryset = KitchenOrder.objects.all()
    serializer_class = KitchenOrderSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def active_orders(self, request):
        orders = KitchenOrder.objects.filter(
            status__in=['received', 'preparing']
        ).order_by('priority', 'received_at')
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def start_preparation(self, request, pk=None):
        order = self.get_object()
        cook_name = request.data.get('cook_name', '')
        order.start_preparation(cook_name)
        return Response({
            'success': True,
            'message': 'Order preparation started'
        })

    @action(detail=True, methods=['post'])
    def mark_ready(self, request, pk=None):
        order = self.get_object()
        order.mark_ready()
        return Response({
            'success': True,
            'message': 'Order marked as ready'
        })

class MenuItemViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MenuItem.objects.filter(available=True)
    serializer_class = MenuItemSerializer
    permission_classes = [IsAuthenticated]
