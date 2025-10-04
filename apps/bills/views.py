# apps/bills/views.py - COMPLETE UPDATED VERSION WITH ALL name_en FIXES
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from django.utils.timezone import now
from datetime import datetime
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from decimal import Decimal
import os
import re

from .models import Bill, BillItem
# FIXED: Use restaurant app MenuItem model
from apps.restaurant.models import MenuItem
from apps.rooms.models import Room
from .permissions import IsAdminOrStaff
from .notifications import notify_admin_via_whatsapp
from .utils import render_to_pdf
from apps.notifications.twilio import notify_customer_via_sms
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from io import BytesIO

def is_valid_indian_phone(phone):
    # Only allow 10 digits, starts with 6-9
    return bool(re.fullmatch(r"[6-9]\\d{9}", phone or ""))

def customer_bill_message(bill_type, customer_name, total, receipt_number, days=None):
    if bill_type == "restaurant":
        return f"Hi {customer_name}, your restaurant bill is ₹{total}. Receipt: {receipt_number}\\nThank you for dining with us!"
    else:
        # Room bill
        return f"Hi {customer_name}, your room bill is ₹{total}" + (f" for {days} day(s)." if days else "") + f" Receipt: {receipt_number}\\nThank you for staying with us!"

def notify_customer(customer_name, customer_phone, total, receipt_number, bill_type, pdf_path=None, days=None):
    # Prefer WhatsApp, fallback to SMS, only if phone is valid
    if not is_valid_indian_phone(customer_phone):
        return
    msg = customer_bill_message(bill_type, customer_name, total, receipt_number, days)
    try:
        notify_customer_via_sms(customer_phone, msg)
    except Exception as e:
        print(f"Customer notification error: {e}")

class DailyBillReportView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrStaff]

    def get(self, request):
        date_str = request.GET.get("date", now().strftime("%Y-%m-%d"))
        try:
            selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

        bills = Bill.objects.filter(created_at__date=selected_date).select_related("user", "room").prefetch_related("items").order_by("created_at")
        html_content = render_to_string("bills/daily_report.html", {"bills": bills, "report_date": selected_date})

        pdf_output = BytesIO()
        pisa_status = pisa.CreatePDF(html_content, dest=pdf_output)
        if pisa_status.err:
            return Response({"error": "Error generating PDF"}, status=500)

        folder = os.path.join(settings.MEDIA_ROOT, "daily_reports")
        os.makedirs(folder, exist_ok=True)
        file_path = os.path.join(folder, f"{date_str}.pdf")

        with open(file_path, "wb") as f:
            f.write(pdf_output.getvalue())

        return Response({"message": f"Daily report generated", "pdf_path": file_path}, status=200)

