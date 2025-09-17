# apps/restaurant/views_admin.py
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Table, Order, OrderSession
from .serializers import TableSerializer, TableWithOrdersSerializer
from decimal import Decimal
from django.utils import timezone

class AdminTableViewSet(viewsets.ModelViewSet):
    """
    Admin-only viewset that exposes:
    - full CRUD
    - current-bill
    - generate-bill-and-free-table
    """
    queryset = Table.objects.all()
    serializer_class = TableSerializer
    permission_classes = [permissions.IsAdminUser]

    @action(detail=True, methods=["get"])
    def with_orders(self, request, pk=None):
        table = self.get_object()
        ser = TableWithOrdersSerializer(table)
        return Response(ser.data)

    @action(detail=True, methods=["post"])
    def generate_bill(self, request, pk=None):
        """
        • Collect all active orders
        • Create Bill + BillItems
        • Close session
        • Mark table free
        """
        from apps.bills.models import Bill, BillItem

        table = self.get_object()
        session = table.order_sessions.filter(is_active=True).first()
        orders = table.orders.filter(status__in=["pending", "confirmed",
                                                 "preparing", "ready"])

        if not orders.exists():
            return Response({"error": "No orders to bill"},
                            status=status.HTTP_400_BAD_REQUEST)

        bill = Bill.objects.create(
            user=request.user,
            bill_type="restaurant",
            customer_name=request.data.get("customer_name", "Guest"),
            customer_phone=request.data.get("customer_phone", "N/A"),
            payment_method=request.data.get("payment_method", "cash")
        )

        for o in orders:
            BillItem.objects.create(
                bill=bill,
                item_name=o.menu_item.name,
                quantity=o.quantity,
                price=o.total_price
            )
            o.status = "served"
            o.save(update_fields=["status"])

        bill.total_amount = orders.aggregate(
            total=Sum("total_price"))["total"] or Decimal("0.00")
        bill.save(update_fields=["total_amount"])

        # close session and free table
        if session:
            session.complete_session()
        else:
            table.mark_free()

        return Response({
            "bill_id": bill.id,
            "receipt": bill.receipt_number,
            "amount": float(bill.total_amount)
        }, status=status.HTTP_201_CREATED)

