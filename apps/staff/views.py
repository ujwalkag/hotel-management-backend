
# apps/staff/views.py - Complete Staff Management Views
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from .models import StaffProfile, AttendanceRecord, AdvancePayment
from .serializers import StaffProfileSerializer, AttendanceRecordSerializer, AdvancePaymentSerializer
from apps.users.models import CustomUser
import json
from datetime import datetime, timedelta

class StaffProfileViewSet(viewsets.ModelViewSet):
    queryset = StaffProfile.objects.all()
    serializer_class = StaffProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        department = self.request.query_params.get('department', None)
        status = self.request.query_params.get('status', None)

        if department:
            queryset = queryset.filter(department=department)
        if status:
            queryset = queryset.filter(employment_status=status)

        return queryset.order_by('-created_at')

class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = AttendanceRecord.objects.all()
    serializer_class = AttendanceRecordSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        staff_id = self.request.query_params.get('staff_id', None)
        month = self.request.query_params.get('month', None)
        year = self.request.query_params.get('year', None)
        date = self.request.query_params.get('date', None)

        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)
        if month and year:
            queryset = queryset.filter(date__month=month, date__year=year)
        if date:
            queryset = queryset.filter(date=date)

        return queryset.order_by('-date')

    @action(detail=False, methods=['post'])
    def mark_attendance(self, request):
        """Mark attendance for a staff member"""
        staff_id = request.data.get('staff_id')
        status = request.data.get('status')
        date = request.data.get('date', timezone.now().date())

        if not staff_id or not status:
            return Response({'error': 'staff_id and status are required'}, 
                          status=status.HTTP_400_BAD_REQUEST)

        try:
            staff = get_object_or_404(StaffProfile, id=staff_id)

            # Check if attendance already marked for today
            attendance, created = AttendanceRecord.objects.get_or_create(
                staff=staff,
                date=date,
                defaults={
                    'status': status,
                    'created_by': request.user
                }
            )

            if not created:
                attendance.status = status
                attendance.save()

            # Set check-in time if present
            if status == 'present' and not attendance.check_in_time:
                attendance.check_in_time = timezone.now().time()
                attendance.save()

            serializer = self.get_serializer(attendance)
            return Response(serializer.data)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Enhanced Tables Views for Mobile Waiter
