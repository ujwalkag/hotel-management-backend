
# BILLING ENHANCEMENTS

# apps/bills/enhanced_views.py - Enhanced Billing with One-Click Generation
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from apps.tables.models import TableOrder
from .models import Bill, BillItem
from decimal import Decimal
import json

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_bill_from_order(request):
    """One-click bill generation from table order with GST calculation"""
    data = request.data
    order_id = data.get('order_id')
    payment_method = data.get('payment_method', 'cash')
    discount_percentage = Decimal(data.get('discount_percentage', '0'))

    if not order_id:
        return Response({'error': 'Order ID required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        order = get_object_or_404(TableOrder, pk=order_id)

        # Check if order is ready for billing
        if order.status not in ['completed', 'ready']:
            return Response({
                'error': 'Order must be completed before billing'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create bill
        bill = Bill.objects.create(
            user=request.user,
            bill_type='restaurant',
            customer_name=order.customer_name or 'Table Guest',
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

        # Mark order as billed
        order.status = 'billed'
        order.save()

        # Free up table
        if order.table.active_orders_count == 0:
            order.table.is_occupied = False
            order.table.save()

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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def orders_ready_for_billing(request):
    """Get all orders that are ready for billing"""
    orders = TableOrder.objects.filter(
        status__in=['completed', 'ready']
    ).select_related('table', 'waiter').prefetch_related('items__menu_item')

    order_data = []
    for order in orders:
        order_data.append({
            'id': order.id,
            'order_number': order.order_number,
            'table_number': order.table.table_number,
            'customer_name': order.customer_name,
            'waiter_name': order.waiter.email if order.waiter else 'Unknown',
            'total_amount': float(order.total_amount),
            'items_count': order.items.count(),
            'created_at': order.created_at.isoformat(),
            'items': [
                {
                    'name': item.menu_item.name_en,
                    'quantity': item.quantity,
                    'price': float(item.price),
                    'total': float(item.total_price)
                }
                for item in order.items.all()
            ]
        })

    return Response(order_data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def split_bill(request):
    """Split bill between multiple customers"""
    data = request.data
    order_id = data.get('order_id')
    split_data = data.get('splits', [])  # Array of {customer_name, items_ids[]}

    if not split_data or len(split_data) < 2:
        return Response({
            'error': 'At least 2 customers required for split billing'
        }, status=status.HTTP_400_BAD_REQUEST)

    order = get_object_or_404(TableOrder, pk=order_id)
    bills_created = []

    for split in split_data:
        customer_name = split.get('customer_name', 'Guest')
        item_ids = split.get('item_ids', [])

        if not item_ids:
            continue

        # Create separate bill for this customer
        bill = Bill.objects.create(
            user=request.user,
            bill_type='restaurant',
            customer_name=customer_name,
            customer_phone=order.customer_phone or 'N/A',
            payment_method=data.get('payment_method', 'cash')
        )

        subtotal = Decimal('0')
        for item_id in item_ids:
            order_item = order.items.get(id=item_id)
            BillItem.objects.create(
                bill=bill,
                item_name=f"{order_item.menu_item.name_en} (Table {order.table.table_number})",
                quantity=order_item.quantity,
                price=order_item.price
            )
            subtotal += order_item.total_price

        # Calculate GST
        gst_amount = subtotal * Decimal('0.18')
        total_amount = subtotal + gst_amount

        bill.total_amount = total_amount
        bill.save()

        bills_created.append({
            'customer_name': customer_name,
            'bill_id': bill.id,
            'receipt_number': bill.receipt_number,
            'amount': float(total_amount)
        })

    # Mark order as billed
    order.status = 'billed'
    order.save()

    return Response({
        'success': True,
        'bills': bills_created,
        'message': f'{len(bills_created)} bills created successfully'
    })
