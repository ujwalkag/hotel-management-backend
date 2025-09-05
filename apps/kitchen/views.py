from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny  # Kitchen display is public
from django.shortcuts import get_object_or_404
from django.db.models import Q
from datetime import datetime, date

from .models import KitchenOrder, KitchenItemStatus, AudioAlert
from .serializers import KitchenOrderSerializer, KitchenItemStatusSerializer, AudioAlertSerializer

class KitchenDisplayViewSet(viewsets.ModelViewSet):
    """Kitchen Display System ViewSet"""
    queryset = KitchenOrder.objects.all()
    serializer_class = KitchenOrderSerializer
    permission_classes = [AllowAny]  # Kitchen display accessible without auth
    
    def get_queryset(self):
        queryset = KitchenOrder.objects.exclude(status='served')
        status_filter = self.request.query_params.get('status')
        priority = self.request.query_params.get('priority')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if priority:
            queryset = queryset.filter(priority=priority)
            
        return queryset.order_by('priority', 'received_at')

    @action(detail=False, methods=['get'])
    def active_orders(self, request):
        """Get all active orders for kitchen display"""
        orders = KitchenOrder.objects.filter(
            status__in=['received', 'preparing', 'ready']
        ).order_by('priority', 'received_at')
        
        serializer = KitchenOrderSerializer(orders, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update order status from kitchen interface"""
        order = self.get_object()
        new_status = request.data.get('status')
        chef_name = request.data.get('chef_name', '')
        
        if new_status not in dict(KitchenOrder.STATUS_CHOICES):
            return Response(
                {'error': 'Invalid status'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_status = order.status
        
        if new_status == 'preparing':
            order.start_preparation()
            order.assigned_chef = chef_name
        elif new_status == 'ready':
            order.mark_ready()
        elif new_status == 'served':
            order.mark_served()
        else:
            order.status = new_status
            
        order.audio_acknowledged = True
        order.save()
        
        return Response({
            'message': f'Order status updated from {old_status} to {new_status}',
            'order': KitchenOrderSerializer(order).data
        })

    @action(detail=True, methods=['post'])
    def acknowledge_audio(self, request, pk=None):
        """Acknowledge audio alert for order"""
        order = self.get_object()
        order.audio_acknowledged = True
        order.save()
        
        return Response({'message': 'Audio alert acknowledged'})

    @action(detail=False, methods=['get'])
    def kitchen_stats(self, request):
        """Get kitchen performance statistics"""
        today = date.today()
        
        today_orders = KitchenOrder.objects.filter(received_at__date=today)
        
        stats = {
            'date': today,
            'total_orders': today_orders.count(),
            'completed_orders': today_orders.filter(status='served').count(),
            'active_orders': today_orders.exclude(status='served').count(),
            'average_prep_time': 0,
            'orders_by_status': {}
        }
        
        # Calculate average prep time
        completed_orders = today_orders.filter(
            status='served', 
            actual_prep_time__isnull=False
        )
        if completed_orders.exists():
            total_time = sum(order.actual_prep_time for order in completed_orders)
            stats['average_prep_time'] = total_time / completed_orders.count()
        
        # Orders by status
        for status_choice, status_display in KitchenOrder.STATUS_CHOICES:
            count = today_orders.filter(status=status_choice).count()
            stats['orders_by_status'][status_choice] = {
                'display': status_display,
                'count': count
            }
        
        return Response(stats)

class KitchenItemStatusViewSet(viewsets.ModelViewSet):
    """Kitchen Item Status Management"""
    queryset = KitchenItemStatus.objects.all()
    serializer_class = KitchenItemStatusSerializer
    permission_classes = [AllowAny]

    @action(detail=True, methods=['post'])
    def update_item_status(self, request, pk=None):
        """Update individual item status"""
        item = self.get_object()
        new_status = request.data.get('status')
        
        if new_status == 'preparing':
            item.start_preparation()
        elif new_status == 'ready':
            item.mark_ready()
        else:
            item.status = new_status
            item.save()
        
        return Response(KitchenItemStatusSerializer(item).data)

class AudioAlertViewSet(viewsets.ModelViewSet):
    """Audio Alert Configuration"""
    queryset = AudioAlert.objects.filter(is_active=True)
    serializer_class = AudioAlertSerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=['get'])
    def active_alerts(self, request):
        """Get active audio alerts"""
        alerts = AudioAlert.objects.filter(is_active=True).order_by('-priority')
        serializer = AudioAlertSerializer(alerts, many=True)
        return Response(serializer.data)