from apps.tables.models import RestaurantTable, TableOrder, OrderItem
from apps.menu.models import MenuItem

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_tables_layout(request):
    """Get all tables with current status for mobile waiter interface"""
    tables = RestaurantTable.objects.all().order_by('table_number')

    table_data = []
    for table in tables:
        current_order = table.orders.filter(status__in=['pending', 'in_progress']).first()
        table_data.append({
            'id': table.id,
            'table_number': table.table_number,
            'capacity': table.capacity,
            'location': table.location,
            'is_occupied': table.is_occupied,
            'is_active': table.is_active,
            'current_order': {
                'id': current_order.id,
                'order_number': current_order.order_number,
                'customer_name': current_order.customer_name,
                'status': current_order.status,
                'total_amount': float(current_order.total_amount)
            } if current_order else None
        })

    return Response(table_data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_waiter_order(request):
    """Create order from mobile waiter interface"""
    data = request.data
    table_id = data.get('table_id') or data.get('table')
    items = data.get('items', [])

    if not table_id or not items:
        return Response({'error': 'table_id and items are required'}, 
                       status=status.HTTP_400_BAD_REQUEST)

    try:
        table = get_object_or_404(RestaurantTable, id=table_id)

        # Create the order
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
            menu_item_id = item_data.get('menu_item_id') or item_data.get('menu_item')
            menu_item = get_object_or_404(MenuItem, id=menu_item_id)

            order_item = OrderItem.objects.create(
                table_order=order,
                menu_item=menu_item,
                quantity=item_data.get('quantity', 1),
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
            'order_id': order.id,
            'order_number': order.order_number,
            'total_amount': float(order.total_amount),
            'message': 'Order created successfully'
        })

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Enhanced Billing Views
from apps.bills.models import Bill, BillItem
from decimal import Decimal

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_orders_ready_for_billing(request):
    """Get orders that are ready for billing"""
    # Get completed orders that haven't been billed yet
    orders = TableOrder.objects.filter(
        status__in=['completed', 'ready']
    ).exclude(status='billed').select_related('table', 'waiter').prefetch_related('items__menu_item')

    order_data = []
    for order in orders:
        order_data.append({
            'id': order.id,
            'order_number': order.order_number,
            'table_id': order.table.id,
            'table_number': order.table.table_number,
            'customer_name': order.customer_name,
            'customer_phone': order.customer_phone,
            'waiter_name': order.waiter.email if order.waiter else 'Unknown',
            'total_amount': float(order.total_amount),
            'items_count': order.items.count(),
            'created_at': order.created_at.isoformat(),
            'status': order.status,
            'items': [
                {
                    'id': item.id,
                    'name': item.menu_item.name_en,
                    'name_hi': item.menu_item.name_hi,
                    'quantity': item.quantity,
                    'price': float(item.price),
                    'total': float(item.total_price),
                    'menu_item': {
                        'id': item.menu_item.id,
                        'name_en': item.menu_item.name_en,
                        'name_hi': item.menu_item.name_hi,
                        'price': float(item.menu_item.price)
                    }
                }
                for item in order.items.all()
            ]
        })

    return Response(order_data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_bill_from_order(request):
    """Generate bill from completed order with GST calculation"""
    data = request.data
    order_id = data.get('order_id')
    payment_method = data.get('payment_method', 'cash')
    discount_percentage = Decimal(str(data.get('discount_percentage', '0')))

    if not order_id:
        return Response({'error': 'order_id is required'}, 
                       status=status.HTTP_400_BAD_REQUEST)

    try:
        order = get_object_or_404(TableOrder, id=order_id)

        # Check if order is ready for billing
        if order.status not in ['completed', 'ready']:
            return Response({
                'error': 'Order must be completed before billing'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create bill using existing structure
        bill = Bill.objects.create(
            user=request.user,
            bill_type='restaurant',
            customer_name=order.customer_name or 'Guest',
            customer_phone=order.customer_phone or 'N/A',
            payment_method=payment_method
        )

        # Add bill items from order
        subtotal = Decimal('0')
        for order_item in order.items.all():
            BillItem.objects.create(
                bill=bill,
                item_name=f"{order_item.menu_item.name_en} (Table {order.table.table_number})",
                quantity=order_item.quantity,
                price=order_item.price
            )
            subtotal += order_item.total_price

        # Apply discount
        discount_amount = (subtotal * discount_percentage) / 100
        discounted_subtotal = subtotal - discount_amount

        # Calculate GST (18% for restaurant services in India)
        gst_rate = Decimal('0.18')
        gst_amount = discounted_subtotal * gst_rate

        # Calculate total
        total_amount = discounted_subtotal + gst_amount

        # Update bill with calculations
        bill.total_amount = total_amount
        bill.save()

        # Mark order as billed
        order.status = 'billed'
        order.save()

        # Free up table if no more active orders
        if order.table.orders.filter(status__in=['pending', 'in_progress']).count() == 0:
            order.table.is_occupied = False
            order.table.save()

        # Create GST breakdown for receipt
        gst_breakdown = {
            'subtotal': float(subtotal),
            'discount_percentage': float(discount_percentage),
            'discount_amount': float(discount_amount),
            'taxable_amount': float(discounted_subtotal),
            'cgst_rate': 9.0,  # Central GST
            'sgst_rate': 9.0,  # State GST
            'cgst_amount': float(gst_amount / 2),
            'sgst_amount': float(gst_amount / 2),
            'total_gst': float(gst_amount),
            'total_amount': float(total_amount)
        }

        return Response({
            'success': True,
            'bill_id': bill.id,
            'receipt_number': bill.receipt_number,
            'gst_breakdown': gst_breakdown,
            'message': 'Bill generated successfully'
        })

    except Exception as e:
        return Response({
            'error': f'Failed to generate bill: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

