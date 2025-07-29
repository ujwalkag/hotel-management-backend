from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.bills.models import Bill
from apps.bills.permissions import IsAdminOrStaff
from django.utils.timezone import now
from django.db.models import Sum
from django.db.models import Q
from datetime import timedelta, datetime

class BillHistoryView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrStaff]

    def get(self, request):
        queryset = Bill.objects.select_related("user", "room").prefetch_related("items").all()

        start = request.GET.get("start")
        end = request.GET.get("end")
        bill_type = request.GET.get("type")
        search = request.GET.get("search")

        if start:
            try:
                start_date = datetime.strptime(start, "%Y-%m-%d")
                queryset = queryset.filter(created_at__date__gte=start_date)
            except ValueError:
                pass

        if end:
            try:
                end_date = datetime.strptime(end, "%Y-%m-%d")
                queryset = queryset.filter(created_at__date__lte=end_date)
            except ValueError:
                pass

        if bill_type:
            queryset = queryset.filter(bill_type=bill_type)

        if search:
            queryset = queryset.filter(
                Q(customer_name__icontains=search) |
                Q(customer_phone__icontains=search) |
                Q(receipt_number__icontains=search)
            )

        queryset = queryset.order_by("-created_at")

        data = []
        for bill in queryset:
            data.append({
                "id": bill.id,
                "receipt_number": bill.receipt_number,
                "bill_type": bill.bill_type,
                "total_amount": float(bill.total_amount),
                "payment_method": bill.payment_method,
                "customer_name": bill.customer_name,
                "customer_phone": bill.customer_phone,
                "user_email": bill.user.email,
                "room_name": f"{bill.room.type_en} / {bill.room.type_hi}" if bill.room else None,  # Both English/Hindi
                "created_at": bill.created_at,
                "items": [
                    {
                        "name": item.item_name,
                        "quantity": item.quantity,
                        "price": float(item.price)
                    } for item in bill.items.all()
                ]
            })

        return Response(data)

class BillAnalyticsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrStaff]

    def get(self, request):
        range_days = int(request.GET.get("range", 7))
        today = now().date()
        start_date = today - timedelta(days=range_days - 1)

        bills = Bill.objects.filter(created_at__date__gte=start_date)
        daily_data = {}

        for i in range(range_days):
            date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            daily_data[date] = 0

        for bill in bills:
            bill_date = bill.created_at.date().strftime("%Y-%m-%d")
            if bill_date in daily_data:
                daily_data[bill_date] += bill.total_amount

        chart_data = [
            {"date": date, "total": daily_data[date]}
            for date in sorted(daily_data.keys())
        ]

        return Response(chart_data)

class BillSummaryView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrStaff]

    def get(self, request):
        today = now().date()
        yesterday = today - timedelta(days=1)
        start_week = today - timedelta(days=today.weekday())
        start_month = today.replace(day=1)

        total_today = Bill.objects.filter(created_at__date=today).aggregate(total=Sum("total_amount"))["total"] or 0
        total_yesterday = Bill.objects.filter(created_at__date=yesterday).aggregate(total=Sum("total_amount"))["total"] or 0
        total_week = Bill.objects.filter(created_at__date__gte=start_week).aggregate(total=Sum("total_amount"))["total"] or 0
        total_month = Bill.objects.filter(created_at__date__gte=start_month).aggregate(total=Sum("total_amount"))["total"] or 0
        total_bills = Bill.objects.count()

        return Response({
            "total_today": float(total_today),
            "total_yesterday": float(total_yesterday),
            "total_week": float(total_week),
            "total_month": float(total_month),
            "total_bills": total_bills
        })