class CreateRestaurantBillView(APIView):
    permission_classes = [IsAdminOrStaff]

    def post(self, request):
        try:
            user = request.user
            items = request.data.get("items", [])
            customer_name = request.data.get("customer_name", "").strip() or "Guest"
            customer_phone = request.data.get("customer_phone", "").strip()
            customer_email = request.data.get("customer_email", "").strip()

            # Enhanced billing settings
            payment_method = request.data.get("payment_method", "cash")
            apply_gst = request.data.get("apply_gst", False)  # ✅ DEFAULT TO FALSE
            
            # Also handle string values from frontend
            if isinstance(apply_gst, str):
                apply_gst = apply_gst.lower() in ['true', '1', 'yes']

            gst_rate = request.data.get("gst_rate", 0)
            interstate = request.data.get("interstate", False)
            discount_percent = request.data.get("discount_percent", 0)
            discount_amount = request.data.get("discount_amount", 0)
            table_number = request.data.get("table_number", "")
            special_instructions = request.data.get("special_instructions", "")

            if not items:
                return Response({
                    "error": "At least one item is required"
                }, status=status.HTTP_400_BAD_REQUEST)

            subtotal = Decimal(0)
            bill_items = []

            # Process each item (handle both regular and custom items)
            for item in items:
                try:
                    item_id = item.get("item_id")
                    item_name = item.get("item_name")
                    quantity = int(item.get("quantity", 1))
                    price = Decimal(str(item.get("price", 0)))
                    discount = Decimal(str(item.get("discount", 0)))
                    notes = item.get("notes", "")

                    if quantity <= 0:
                        continue

                    # Handle regular menu items
                    if item_id:
                        try:
                            # ✅ FIXED: Use MenuItem from restaurant app
                            menu_item = MenuItem.objects.get(id=item_id)
                            # ✅ FIXED: Use correct field name 'name' instead of 'name_en'
                            item_name = getattr(menu_item, 'name', None) or str(menu_item.id)
                            if price <= 0:
                                price = menu_item.price
                        except MenuItem.DoesNotExist:
                            return Response({
                                "error": f"Menu item with ID {item_id} not found or not available"
                            }, status=status.HTTP_400_BAD_REQUEST)

                    # Handle custom items
                    elif item_name:
                        if price <= 0:
                            return Response({
                                "error": f"Price is required for custom item: {item_name}"
                            }, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        return Response({
                            "error": "Either item_id or item_name is required"
                        }, status=status.HTTP_400_BAD_REQUEST)

                    # Calculate item total
                    item_total = (price * quantity) - discount
                    if item_total < 0:
                        item_total = Decimal(0)

                    subtotal += item_total

                    # Store for bill creation
                    bill_items.append({
                        'item_name': item_name,
                        'quantity': quantity,
                        'unit_price': price,
                        'discount': discount,
                        'total_price': item_total,
                        'notes': notes
                    })

                except (ValueError, TypeError, KeyError) as e:
                    return Response({
                        "error": f"Invalid item data: {str(e)}"
                    }, status=status.HTTP_400_BAD_REQUEST)

            # Calculate discounts
            bill_discount_amount = Decimal(0)
            if discount_percent > 0:
                bill_discount_amount = (subtotal * Decimal(str(discount_percent))) / 100
            if discount_amount > 0:
                bill_discount_amount = max(bill_discount_amount, Decimal(str(discount_amount)))

            # Calculate taxable amount
            taxable_amount = subtotal - bill_discount_amount
            if taxable_amount < 0:
                taxable_amount = Decimal(0)

            # Calculate GST
            gst_amount = Decimal(0)
            cgst_amount = Decimal(0)
            sgst_amount = Decimal(0)
            igst_amount = Decimal(0)

            if apply_gst and gst_rate > 0:
                gst_rate_decimal = Decimal(str(gst_rate)) / 100
                gst_amount = taxable_amount * gst_rate_decimal
                
                if interstate:
                    igst_amount = gst_amount
                else:
                    cgst_amount = gst_amount / 2
                    sgst_amount = gst_amount / 2

            # Calculate final total
            final_total = taxable_amount + gst_amount

            # Create bill record
            bill = Bill.objects.create(
                user=user,
                bill_type='restaurant',
                customer_name=customer_name,
                customer_phone=customer_phone,
                total_amount=final_total,
                payment_method=payment_method
            )

            # Create bill items
            for bill_item in bill_items:
                BillItem.objects.create(
                    bill=bill,
                    item_name=bill_item['item_name'],
                    quantity=bill_item['quantity'],
                    price=bill_item['unit_price']
                )

            # Generate PDF
            try:
                folder = os.path.join(settings.MEDIA_ROOT, "bills", datetime.now().strftime("%Y-%m"))
                os.makedirs(folder, exist_ok=True)
                filename = f"{bill.receipt_number}.pdf"
                pdf_path = os.path.join(folder, filename)

                render_to_pdf("bills/bill_pdf.html", {
                    "bill": bill,
                    "items": bill.items.all(),
                    "gst": gst_amount,
                    "gst_rate": gst_rate,
                    "cgst_amount": cgst_amount,
                    "sgst_amount": sgst_amount,
                    "igst_amount": igst_amount,
                    "subtotal": subtotal,
                    "discount_amount": bill_discount_amount,
                    "taxable_amount": taxable_amount
                }, pdf_path)

            except Exception as pdf_error:
                # Don't fail the entire operation if PDF generation fails
                print(f"PDF generation error: {pdf_error}")

            # Notify admin
            try:
                notify_admin_via_whatsapp(
                    f"🍽️ New Restaurant Bill\\n"
                    f"Customer: {customer_name}\\n"
                    f"Phone: {customer_phone}\\n"
                    f"Total: ₹{final_total}\\n"
                    f"Receipt: {bill.receipt_number}"
                )
            except Exception:
                pass  # Don't fail if notification fails

            return Response({
                "message": "Restaurant bill created successfully",
                "bill_id": bill.id,
                "receipt_number": bill.receipt_number,
                "total_amount": float(final_total),
                "customer_name": customer_name,
                "customer_phone": customer_phone,
                "payment_method": payment_method,
                "gst_breakdown": {
                    "subtotal": float(subtotal),
                    "discount_amount": float(bill_discount_amount),
                    "taxable_amount": float(taxable_amount),
                    "gst_applied": apply_gst,
                    "gst_rate": gst_rate,
                    "gst_amount": float(gst_amount),
                    "cgst_amount": float(cgst_amount),
                    "sgst_amount": float(sgst_amount),
                    "igst_amount": float(igst_amount),
                    "interstate": interstate
                }
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            # Log the full error for debugging
            import traceback
            print(f"Restaurant billing error: {e}")
            print(f"Full traceback: {traceback.format_exc()}")
            
            return Response({
                "error": f"Failed to create bill: {str(e)}",
                "details": "Please check server logs for more information"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CreateRoomBillView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrStaff]

    def post(self, request):
        user = request.user
        data = request.data

        # Required fields
        customer_name = data.get("customer_name", "").strip()
        customer_phone = data.get("customer_phone", "").strip()
        items = data.get("items", [])  # Expecting list of {room, quantity}
        payment_method = data.get("payment_method", "cash")
        apply_gst = data.get("apply_gst", False)
        notify_flag = data.get("notify_customer", False)

        # Validate
        if not customer_name or not customer_phone or not items or not isinstance(items, list):
            return Response(
                {"error": "Customer name, phone and items required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Calculate base total
        base_total = Decimal(0)
        for it in items:
            try:
                room = Room.objects.get(id=it.get("room"))
                qty = int(it.get("quantity", 1))
                base_total += room.price_per_day * qty
            except (Room.DoesNotExist, ValueError, TypeError):
                return Response({"error": "Invalid room or quantity"}, status=400)

        # GST calculation
        gst_rate = Decimal(0)
        if apply_gst:
            if base_total < 1000:
                gst_rate = Decimal("0.00")
            elif base_total < 7500:
                gst_rate = Decimal("0.05")
            else:
                gst_rate = Decimal("0.12")

        gst_amount = (base_total * gst_rate).quantize(Decimal("0.01"))
        total_amount = base_total + gst_amount

        # Create bill
        bill = Bill.objects.create(
            user=user,
            bill_type="room",
            customer_name=customer_name,
            customer_phone=customer_phone,
            total_amount=total_amount,
            payment_method=payment_method
        )

        # Create BillItems
        for it in items:
            room = Room.objects.get(id=it.get("room"))
            qty = int(it.get("quantity", 1))
            BillItem.objects.create(
                bill=bill,
                item_name=f"{getattr(room, 'type_en', room.type)} / {getattr(room, 'type_hi', room.type)}",
                quantity=qty,
                price=room.price_per_day
            )

        # Render PDF
        folder = os.path.join(settings.MEDIA_ROOT, "bills", datetime.now().strftime("%Y-%m"))
        os.makedirs(folder, exist_ok=True)
        filename = f"{bill.receipt_number}.pdf"
        pdf_path = os.path.join(folder, filename)

        render_to_pdf("bills/bill_pdf.html", {
            "bill": bill,
            "items": bill.items.all(),
            "gst": gst_amount,
            "gst_rate_percent": float(gst_rate * 100),
        }, pdf_path)

        # Notify admin
        notify_admin_via_whatsapp(
            f"🛏️ New Room Bill\\nCustomer: {customer_name}\\nPhone: {customer_phone}\\nTotal: ₹{total_amount}\\nReceipt: {bill.receipt_number}"
        )

        # Notify customer if requested
        if notify_flag:
            notify_customer_via_sms(
                customer_phone,
                f"Hi {customer_name}, your room bill is ₹{total_amount}. Receipt: {bill.receipt_number}"
            )

        # Response
        return Response({
            "message": "Room bill created",
            "bill_id": bill.id,
            "receipt_number": bill.receipt_number,
            "gst_applied": bool(apply_gst),
            "gst_rate": float(gst_rate * 100),
            "gst_amount": float(gst_amount),
            "total_amount": float(total_amount),
        }, status=status.HTTP_201_CREATED)

class BillPDFView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrStaff]

    def get(self, request, pk):
        bill = get_object_or_404(Bill, pk=pk)
        pdf_path = os.path.join(settings.MEDIA_ROOT, "bills", bill.created_at.strftime("%Y-%m"), f"{bill.receipt_number}.pdf")

        if not os.path.exists(pdf_path):
            return Response({"error": "PDF not found"}, status=404)

        with open(pdf_path, "rb") as f:
            response = HttpResponse(f.read(), content_type="application/pdf")
            response["Content-Disposition"] = f"inline; filename={bill.receipt_number}.pdf"
            return response

class BillDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrStaff]

    def get(self, request, pk):
        bill = get_object_or_404(Bill.objects.select_related("user", "room").prefetch_related("items"), pk=pk)

        data = {
            "id": bill.id,
            "receipt_number": bill.receipt_number,
            "bill_type": bill.bill_type,
            "total_amount": float(bill.total_amount),
            "payment_method": bill.payment_method,
            "customer_name": bill.customer_name,
            "customer_phone": bill.customer_phone,
            "user_email": bill.user.email,
            "room_name": f"{getattr(bill.room, 'type_en', bill.room.type)} / {getattr(bill.room, 'type_hi', bill.room.type)}" if bill.room else None,
            "created_at": bill.created_at.isoformat(),
            "items": [
                {
                    "name": item.item_name,
                    "quantity": item.quantity,
                    "price": float(item.price),
                    "total": float(item.price * item.quantity)
                } for item in bill.items.all()
            ]
        }
        return Response(data)

# ================================================
# ENHANCED BILLING API FUNCTIONS - ALL name_en FIXED
# ================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_orders_ready_for_billing(request):
    """Get all orders that are ready for billing - FIXED name_en issues"""
    try:
        # Check if we have restaurant app orders or separate tables app orders
        try:
            from apps.restaurant.models import Order
            # Get completed orders that haven't been billed yet
            orders = Order.objects.filter(
                status__in=['served', 'ready']
            ).select_related('table', 'menu_item', 'created_by')
            
            order_data = []
            for order in orders:
                order_data.append({
                    'id': order.id,
                    'order_number': getattr(order, 'order_number', f"ORD-{order.id}"),
                    'table_id': order.table.id,
                    'table_number': order.table.table_number,
                    'customer_name': 'Guest',
                    'customer_phone': '',
                    'waiter_name': order.created_by.email if order.created_by else 'Unknown',
                    'total_amount': float(order.total_price or 0),
                    'items_count': 1,
                    'created_at': order.created_at.isoformat(),
                    'status': order.status,
                    'items': [{
                        'id': order.id,
                        'name': getattr(order.menu_item, 'name', 'Unknown Item'),  # ✅ FIXED
                        'name_hi': getattr(order.menu_item, 'name', ''),  # ✅ FIXED
                        'quantity': order.quantity,
                        'price': float(order.unit_price),
                        'total': float(order.total_price),
                        'menu_item': {
                            'id': order.menu_item.id,
                            'name_en': getattr(order.menu_item, 'name', 'Unknown'),  # ✅ FIXED
                            'name_hi': getattr(order.menu_item, 'name', ''),  # ✅ FIXED
                            'price': float(order.menu_item.price)
                        }
                    }]
                })
            return Response(order_data)
        except ImportError:
            # Fallback to tables app if it exists
            from apps.tables.models import TableOrder
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
                    'customer_name': order.customer_name or 'Guest',
                    'customer_phone': order.customer_phone or '',
                    'waiter_name': order.waiter.email if order.waiter else 'Unknown',
                    'total_amount': float(order.total_amount or 0),
                    'items_count': order.items.count(),
                    'created_at': order.created_at.isoformat(),
                    'status': order.status,
                    'items': [
                        {
                            'id': item.id,
                            'name': getattr(item.menu_item, 'name', 'Unknown Item'),  # ✅ FIXED
                            'name_hi': getattr(item.menu_item, 'name', ''),  # ✅ FIXED
                            'quantity': item.quantity,
                            'price': float(item.price),
                            'total': float(item.total_price),
                            'menu_item': {
                                'id': item.menu_item.id,
                                'name_en': getattr(item.menu_item, 'name', 'Unknown'),  # ✅ FIXED
                                'name_hi': getattr(item.menu_item, 'name', ''),  # ✅ FIXED
                                'price': float(item.menu_item.price)
                            }
                        }
                        for item in order.items.all()
                    ]
                })
            return Response(order_data)

    except Exception as e:
        return Response({'error': f'Failed to fetch orders: {str(e)}'},
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_bill_from_order(request):
    """Generate bill from completed order with GST calculation - FIXED name_en issues"""
    data = request.data
    order_id = data.get('order_id')
    payment_method = data.get('payment_method', 'cash')
    discount_percentage = Decimal(str(data.get('discount_percentage', '0')))

    if not order_id:
        return Response({'error': 'order_id is required'},
                       status=status.HTTP_400_BAD_REQUEST)

    try:
        # Try restaurant app first
        try:
            from apps.restaurant.models import Order
            order = get_object_or_404(Order, id=order_id)
            
            # Check if order is ready for billing
            if order.status not in ['served', 'ready']:
                return Response({
                    'error': f'Order must be completed before billing. Current status: {order.status}'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Create bill using existing structure
            bill = Bill.objects.create(
                user=request.user,
                bill_type='restaurant',
                customer_name='Guest',
                customer_phone='N/A',
                payment_method=payment_method
            )

            # Add bill item from order
            BillItem.objects.create(
                bill=bill,
                item_name=f"{getattr(order.menu_item, 'name', 'Unknown Item')} (Table {order.table.table_number})",  # ✅ FIXED
                quantity=order.quantity,
                price=order.unit_price
            )
            subtotal = Decimal(str(order.quantity)) * Decimal(str(order.unit_price))

        except ImportError:
            # Fallback to tables app
            from apps.tables.models import TableOrder
            order = get_object_or_404(TableOrder, id=order_id)
            
            # Check if order is ready for billing
            if order.status not in ['completed', 'ready']:
                return Response({
                    'error': f'Order must be completed before billing. Current status: {order.status}'
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
                    item_name=f"{getattr(order_item.menu_item, 'name', 'Unknown Item')} (Table {order.table.table_number})",  # ✅ FIXED
                    quantity=order_item.quantity,
                    price=order_item.price
                )
                subtotal += Decimal(str(order_item.quantity)) * Decimal(str(order_item.price))

            # Mark order as billed
            order.status = 'billed'
            order.save()

            # Free up table if no more active orders
            if hasattr(order.table, 'active_orders_count') and order.table.active_orders_count == 0:
                order.table.is_occupied = False
                order.table.save()

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
