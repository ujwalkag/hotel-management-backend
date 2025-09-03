# apps/bills/views.py - COMPLETE UPDATED VERSION
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
from apps.menu.models import MenuItem
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
    return bool(re.fullmatch(r"[6-9]\d{9}", phone or ""))

def customer_bill_message(bill_type, customer_name, total, receipt_number, days=None):
    if bill_type == "restaurant":
        return f"Hi {customer_name}, your restaurant bill is ₹{total}. Receipt: {receipt_number}\nThank you for dining with us!"
    else:
        # Room bill
        return f"Hi {customer_name}, your room bill is ₹{total}" + (f" for {days} day(s)." if days else "") + f" Receipt: {receipt_number}\nThank you for staying with us!"

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
        user = request.user
        items = request.data.get("items", [])
        customer_name = request.data.get("customer_name", "").strip()
        customer_phone = request.data.get("customer_phone", "").strip()
        notify_customer_flag = request.data.get("notify_customer", False)
        payment_method = request.data.get("payment_method", "cash")
        apply_gst = request.data.get("apply_gst", False)

        if isinstance(apply_gst, str):
            apply_gst = apply_gst.lower() == 'true'

        if not items or not customer_name or not customer_phone:
            return Response({"error": "Customer name, phone, and items required"}, status=400)

        total = Decimal(0)
        for item in items:
            try:
                menu_item = MenuItem.objects.get(id=item["item_id"])
                total += Decimal(menu_item.price) * item["quantity"]
            except MenuItem.DoesNotExist:
                continue

        gst_amount = Decimal(0)
        gst_rate = Decimal("0.00")

        if apply_gst:
            gst_rate = Decimal("0.05")
            gst_amount = (total * gst_rate).quantize(Decimal("0.01"))
            total += gst_amount

        bill = Bill.objects.create(
            user=user,
            bill_type='restaurant',
            customer_name=customer_name,
            customer_phone=customer_phone,
            total_amount=total,
            payment_method=payment_method
        )

        for item in items:
            try:
                menu_item = MenuItem.objects.get(id=item["item_id"])
                BillItem.objects.create(
                    bill=bill,
                    item_name=menu_item.name_en,
                    quantity=item["quantity"],
                    price=menu_item.price
                )
            except MenuItem.DoesNotExist:
                continue

        folder = os.path.join(settings.MEDIA_ROOT, "bills", datetime.now().strftime("%Y-%m"))
        os.makedirs(folder, exist_ok=True)
        filename = f"{bill.receipt_number}.pdf"
        pdf_path = os.path.join(folder, filename)

        render_to_pdf("bills/bill_pdf.html", {
            "bill": bill,
            "items": bill.items.all(),
            "gst": gst_amount,
            "gst_rate": gst_rate * 100,
        }, pdf_path)

        notify_admin_via_whatsapp(
            f"🍽️ New Restaurant Bill\nCustomer: {customer_name}\nPhone: {customer_phone}\nTotal: ₹{total}\nReceipt: {bill.receipt_number}"
        )

        if notify_customer_flag:
            notify_customer(
                customer_name=customer_name,
                customer_phone=customer_phone,
                total=total,
                receipt_number=bill.receipt_number,
                bill_type="restaurant",
                pdf_path=pdf_path
            )

        return Response({
            "message": "Restaurant bill created",
            "bill_id": bill.id,
            "receipt_number": bill.receipt_number,
            "payment_method": bill.payment_method,
            "gst_applied": apply_gst,
            "gst_amount": float(gst_amount),
            "gst_rate": float(gst_rate * 100)
        }, status=201)


