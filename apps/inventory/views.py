# apps/inventory/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth
from datetime import datetime, date
from decimal import Decimal

from .models import InventoryCategory, InventoryEntry
from .serializers import (
    InventoryCategorySerializer, 
    InventoryEntrySerializer,
    InventoryReportSerializer
)
from .permissions import IsAdminOnly

class InventoryCategoryViewSet(viewsets.ModelViewSet):
    queryset = InventoryCategory.objects.all()
    serializer_class = InventoryCategorySerializer
    permission_classes = [IsAuthenticated, IsAdminOnly]

    def get_queryset(self):
        queryset = InventoryCategory.objects.all()
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        active_only = self.request.query_params.get('active_only', None)
        if active_only == 'true':
            queryset = queryset.filter(is_active=True)
            
        return queryset.order_by('name')

class InventoryEntryViewSet(viewsets.ModelViewSet):
    queryset = InventoryEntry.objects.all()
    serializer_class = InventoryEntrySerializer
    permission_classes = [IsAuthenticated, IsAdminOnly]

    def get_queryset(self):
        queryset = InventoryEntry.objects.select_related('category', 'created_by').all()
        
        # Filter by category
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category_id=category)
        
        # Filter by month/year
        month = self.request.query_params.get('month', None)
        year = self.request.query_params.get('year', None)
        if month and year:
            queryset = queryset.filter(
                purchase_date__month=month,
                purchase_date__year=year
            )
        
        # Filter by date range
        date_from = self.request.query_params.get('date_from', None)
        date_to = self.request.query_params.get('date_to', None)
        if date_from:
            queryset = queryset.filter(purchase_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(purchase_date__lte=date_to)
        
        # Search
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(item_name__icontains=search) |
                Q(supplier_name__icontains=search)
            )
        
        return queryset.order_by('-purchase_date', '-created_at')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def monthly_report(self, request):
        """Generate monthly inventory report"""
        try:
            month = request.query_params.get('month', datetime.now().month)
            year = request.query_params.get('year', datetime.now().year)
            
            entries = InventoryEntry.objects.filter(
                purchase_date__month=month,
                purchase_date__year=year
            )
            
            total_spent = entries.aggregate(
                total=Sum('total_cost')
            )['total'] or Decimal('0.00')
            
            total_entries = entries.count()
            
            # Category-wise data
            categories_data = entries.values('category__name').annotate(
                spent=Sum('total_cost'),
                count=Count('id')
            ).order_by('-spent')
            
            # Top suppliers
            top_suppliers = entries.values('supplier_name').annotate(
                spent=Sum('total_cost'),
                count=Count('id')
            ).order_by('-spent')[:10]
            
            report_data = {
                'month': month,
                'year': year,
                'total_spent': total_spent,
                'total_entries': total_entries,
                'categories_data': list(categories_data),
                'top_suppliers': list(top_suppliers)
            }
            
            return Response(report_data)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Quick stats for dashboard"""
        try:
            # Current month stats
            current_month = datetime.now().month
            current_year = datetime.now().year
            
            current_month_spent = InventoryEntry.objects.filter(
                purchase_date__month=current_month,
                purchase_date__year=current_year
            ).aggregate(total=Sum('total_cost'))['total'] or Decimal('0.00')
            
            total_categories = InventoryCategory.objects.filter(is_active=True).count()
            
            # Recent entries (last 10)
            recent_entries = InventoryEntry.objects.select_related('category').order_by('-created_at')[:10]
            recent_serializer = InventoryEntrySerializer(recent_entries, many=True)
            
            return Response({
                'current_month_spent': current_month_spent,
                'total_categories': total_categories,
                'recent_entries': recent_serializer.data
            })
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

