# apps/admin_dashboard/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.utils.timezone import now
from datetime import timedelta
from django.db import models
from rest_framework.permissions import IsAuthenticated

from apps.bookings.models import Order, MenuItem
from apps.admin_dashboard.models import SalesSummary, BestSellingItem
from .serializers import (
    SalesSummarySerializer,
    BestSellingItemSerializer,
    OrderStatsSerializer,
    RevenueStatsSerializer
)

class AdminPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and getattr(request.user, 'role', '') == 'admin'

class DashboardHomeView(APIView):
    permission_classes = [IsAuthenticated, AdminPermission]

    def get(self, request):
        return Response({"message": "Welcome to the Admin Dashboard"}, status=status.HTTP_200_OK)

class OrderStatsView(APIView):
    permission_classes = [IsAuthenticated, AdminPermission]

    def get(self, request):
        total_orders = Order.objects.count()
        completed = Order.objects.filter(status='completed').count()
        pending = Order.objects.filter(status='pending').count()
        failed = Order.objects.filter(status='failed').count()

        data = {
            "total_orders": total_orders,
            "completed_orders": completed,
            "pending_orders": pending,
            "failed_orders": failed,
        }
        return Response(data, status=status.HTTP_200_OK)

class RevenueStatsView(APIView):
    permission_classes = [IsAuthenticated, AdminPermission]

    def get(self, request):
        today = now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        daily_sales = Order.objects.filter(
            status='completed', created_at__date=today).aggregate(total=models.Sum('total_price'))['total'] or 0

        weekly_sales = Order.objects.filter(
            status='completed', created_at__date__gte=week_ago).aggregate(total=models.Sum('total_price'))['total'] or 0

        monthly_sales = Order.objects.filter(
            status='completed', created_at__date__gte=month_ago).aggregate(total=models.Sum('total_price'))['total'] or 0

        return Response({
            "daily_sales": daily_sales,
            "weekly_sales": weekly_sales,
            "monthly_sales": monthly_sales,
        }, status=status.HTTP_200_OK)

class BestSellingItemsView(APIView):
    permission_classes = [IsAuthenticated, AdminPermission]

    def get(self, request):
        top_items = BestSellingItem.objects.select_related('item').order_by('-sales_count')[:10]
        serializer = BestSellingItemSerializer(top_items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class SalesSummaryView(APIView):
    permission_classes = [IsAuthenticated, AdminPermission]

    def get(self, request):
        summaries = SalesSummary.objects.all().order_by('-date')[:10]
        serializer = SalesSummarySerializer(summaries, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

