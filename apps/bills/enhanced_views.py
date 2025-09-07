# apps/bills/enhanced_views.py - COMPLETELY UPDATED FOR TABLE-BASED DYNAMIC BILLING
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from decimal import Decimal
from datetime import datetime, date

from .models import Bill, BillItem
from .serializers import BillSerializer
from apps.tables.models import RestaurantTable, TableOrder, OrderItem, EnhancedBillingSession
from apps.menu.models import MenuItem
from django.utils import timezone

class EnhancedBillingViewSet(viewsets.ModelViewSet):
    """
    NEW Enhanced Billing System - Shows table-specific orders dynamically
    Mobile orders for T1, T2, T3 etc. appear here automatically
    Admin can add/edit/delete items and generate bills with GST
    """
    queryset = Bill.objects.all()
    serializer_class = BillSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def active_tables_dashboard(self, request):
        """
        GET /api/bills/enhanced/active_tables_dashboard/
        Main dashboard showing all tables with active orders
        This replaces the old enhanced billing - shows T1, T2, T3 etc. with orders
        """
        # Get all tables that have active orders (from mobile ordering)
        active_tables = RestaurantTable.objects.filter(
            status='occupied',
            orders__status__in=['pending', 'in_progress', 'ready', 'completed']
        ).distinct().order_by('table_number')

        dashboard_data = []

        for table in active_tables:
            # Get all active orders for this table
            active_orders = table.orders.filter(
                status__in=['pending', 'in_progress', 'ready', 'completed'],
                is_in_enhanced_billing=True
            ).order_by('-created_at')

            # Calculate table totals
            table_subtotal = sum(order.total_amount for order in active_orders)

            # Get order details for display
            order_details = []
            for order in active_orders:
                order_items = []
                for item in order.items.all():
                    order_items.append({
                        'id': item.id,
                        'name': item.menu_item.name_en,
                        'name_hi': item.menu_item.name_hi,
                        'quantity': item.quantity,
                        'price': float(item.price),
                        'total': float(item.total_price),
                        'status': item.status,
                        'special_instructions': item.special_instructions
                    })

                order_details.append({
                    'order_id': order.id,
                    'order_number': order.order_number,
                    'status': order.status,
                    'customer_name': order.customer_name,
                    'customer_count': order.customer_count,
                    'total_amount': float(order.total_amount),
                    'created_at': order.created_at.isoformat(),
                    'items': order_items
                })

            dashboard_data.append({
                'table_id': table.id,
                'table_number': table.table_number,
                'table_capacity': table.capacity,
                'table_status': table.status,
                'session_id': table.current_session_id,
                'orders_count': active_orders.count(),
                'subtotal': float(table_subtotal),
                'can_generate_bill': active_orders.exists(),
                'last_order_time': active_orders.first().created_at.isoformat() if active_orders.exists() else None,
                'orders': order_details
            })

        return Response({
            'status': 'success',
            'active_tables': dashboard_data,
            'total_active_tables': len(dashboard_data),
            'total_pending_revenue': float(sum(table['subtotal'] for table in dashboard_data)),
            'timestamp': timezone.now().isoformat()
        })

    @action(detail=False, methods=['post'])
    def add_custom_item_to_table(self, request):
        """
        POST /api/bills/enhanced/add_custom_item_to_table/
        Admin can add custom items to any table's bill
        Body: {
            "table_id": 1,
            "item_name": "Special Item",
            "quantity": 2,
            "price": 100.00,
            "notes": "Custom addition"
        }
        """
        table_id = request.data.get('table_id')
        item_name = request.data.get('item_name')
        quantity = int(request.data.get('quantity', 1))
        price = Decimal(str(request.data.get('price', 0)))
        notes = request.data.get('notes', '')

        if not all([table_id, item_name, price]):
            return Response({
                'error': 'table_id, item_name, and price are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            table = RestaurantTable.objects.get(id=table_id)

            # Get or create an active order for this table
            active_order = table.orders.filter(
                status__in=['pending', 'in_progress', 'ready', 'completed'],
                is_in_enhanced_billing=True
            ).first()

            if not active_order:
                # Create a new order if none exists
                active_order = TableOrder.objects.create(
                    table=table,
                    customer_name="Admin Addition",
                    status='completed',
                    is_in_enhanced_billing=True,
                    enhanced_billing_notes=f"Custom item added: {item_name}"
                )
                table.occupy_table()

            # Create a custom menu item entry or find existing
            try:
                # Try to find existing menu item
                menu_item = MenuItem.objects.filter(name_en__icontains=item_name).first()
                if not menu_item:
                    # For custom items, we'll create a temporary reference
                    # In production, you might want to have a "custom items" category
                    menu_item = MenuItem.objects.create(
                        name_en=item_name,
                        name_hi=item_name,
                        price=price,
                        category=None,
                        available=True
                    )
            except Exception:
                return Response({
                    'error': 'Failed to create menu item reference'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Add the item to the order
            order_item = OrderItem.objects.create(
                table_order=active_order,
                menu_item=menu_item,
                quantity=quantity,
                price=price,
                status='served',  # Custom items are considered already prepared
                special_instructions=notes,
                kitchen_notes="Added via Enhanced Billing"
            )

            # Update order total
            active_order.calculate_total()

            return Response({
                'status': 'success',
                'message': f'Added {item_name} x {quantity} to Table {table.table_number}',
                'order_item': {
                    'id': order_item.id,
                    'name': order_item.menu_item.name_en,
                    'quantity': order_item.quantity,
                    'price': float(order_item.price),
                    'total': float(order_item.total_price)
                },
                'order_total': float(active_order.total_amount)
            })

        except RestaurantTable.DoesNotExist:
            return Response({
                'error': 'Table not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Failed to add item: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['delete'])
    def delete_item_from_table(self, request):
        """
        DELETE /api/bills/enhanced/delete_item_from_table/
        Admin can delete items from table bills
        Body: {
            "order_item_id": 123
        }
        """
        order_item_id = request.data.get('order_item_id')

        if not order_item_id:
            return Response({
                'error': 'order_item_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            order_item = OrderItem.objects.get(id=order_item_id)
            table_order = order_item.table_order
            table = table_order.table

            # Delete the item
            item_name = order_item.menu_item.name_en
            item_quantity = order_item.quantity
            order_item.delete()

            # Recalculate order total
            table_order.calculate_total()

            return Response({
                'status': 'success',
                'message': f'Deleted {item_name} x {item_quantity} from Table {table.table_number}',
                'order_total': float(table_order.total_amount)
            })

        except OrderItem.DoesNotExist:
            return Response({
                'error': 'Order item not found'
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['patch'])
    def update_item_quantity(self, request):
        """
        PATCH /api/bills/enhanced/update_item_quantity/
        Admin can update item quantities
        Body: {
            "order_item_id": 123,
            "new_quantity": 3
        }
        """
        order_item_id = request.data.get('order_item_id')
        new_quantity = request.data.get('new_quantity')

        if not all([order_item_id, new_quantity]):
            return Response({
                'error': 'order_item_id and new_quantity are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_quantity = int(new_quantity)
            if new_quantity < 0:
                return Response({
                    'error': 'Quantity must be positive'
                }, status=status.HTTP_400_BAD_REQUEST)
            elif new_quantity == 0:
                # Delete the item if quantity is 0
                return self.delete_item_from_table(request)

            order_item = OrderItem.objects.get(id=order_item_id)
            old_quantity = order_item.quantity
            order_item.quantity = new_quantity
            order_item.save()

            # Recalculate order total
            order_item.table_order.calculate_total()

            return Response({
                'status': 'success',
                'message': f'Updated {order_item.menu_item.name_en} quantity from {old_quantity} to {new_quantity}',
                'order_item': {
                    'id': order_item.id,
                    'name': order_item.menu_item.name_en,
                    'quantity': order_item.quantity,
                    'price': float(order_item.price),
                    'total': float(order_item.total_price)
                },
                'order_total': float(order_item.table_order.total_amount)
            })

        except OrderItem.DoesNotExist:
            return Response({
                'error': 'Order item not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({
                'error': 'Invalid quantity value'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def calculate_bill_with_gst(self, request):
        """
        POST /api/bills/enhanced/calculate_bill_with_gst/
        Calculate final bill with GST for a table
        Body: {
            "table_id": 1,
            "apply_gst": true,
            "gst_rate": 18,  // percentage
            "interstate": false,  // true for IGST, false for CGST+SGST
            "discount_percent": 0,
            "discount_amount": 0
        }
        """
        table_id = request.data.get('table_id')
        apply_gst = request.data.get('apply_gst', False)
        gst_rate = Decimal(str(request.data.get('gst_rate', 18)))
        interstate = request.data.get('interstate', False)
        discount_percent = Decimal(str(request.data.get('discount_percent', 0)))
        discount_amount = Decimal(str(request.data.get('discount_amount', 0)))

        if not table_id:
            return Response({
                'error': 'table_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            table = RestaurantTable.objects.get(id=table_id)

            # Get all active orders for the table
            active_orders = table.orders.filter(
                status__in=['pending', 'in_progress', 'ready', 'completed'],
                is_in_enhanced_billing=True
            )

            if not active_orders.exists():
                return Response({
                    'error': 'No active orders found for this table'
                }, status=status.HTTP_404_NOT_FOUND)

            # Calculate subtotal
            subtotal = sum(order.total_amount for order in active_orders)

            # Apply discount
            if discount_percent > 0:
                discount_amount = subtotal * (discount_percent / 100)

            discounted_subtotal = subtotal - discount_amount

            # Calculate GST
            gst_amount = Decimal('0')
            cgst_amount = Decimal('0')
            sgst_amount = Decimal('0')
            igst_amount = Decimal('0')

            if apply_gst:
                gst_decimal = gst_rate / 100
                gst_amount = discounted_subtotal * gst_decimal

                if interstate:
                    igst_amount = gst_amount
                else:
                    cgst_amount = gst_amount / 2
                    sgst_amount = gst_amount / 2

            # Calculate final total
            total_amount = discounted_subtotal + gst_amount

            # Prepare bill breakdown
            bill_breakdown = {
                'table_number': table.table_number,
                'subtotal': float(subtotal),
                'discount_percent': float(discount_percent),
                'discount_amount': float(discount_amount),
                'discounted_subtotal': float(discounted_subtotal),
                'gst_applied': apply_gst,
                'gst_rate': float(gst_rate),
                'interstate': interstate,
                'cgst_amount': float(cgst_amount),
                'sgst_amount': float(sgst_amount),
                'igst_amount': float(igst_amount),
                'total_gst_amount': float(gst_amount),
                'total_amount': float(total_amount),
                'orders_count': active_orders.count(),
                'calculation_time': timezone.now().isoformat()
            }

            return Response({
                'status': 'success',
                'bill_breakdown': bill_breakdown
            })

        except RestaurantTable.DoesNotExist:
            return Response({
                'error': 'Table not found'
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def generate_final_bill(self, request):
        """
        POST /api/bills/enhanced/generate_final_bill/
        Generate final bill and mark table as available
        Body: {
            "table_id": 1,
            "customer_name": "John Doe",
            "customer_phone": "9876543210",
            "payment_method": "cash",
            "apply_gst": true,
            "gst_rate": 18,
            "interstate": false,
            "discount_amount": 0
        }
        """
        table_id = request.data.get('table_id')
        customer_name = request.data.get('customer_name', 'Guest')
        customer_phone = request.data.get('customer_phone', '')
        payment_method = request.data.get('payment_method', 'cash')
        apply_gst = request.data.get('apply_gst', False)
        gst_rate = Decimal(str(request.data.get('gst_rate', 18)))
        interstate = request.data.get('interstate', False)
        discount_amount = Decimal(str(request.data.get('discount_amount', 0)))

        if not table_id:
            return Response({
                'error': 'table_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                table = RestaurantTable.objects.get(id=table_id)

                # Get all active orders for the table
                active_orders = table.orders.filter(
                    status__in=['pending', 'in_progress', 'ready', 'completed'],
                    is_in_enhanced_billing=True
                )

                if not active_orders.exists():
                    return Response({
                        'error': 'No active orders found for this table'
                    }, status=status.HTTP_404_NOT_FOUND)

                # Calculate totals
                subtotal = sum(order.total_amount for order in active_orders)
                discounted_subtotal = subtotal - discount_amount

                # Calculate GST
                gst_amount = Decimal('0')
                if apply_gst:
                    gst_amount = discounted_subtotal * (gst_rate / 100)

                total_amount = discounted_subtotal + gst_amount

                # Create the final bill
                bill = Bill.objects.create(
                    user=request.user,
                    bill_type='restaurant',
                    customer_name=customer_name,
                    customer_phone=customer_phone,
                    total_amount=total_amount,
                    payment_method=payment_method
                )

                # Create bill items from all order items
                for order in active_orders:
                    for order_item in order.items.all():
                        BillItem.objects.create(
                            bill=bill,
                            item_name=order_item.menu_item.name_en,
                            quantity=order_item.quantity,
                            price=order_item.price
                        )

                # Mark all orders as billed
                for order in active_orders:
                    order.mark_billed()

                # Release the table (status: occupied -> available)
                table.release_table()

                return Response({
                    'status': 'success',
                    'message': f'Bill generated successfully for Table {table.table_number}',
                    'bill': {
                        'bill_id': bill.id,
                        'receipt_number': bill.receipt_number,
                        'customer_name': bill.customer_name,
                        'customer_phone': bill.customer_phone,
                        'subtotal': float(subtotal),
                        'discount_amount': float(discount_amount),
                        'gst_amount': float(gst_amount),
                        'total_amount': float(total_amount),
                        'payment_method': payment_method,
                        'created_at': bill.created_at.isoformat()
                    },
                    'table': {
                        'table_number': table.table_number,
                        'status': table.status,  # Should be 'available' now
                        'session_cleared': True
                    }
                })

        except RestaurantTable.DoesNotExist:
            return Response({
                'error': 'Table not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Failed to generate bill: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def table_order_history(self, request):
        """
        GET /api/bills/enhanced/table_order_history/?table_id=1
        Get order history for a specific table
        """
        table_id = request.query_params.get('table_id')

        if not table_id:
            return Response({
                'error': 'table_id parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            table = RestaurantTable.objects.get(id=table_id)

            # Get recent orders (last 30 days)
            from datetime import timedelta
            thirty_days_ago = timezone.now() - timedelta(days=30)

            orders = table.orders.filter(
                created_at__gte=thirty_days_ago
            ).order_by('-created_at')

            order_history = []
            for order in orders:
                order_items = []
                for item in order.items.all():
                    order_items.append({
                        'name': item.menu_item.name_en,
                        'quantity': item.quantity,
                        'price': float(item.price),
                        'total': float(item.total_price),
                        'status': item.status
                    })

                order_history.append({
                    'order_id': order.id,
                    'order_number': order.order_number,
                    'status': order.status,
                    'customer_name': order.customer_name,
                    'total_amount': float(order.total_amount),
                    'created_at': order.created_at.isoformat(),
                    'completed_at': order.completed_at.isoformat() if order.completed_at else None,
                    'items': order_items
                })

            return Response({
                'status': 'success',
                'table_number': table.table_number,
                'order_history': order_history,
                'total_orders': len(order_history)
            })

        except RestaurantTable.DoesNotExist:
            return Response({
                'error': 'Table not found'
            }, status=status.HTTP_404_NOT_FOUND)

