from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Bill
from django.utils.timezone import now, timedelta
from django.db.models import Sum, Count

class BillSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({"error": "Unauthorized"}, status=403)

        today = now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        total_today = Bill.objects.filter(created_at__date=today).aggregate(total=Sum('total_amount'))['total'] or 0
        total_week = Bill.objects.filter(created_at__date__gte=week_start).aggregate(total=Sum('total_amount'))['total'] or 0
        total_month = Bill.objects.filter(created_at__date__gte=month_start).aggregate(total=Sum('total_amount'))['total'] or 0

        total_bills = Bill.objects.count()

        return Response({
            "total_today": total_today,
            "total_week": total_week,
            "total_month": total_month,
            "total_bills": total_bills
        })

class DailySalesView(APIView):
    """
    API to get daily total sales for the past 7 days (including today).
    """

    def get(self, request):
        today = timezone.now().date()
        week_ago = today - timedelta(days=6)  # 7 days range

        daily_sales = []
        for day in range(7):
            date = week_ago + timedelta(days=day)
            total_sales = Bill.objects.filter(created_at__date=date).aggregate(total=Sum('amount'))['total'] or 0

            daily_sales.append({
                "date": date.strftime('%Y-%m-%d'),
                "total_sales": total_sales
            })

        return Response(daily_sales, status=200)
