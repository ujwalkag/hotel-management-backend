# apps/bills/enhanced_views.py - COMPLETE SOLUTION WITH CUSTOMER HANDLING
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from decimal import Decimal
from datetime import datetime
import os
from django.conf import settings
from django.utils import timezone

# Import correct models from your restaurant app
from .models import Bill, BillItem
from .serializers import BillSerializer
from apps.restaurant.models import Table, Order, MenuItem, MenuCategory, OrderSession
from apps.menu.models import MenuItem as MenuItemOld  # Your old menu model
from .utils import render_to_pdf
from django.template.loader import render_to_string

class EnhancedBillingViewSet(viewsets.ModelViewSet):
    """
    Complete Enhanced Billing System with customer handling and table freeing
    """
    queryset = Bill.objects.all()
    serializer_class = BillSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def active_tables_dashboard(self, request):
        """
        GET /api/bills/enhanced/active_tables_dashboard/
        Show all occupied tables with orders ready for billing
        """
        try:
            # Get all occupied tables with active orders
            occupied_tables = Table.objects.filter(
                status='occupied',
                is_active=True
            ).distinct().order_by('table_number')

            dashboard_data = []

            for table in occupied_tables:
                # Get all active orders for this table
                active_orders = Order.objects.filter(
                    table=table,
                    status__in=['confirmed', 'preparing', 'ready', 'served']
                ).select_related('menu_item', 'menu_item__category', 'created_by').order_by('-created_at')

                if not active_orders.exists():
                    continue

                # Calculate table totals
                table_subtotal = sum(order.total_price for order in active_orders)

                # Prepare order details for display
                order_details = []
                customer_name = 'Guest'
                customer_phone = ''

                # Try to get customer info from order session
                session = table.order_sessions.filter(is_active=True).first()
                if session:
                    customer_name = getattr(session, 'customer_name', 'Guest')
                    customer_phone = getattr(session, 'customer_phone', '')

                for order in active_orders:
                    order_details.append({
                        'order_id': order.id,
                        'order_number': order.order_number,
                        'status': order.status,
                        'customer_name': customer_name,
                        'menu_item_name': order.menu_item.name,
                        'menu_category': order.menu_item.category.name if order.menu_item.category else 'No Category',
                        'quantity': order.quantity,
                        'unit_price': float(order.unit_price),
                        'total_price': float(order.total_price),
                        'special_instructions': order.special_instructions or '',
                        'created_at': order.created_at.isoformat(),
                        # Format for frontend compatibility
                        'items': [{
                            'id': order.id,
                            'name': order.menu_item.name,
                            'quantity': order.quantity,
                            'price': float(order.unit_price),
                            'total': float(order.total_price),
                            'status': order.status,
                            'special_instructions': order.special_instructions or ''
                        }]
                    })

                dashboard_data.append({
                    'table_id': table.id,
                    'table_number': table.table_number,
                    'table_capacity': table.capacity,
                    'table_status': table.status,
                    'table_location': table.location or '',
                    'orders_count': active_orders.count(),
                    'subtotal': float(table_subtotal),
                    'can_generate_bill': True,
                    'last_order_time': active_orders.first().created_at.isoformat(),
                    'customer_name': customer_name,
                    'customer_phone': customer_phone,
                    'orders': order_details
                })

            return Response({
                'status': 'success',
                'active_tables': dashboard_data,
                'total_active_tables': len(dashboard_data),
                'total_pending_revenue': float(sum(table['subtotal'] for table in dashboard_data)),
                'timestamp': timezone.now().isoformat()
            })

        except Exception as e:
            return Response({
                'error': f'Failed to fetch active tables: {str(e)}',
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def update_customer_details(self, request):
        """
        POST /api/bills/enhanced/update_customer_details/
        Update customer details for a table session
        Body: {
            "table_id": 1,
            "customer_name": "John Doe", 
            "customer_phone": "9876543210"
        }
        """
        table_id = request.data.get('table_id')
        customer_name = request.data.get('customer_name', 'Guest')
        customer_phone = request.data.get('customer_phone', '')

        if not table_id:
            return Response({
                'error': 'table_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                table = get_object_or_404(Table, id=table_id, is_active=True)

                # Get or create active order session
                session = table.order_sessions.filter(is_active=True).first()
                if not session:
                    session = OrderSession.objects.create(
                        table=table,
                        created_by=request.user,
                        is_active=True
                    )

                # Update customer details in session
                session.customer_name = customer_name
                session.customer_phone = customer_phone
                session.save()

                return Response({
                    'status': 'success',
                    'message': f'Customer details updated for Table {table.table_number}',
                    'customer_name': customer_name,
                    'customer_phone': customer_phone
                })

        except Exception as e:
            return Response({
                'error': f'Failed to update customer details: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def add_custom_item_to_table(self, request):
        """
        POST /api/bills/enhanced/add_custom_item_to_table/
        Add custom items to table bill during billing process
        """
        table_id = request.data.get('table_id')
        item_name = request.data.get('item_name', '').strip()
        quantity = int(request.data.get('quantity', 1))
        price = Decimal(str(request.data.get('price', 0)))
        notes = request.data.get('notes', '').strip()

        if not all([table_id, item_name]) or price <= 0:
            return Response({
                'error': 'table_id, item_name, and valid price are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                table = get_object_or_404(Table, id=table_id, is_active=True)

                # Get or create a "Custom Items" category
                custom_category, created = MenuCategory.objects.get_or_create(
                    name='Custom Items',
                    defaults={
                        'description': 'Custom items added during billing',
                        'display_order': 999,
                        'is_active': True
                    }
                )

                # Create or get menu item for this custom item
                menu_item, item_created = MenuItem.objects.get_or_create(
                    name=item_name,
                    category=custom_category,
                    defaults={
                        'description': f'Custom item: {item_name}',
                        'price': price,
                        'preparation_time': 5,
                        'is_active': True,
                        'availability': 'available',
                        'is_veg': True
                    }
                )

                # Update price if different
                if menu_item.price != price:
                    menu_item.price = price
                    menu_item.save()

                # Create new order for the custom item
                order = Order.objects.create(
                    table=table,
                    menu_item=menu_item,
                    quantity=quantity,
                    unit_price=price,
                    special_instructions=notes,
                    created_by=request.user,
                    status='served',  # Custom items are immediately ready
                    priority='normal'
                )

                return Response({
                    'status': 'success',
                    'message': f'Added {item_name} x {quantity} to Table {table.table_number}',
                    'order': {
                        'id': order.id,
                        'order_number': order.order_number,
                        'name': order.menu_item.name,
                        'quantity': order.quantity,
                        'price': float(order.unit_price),
                        'total': float(order.total_price),
                        'status': order.status,
                        'special_instructions': order.special_instructions
                    }
                })

        except Exception as e:
            return Response({
                'error': f'Failed to add item: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['delete'])
    def delete_item_from_table(self, request):
        """
        DELETE /api/bills/enhanced/delete_item_from_table/
        Remove items from table bill
        """
        order_item_id = request.data.get('order_item_id')

        if not order_item_id:
            return Response({
                'error': 'order_item_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                order = get_object_or_404(Order, id=order_item_id)
                table = order.table
                item_info = {
                    'name': order.menu_item.name,
                    'quantity': order.quantity,
                    'total_price': float(order.total_price)
                }

                # Delete the order
                order.delete()

                return Response({
                    'status': 'success',
                    'message': f'Deleted {item_info["name"]} x {item_info["quantity"]} from Table {table.table_number}',
                    'deleted_item': item_info
                })

        except Exception as e:
            return Response({
                'error': f'Failed to delete item: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['patch'])
    def update_item_quantity(self, request):
        """
        PATCH /api/bills/enhanced/update_item_quantity/
        Update quantity of items in table bill
        """
        order_item_id = request.data.get('order_item_id')
        new_quantity = request.data.get('new_quantity')

        if not all([order_item_id, new_quantity]):
            return Response({
                'error': 'order_item_id and new_quantity are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_quantity = int(new_quantity)
            if new_quantity <= 0:
                # If quantity is 0 or negative, delete the item
                return self.delete_item_from_table(request)

            with transaction.atomic():
                order = get_object_or_404(Order, id=order_item_id)
                old_quantity = order.quantity
                old_total = float(order.total_price)

                order.quantity = new_quantity
                order.save()  # This will recalculate total_price

                return Response({
                    'status': 'success',
                    'message': f'Updated {order.menu_item.name} quantity from {old_quantity} to {new_quantity}',
                    'order': {
                        'id': order.id,
                        'name': order.menu_item.name,
                        'quantity': order.quantity,
                        'unit_price': float(order.unit_price),
                        'total_price': float(order.total_price),
                        'old_total': old_total
                    }
                })

        except ValueError:
            return Response({
                'error': 'Invalid quantity value'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': f'Failed to update quantity: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def calculate_bill_with_gst(self, request):
        """
        POST /api/bills/enhanced/calculate_bill_with_gst/
        Calculate bill with GST breakdown for table
        """
        table_id = request.data.get('table_id')
        apply_gst = request.data.get('apply_gst', True)
        gst_rate = Decimal(str(request.data.get('gst_rate', 18)))
        interstate = request.data.get('interstate', False)
        discount_percent = Decimal(str(request.data.get('discount_percent', 0)))
        discount_amount = Decimal(str(request.data.get('discount_amount', 0)))

        if not table_id:
            return Response({
                'error': 'table_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            table = get_object_or_404(Table, id=table_id, is_active=True)

            # Get all orders for this table that can be billed
            billable_orders = Order.objects.filter(
                table=table,
                status__in=['confirmed', 'preparing', 'ready', 'served']
            ).select_related('menu_item')

            if not billable_orders.exists():
                return Response({
                    'error': 'No billable orders found for this table'
                }, status=status.HTTP_404_NOT_FOUND)

            # Calculate subtotal
            subtotal = sum(order.total_price for order in billable_orders)

            # Apply discount
            calculated_discount = Decimal('0')
            if discount_percent > 0:
                calculated_discount = (subtotal * discount_percent) / 100
            if discount_amount > 0:
                calculated_discount = max(calculated_discount, discount_amount)

            taxable_amount = subtotal - calculated_discount

            # Calculate GST
            gst_amount = Decimal('0')
            cgst_amount = Decimal('0')
            sgst_amount = Decimal('0')
            igst_amount = Decimal('0')

            if apply_gst and gst_rate > 0:
                gst_decimal = gst_rate / 100
                gst_amount = (taxable_amount * gst_decimal).quantize(Decimal('0.01'))

                if interstate:
                    igst_amount = gst_amount
                else:
                    cgst_amount = (gst_amount / 2).quantize(Decimal('0.01'))
                    sgst_amount = (gst_amount / 2).quantize(Decimal('0.01'))

            # Calculate final total
            total_amount = taxable_amount + gst_amount

            # Prepare detailed bill breakdown (D-mart style)
            bill_breakdown = {
                'table_number': table.table_number,
                'table_location': table.location or '',
                'order_count': billable_orders.count(),
                'item_count': sum(order.quantity for order in billable_orders),

                # Financial breakdown
                'subtotal': float(subtotal),
                'discount_percent': float(discount_percent),
                'discount_amount': float(calculated_discount),
                'taxable_amount': float(taxable_amount),

                # GST details
                'gst_applied': apply_gst,
                'gst_rate': float(gst_rate),
                'interstate': interstate,
                'cgst_rate': float(gst_rate / 2) if not interstate else 0,
                'sgst_rate': float(gst_rate / 2) if not interstate else 0,
                'igst_rate': float(gst_rate) if interstate else 0,
                'cgst_amount': float(cgst_amount),
                'sgst_amount': float(sgst_amount),
                'igst_amount': float(igst_amount),
                'total_gst_amount': float(gst_amount),

                # Final totals
                'total_amount': float(total_amount),
                'total_savings': float(calculated_discount),

                # Metadata
                'calculation_time': timezone.now().isoformat(),
                'calculated_by': request.user.email,

                # Item details for receipt
                'items': [{
                    'name': order.menu_item.name,
                    'quantity': order.quantity,
                    'unit_price': float(order.unit_price),
                    'total_price': float(order.total_price),
                    'category': order.menu_item.category.name if order.menu_item.category else 'Others'
                } for order in billable_orders]
            }

            return Response({
                'status': 'success',
                'bill_breakdown': bill_breakdown,
                'ready_for_billing': True
            })

        except Exception as e:
            return Response({
                'error': f'Failed to calculate bill: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def generate_final_bill(self, request):
        """
        POST /api/bills/enhanced/generate_final_bill/
        Generate final D-mart style bill and FREE THE TABLE
        Handle missing customer details by making them optional
        """
        table_id = request.data.get('table_id')
        customer_name = request.data.get('customer_name', 'Guest').strip() or 'Guest'
        customer_phone = request.data.get('customer_phone', '').strip() or 'N/A'
        payment_method = request.data.get('payment_method', 'cash')
        apply_gst = request.data.get('apply_gst', True)
        gst_rate = Decimal(str(request.data.get('gst_rate', 18)))
        interstate = request.data.get('interstate', False)
        discount_percent = Decimal(str(request.data.get('discount_percent', 0)))
        discount_amount = Decimal(str(request.data.get('discount_amount', 0)))

        if not table_id:
            return Response({
                'error': 'table_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                table = get_object_or_404(Table, id=table_id, is_active=True)

                # Get all billable orders
                billable_orders = Order.objects.filter(
                    table=table,
                    status__in=['confirmed', 'preparing', 'ready', 'served']
                ).select_related('menu_item', 'menu_item__category')

                if not billable_orders.exists():
                    return Response({
                        'error': 'No billable orders found for this table'
                    }, status=status.HTTP_404_NOT_FOUND)

                # Calculate all amounts
                subtotal = sum(order.total_price for order in billable_orders)

                # Apply discount
                calculated_discount = Decimal('0')
                if discount_percent > 0:
                    calculated_discount = (subtotal * discount_percent) / 100
                if discount_amount > 0:
                    calculated_discount = max(calculated_discount, discount_amount)

                taxable_amount = subtotal - calculated_discount

                # Calculate GST
                gst_amount = Decimal('0')
                cgst_amount = Decimal('0')
                sgst_amount = Decimal('0')

                if apply_gst and gst_rate > 0:
                    gst_decimal = gst_rate / 100
                    gst_amount = (taxable_amount * gst_decimal).quantize(Decimal('0.01'))

                    if not interstate:
                        cgst_amount = (gst_amount / 2).quantize(Decimal('0.01'))
                        sgst_amount = (gst_amount / 2).quantize(Decimal('0.01'))

                total_amount = taxable_amount + gst_amount

                # Create the bill record
                bill = Bill.objects.create(
                    user=request.user,
                    bill_type='restaurant',
                    customer_name=customer_name,
                    customer_phone=customer_phone,
                    total_amount=total_amount,
                    payment_method=payment_method
                )

                # Create bill items
                for order in billable_orders:
                    BillItem.objects.create(
                        bill=bill,
                        item_name=f"{order.menu_item.name} (Table {table.table_number})",
                        quantity=order.quantity,
                        price=order.unit_price
                    )

                # Generate D-mart style PDF receipt
                pdf_path = self.generate_dmart_receipt(
                    bill, table, billable_orders, subtotal, calculated_discount, 
                    gst_amount, cgst_amount, sgst_amount, interstate, gst_rate
                )

                # Update order statuses to served
                billable_orders.update(status='served', served_at=timezone.now())

                # Complete any active session
                session = table.order_sessions.filter(is_active=True).first()
                if session:
                    session.complete_session()

                # FREE THE TABLE - This is the key requirement!
                table.mark_free()

                # Try to broadcast table status update via WebSocket
                try:
                    from apps.restaurant.utils import broadcast_table_update
                    broadcast_table_update(table, 'occupied')
                except ImportError:
                    pass  # WebSocket not available

                return Response({
                    'status': 'success',
                    'message': f'✅ D-mart Style Bill Generated & Table Freed!',
                    'bill': {
                        'bill_id': bill.id,
                        'receipt_number': bill.receipt_number,
                        'customer_name': bill.customer_name,
                        'customer_phone': bill.customer_phone,
                        'table_number': table.table_number,
                        'subtotal': float(subtotal),
                        'discount_amount': float(calculated_discount),
                        'taxable_amount': float(taxable_amount),
                        'gst_amount': float(gst_amount),
                        'cgst_amount': float(cgst_amount),
                        'sgst_amount': float(sgst_amount),
                        'total_amount': float(total_amount),
                        'payment_method': payment_method,
                        'gst_applied': apply_gst,
                        'interstate': interstate,
                        'gst_rate': float(gst_rate),
                        'items_count': sum(order.quantity for order in billable_orders),
                        'orders_count': billable_orders.count(),
                        'created_at': bill.created_at.isoformat(),
                        'pdf_path': pdf_path
                    },
                    'table': {
                        'table_id': table.id,
                        'table_number': table.table_number,
                        'status': table.status,  # Should be 'free' now
                        'previous_status': 'occupied',
                        'freed_at': timezone.now().isoformat(),
                        'session_cleared': True
                    },
                    'orders_processed': billable_orders.count(),
                    'table_freed': True,
                    'timestamp': timezone.now().isoformat()
                })

        except Exception as e:
            return Response({
                'error': f'Failed to generate bill: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def generate_dmart_receipt(self, bill, table, orders, subtotal, discount, 
                              gst_amount, cgst_amount, sgst_amount, interstate, gst_rate):
        """Generate D-mart style professional receipt PDF"""
        try:
            # Create bills directory structure
            folder = os.path.join(settings.MEDIA_ROOT, "bills", datetime.now().strftime("%Y-%m"))
            os.makedirs(folder, exist_ok=True)
            filename = f"{bill.receipt_number}.pdf"
            pdf_path = os.path.join(folder, filename)

            # Prepare comprehensive context for D-mart style template
            context = {
                'bill': bill,
                'table': table,
                'items': bill.items.all(),
                'orders': orders,

                # Financial details
                'subtotal': float(subtotal),
                'discount_amount': float(discount),
                'taxable_amount': float(subtotal - discount),
                'gst_amount': float(gst_amount),
                'cgst_amount': float(cgst_amount),
                'sgst_amount': float(sgst_amount),
                'interstate': interstate,
                'gst_rate': float(gst_rate),

                # Additional details for professional receipt
                'total_items': sum(order.quantity for order in orders),
                'total_orders': orders.count(),
                'current_date': timezone.now(),
                'bill_time': bill.created_at,

                # Company details (can be configured in settings)
                'company_name': getattr(settings, 'COMPANY_NAME', 'Hotel Restaurant'),
                'company_address': getattr(settings, 'COMPANY_ADDRESS', 'Hotel Address, City, State'),
                'company_phone': getattr(settings, 'COMPANY_PHONE', '+91-XXXXXXXXXX'),
                'gstin': getattr(settings, 'COMPANY_GSTIN', 'GSTIN_NUMBER'),
                'fssai': getattr(settings, 'COMPANY_FSSAI', 'FSSAI_NUMBER'),

                # Receipt styling
                'show_qr_code': True,
                'show_tax_summary': gst_amount > 0,
                'show_savings': discount > 0
            }

            # Render PDF using D-mart style template
            render_to_pdf("bills/dmart_style_bill.html", context, pdf_path)

            return pdf_path

        except Exception as e:
            print(f"Error generating D-mart receipt: {e}")
            return None