class CreateRoomBillView(APIView):
    permission_classes = [IsAdminOrStaff]

    def post(self, request):
        user = request.user
        customer_name = request.data.get("customer_name", "").strip()
        customer_phone = request.data.get("customer_phone", "").strip()
        room_id = request.data.get("room")
        days = int(request.data.get("days", 1))
        notify_customer_flag = request.data.get("notify_customer", False)
        payment_method = request.data.get("payment_method", "cash")
        apply_gst = request.data.get("apply_gst", False)

        if isinstance(apply_gst, str):
            apply_gst = apply_gst.lower() == "true"

        if not customer_name or not customer_phone or not room_id:
            return Response({"error": "Customer name, phone and room required"}, status=400)

        try:
            room = Room.objects.get(id=room_id)
        except Room.DoesNotExist:
            return Response({"error": "Room not found"}, status=404)

        base_total = Decimal(room.price_per_day) * days
        gst_amount = Decimal(0)
        gst_rate = Decimal(0)

        if apply_gst:
            if base_total < 1000:
                gst_rate = Decimal("0.00")
            elif 1000 <= base_total < 7500:
                gst_rate = Decimal("0.05")
            else:
                gst_rate = Decimal("0.12")
            gst_amount = (base_total * gst_rate).quantize(Decimal("0.01"))

        total = base_total + gst_amount

        bill = Bill.objects.create(
            user=user,
            bill_type='room',
            customer_name=customer_name,
            customer_phone=customer_phone,
            room=room,
            total_amount=total,
            payment_method=payment_method
        )

        BillItem.objects.create(
            bill=bill,
            item_name=f"{room.type_en} / {room.type_hi}",
            quantity=days,
            price=room.price_per_day
        )

        folder = os.path.join(settings.MEDIA_ROOT, "bills", datetime.now().strftime("%Y-%m"))
        os.makedirs(folder, exist_ok=True)
        filename = f"{bill.receipt_number}.pdf"
        pdf_path = os.path.join(folder, filename)
        render_to_pdf("bills/bill_pdf.html", {"bill": bill, "items": bill.items.all(), "gst": gst_amount}, pdf_path)

        notify_admin_via_whatsapp(
            f"🛏️ New Room Bill\nCustomer: {customer_name}\nPhone: {customer_phone}\nRoom: {room.type_en} / {room.type_hi}\nDays: {days}\nTotal: ₹{total}\nReceipt: {bill.receipt_number}"
        )

        if notify_customer_flag:
            notify_customer(
                customer_name=customer_name,
                customer_phone=customer_phone,
                total=total,
                receipt_number=bill.receipt_number,
                bill_type="room",
                pdf_path=pdf_path,
                days=days
            )

        return Response({
            "message": "Room bill created",
            "bill_id": bill.id,
            "receipt_number": bill.receipt_number,
            "payment_method": bill.payment_method,
            "gst_applied": apply_gst,
            "gst_amount": float(gst_amount),
            "gst_rate": float(gst_rate)
        }, status=201)


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
            "room_name": f"{bill.room.type_en} / {bill.room.type_hi}" if bill.room else None,
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


# ============================================
# ENHANCED BILLING API FUNCTIONS
# ============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_orders_ready_for_billing(request):
    """Get all orders that are ready for billing"""
    try:
        from apps.tables.models import TableOrder

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
                        'name': item.menu_item.name_en,
                        'name_hi': getattr(item.menu_item, 'name_hi', ''),
                        'quantity': item.quantity,
                        'price': float(item.price),
                        'total': float(item.total_price),
                        'menu_item': {
                            'id': item.menu_item.id,
                            'name_en': item.menu_item.name_en,
                            'name_hi': getattr(item.menu_item, 'name_hi', ''),
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
    """Generate bill from completed order with GST calculation"""
    data = request.data
    order_id = data.get('order_id')
    payment_method = data.get('payment_method', 'cash')
    discount_percentage = Decimal(str(data.get('discount_percentage', '0')))

    if not order_id:
        return Response({'error': 'order_id is required'}, 
                       status=status.HTTP_400_BAD_REQUEST)

    try:
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
                item_name=f"{order_item.menu_item.name_en} (Table {order.table.table_number})",
                quantity=order_item.quantity,
                price=order_item.price
            )
            subtotal += Decimal(str(order_item.quantity)) * Decimal(str(order_item.price))

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
        if order.table.active_orders_count == 0:
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

