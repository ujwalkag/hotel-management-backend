# apps/inventory/views.py - ENHANCED VERSION WITH CUSTOM FILTERS AND SPENDING ANALYTICS
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Q, Avg
from django.db.models.functions import TruncMonth, TruncDate
from datetime import datetime, date, timedelta
from decimal import Decimal
import json

from .models import InventoryCategory, InventoryEntry, SpendingBudget
from .serializers import (
    InventoryCategorySerializer, 
    InventoryEntrySerializer,
    InventoryReportSerializer,
    SpendingBudgetSerializer,
    EnhancedInventoryEntrySerializer
)

class InventoryCategoryViewSet(viewsets.ModelViewSet):
    queryset = InventoryCategory.objects.all()
    serializer_class = InventoryCategorySerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """Allow admin users full access to inventory management"""
        if (self.request.user.is_authenticated and 
            hasattr(self.request.user, 'role') and 
            self.request.user.role == 'admin'):
            return []
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = InventoryCategory.objects.all()
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(name__icontains=search)

        active_only = self.request.query_params.get('active_only', None)
        if active_only == 'true':
            queryset = queryset.filter(is_active=True)

        return queryset.order_by('name')

    @action(detail=True, methods=['get'])
    def spending_analysis(self, request, pk=None):
        """Get spending analysis for a specific category"""
        category = self.get_object()

        # Get query parameters for date filtering
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        # Calculate spending metrics
        total_spent = category.get_spent_by_period(start_date, end_date)

        # Monthly breakdown for the category
        entries = category.entries.all()
        if start_date:
            entries = entries.filter(purchase_date__gte=start_date)
        if end_date:
            entries = entries.filter(purchase_date__lte=end_date)

        monthly_breakdown = entries.extra({
            'month': "EXTRACT(month FROM purchase_date)",
            'year': "EXTRACT(year FROM purchase_date)"
        }).values('year', 'month').annotate(
            total_spent=Sum('total_cost'),
            entry_count=Count('id')
        ).order_by('year', 'month')

        # Top items in this category
        top_items = entries.values('item_name').annotate(
            total_spent=Sum('total_cost'),
            total_quantity=Sum('quantity'),
            entry_count=Count('id')
        ).order_by('-total_spent')[:10]

        return Response({
            'category': InventoryCategorySerializer(category).data,
            'total_spent': float(total_spent),
            'monthly_breakdown': list(monthly_breakdown),
            'top_items': list(top_items),
            'period': {
                'start_date': start_date,
                'end_date': end_date
            }
        })

class InventoryEntryViewSet(viewsets.ModelViewSet):
    queryset = InventoryEntry.objects.all()
    serializer_class = EnhancedInventoryEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """Allow admin users full access to inventory management"""
        if (self.request.user.is_authenticated and 
            hasattr(self.request.user, 'role') and 
            self.request.user.role == 'admin'):
            return []
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = InventoryEntry.objects.select_related('category', 'created_by').all()

        # Enhanced filtering options
        filters = self.extract_filters()

        # Apply all filters
        if filters.get('category'):
            queryset = queryset.filter(category_id=filters['category'])

        if filters.get('start_date'):
            queryset = queryset.filter(purchase_date__gte=filters['start_date'])

        if filters.get('end_date'):
            queryset = queryset.filter(purchase_date__lte=filters['end_date'])

        if filters.get('supplier'):
            queryset = queryset.filter(supplier_name__icontains=filters['supplier'])

        if filters.get('priority'):
            queryset = queryset.filter(priority=filters['priority'])

        if filters.get('min_cost'):
            queryset = queryset.filter(total_cost__gte=filters['min_cost'])

        if filters.get('max_cost'):
            queryset = queryset.filter(total_cost__lte=filters['max_cost'])

        if filters.get('unit_type'):
            queryset = queryset.filter(unit_type__icontains=filters['unit_type'])

        if filters.get('is_recurring') is not None:
            queryset = queryset.filter(is_recurring=filters['is_recurring'])

        if filters.get('tags'):
            queryset = queryset.filter(tags__icontains=filters['tags'])

        if filters.get('search'):
            search = filters['search']
            queryset = queryset.filter(
                Q(item_name__icontains=search) |
                Q(supplier_name__icontains=search) |
                Q(notes__icontains=search) |
                Q(tags__icontains=search)
            )

        # Sorting options
        sort_by = self.request.query_params.get('sort_by', '-created_at')
        valid_sorts = [
            'purchase_date', '-purchase_date',
            'total_cost', '-total_cost',
            'item_name', '-item_name',
            'created_at', '-created_at'
        ]

        if sort_by in valid_sorts:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('-purchase_date', '-created_at')

        return queryset

    def extract_filters(self):
        """Extract and validate filter parameters"""
        filters = {}

        # Date filters
        if self.request.query_params.get('start_date'):
            try:
                filters['start_date'] = datetime.strptime(
                    self.request.query_params.get('start_date'), '%Y-%m-%d'
                ).date()
            except ValueError:
                pass

        if self.request.query_params.get('end_date'):
            try:
                filters['end_date'] = datetime.strptime(
                    self.request.query_params.get('end_date'), '%Y-%m-%d'
                ).date()
            except ValueError:
                pass

        # Legacy month/year filters for backward compatibility
        month = self.request.query_params.get('month')
        year = self.request.query_params.get('year')
        if month and year:
            try:
                filters['start_date'] = date(int(year), int(month), 1)
                if int(month) == 12:
                    filters['end_date'] = date(int(year) + 1, 1, 1) - timedelta(days=1)
                else:
                    filters['end_date'] = date(int(year), int(month) + 1, 1) - timedelta(days=1)
            except ValueError:
                pass

        # Other filters
        if self.request.query_params.get('category'):
            filters['category'] = self.request.query_params.get('category')

        if self.request.query_params.get('supplier'):
            filters['supplier'] = self.request.query_params.get('supplier')

        if self.request.query_params.get('priority'):
            filters['priority'] = self.request.query_params.get('priority')

        if self.request.query_params.get('unit_type'):
            filters['unit_type'] = self.request.query_params.get('unit_type')

        if self.request.query_params.get('tags'):
            filters['tags'] = self.request.query_params.get('tags')

        # Cost range filters
        try:
            if self.request.query_params.get('min_cost'):
                filters['min_cost'] = Decimal(self.request.query_params.get('min_cost'))
        except (ValueError, TypeError):
            pass

        try:
            if self.request.query_params.get('max_cost'):
                filters['max_cost'] = Decimal(self.request.query_params.get('max_cost'))
        except (ValueError, TypeError):
            pass

        # Boolean filters
        is_recurring = self.request.query_params.get('is_recurring')
        if is_recurring is not None:
            filters['is_recurring'] = is_recurring.lower() == 'true'

        if self.request.query_params.get('search'):
            filters['search'] = self.request.query_params.get('search')

        return filters

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def spending_analytics(self, request):
        """Get comprehensive spending analytics with custom filters"""
        try:
            filters = self.extract_filters()
            analytics = InventoryEntry.get_spending_analytics(filters)

            return Response(analytics)

        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Failed to generate spending analytics'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def monthly_report(self, request):
        """Enhanced monthly inventory report"""
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

            # Category-wise data with more details
            categories_data = entries.values('category__name').annotate(
                spent=Sum('total_cost'),
                count=Count('id'),
                avg_cost=Avg('total_cost')
            ).order_by('-spent')

            # Top suppliers with more metrics
            top_suppliers = entries.values('supplier_name').annotate(
                spent=Sum('total_cost'),
                count=Count('id'),
                avg_cost=Avg('total_cost')
            ).order_by('-spent')[:10]

            # Priority-wise breakdown
            priority_breakdown = entries.values('priority').annotate(
                spent=Sum('total_cost'),
                count=Count('id')
            ).order_by('-spent')

            # Daily spending trend for the month
            daily_spending = entries.extra({
                'day': 'EXTRACT(day FROM purchase_date)'
            }).values('day').annotate(
                daily_spent=Sum('total_cost'),
                daily_count=Count('id')
            ).order_by('day')

            report_data = {
                'month': month,
                'year': year,
                'total_spent': float(total_spent),
                'total_entries': total_entries,
                'avg_cost_per_entry': float(total_spent / total_entries) if total_entries > 0 else 0,
                'categories_data': list(categories_data),
                'top_suppliers': list(top_suppliers),
                'priority_breakdown': list(priority_breakdown),
                'daily_spending': list(daily_spending)
            }

            return Response(report_data)

        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Enhanced dashboard stats with custom filtering"""
        try:
            # Current month stats
            current_month = datetime.now().month
            current_year = datetime.now().year

            current_month_spent = InventoryEntry.objects.filter(
                purchase_date__month=current_month,
                purchase_date__year=current_year
            ).aggregate(total=Sum('total_cost'))['total'] or Decimal('0.00')

            # Total categories
            total_categories = InventoryCategory.objects.filter(is_active=True).count()

            # Total suppliers
            total_suppliers = InventoryEntry.objects.values('supplier_name').distinct().count()

            # Recent entries with enhanced details
            recent_entries = InventoryEntry.objects.select_related('category').order_by('-created_at')[:10]
            recent_serializer = EnhancedInventoryEntrySerializer(recent_entries, many=True)

            # Quick stats for last 30 days
            thirty_days_ago = datetime.now() - timedelta(days=30)
            last_30_days_spent = InventoryEntry.objects.filter(
                purchase_date__gte=thirty_days_ago
            ).aggregate(total=Sum('total_cost'))['total'] or Decimal('0.00')

            # Top category this month
            top_category_this_month = InventoryEntry.objects.filter(
                purchase_date__month=current_month,
                purchase_date__year=current_year
            ).values('category__name').annotate(
                spent=Sum('total_cost')
            ).order_by('-spent').first()

            response_data = {
                'current_month_spent': float(current_month_spent),
                'total_categories': total_categories,
                'total_suppliers': total_suppliers,
                'last_30_days_spent': float(last_30_days_spent),
                'top_category_this_month': top_category_this_month,
                'recent_entries': recent_serializer.data
            }

            return Response(response_data)

        except Exception as e:
            return Response({
                'error': 'Failed to load inventory dashboard stats',
                'detail': str(e),
                'current_month_spent': 0,
                'total_categories': 0,
                'recent_entries': []
            }, status=200)

    @action(detail=False, methods=['get'])
    def filter_options(self, request):
        """Get available filter options for the frontend"""
        try:
            # Get all unique suppliers
            suppliers = list(InventoryEntry.objects.values_list('supplier_name', flat=True).distinct())

            # Get all categories
            categories = InventoryCategorySerializer(
                InventoryCategory.objects.filter(is_active=True), 
                many=True
            ).data

            # Get priority choices
            priorities = [
                {'value': 'low', 'label': 'Low'},
                {'value': 'medium', 'label': 'Medium'},
                {'value': 'high', 'label': 'High'},
                {'value': 'urgent', 'label': 'Urgent'}
            ]

            # Get unique unit types
            unit_types = list(InventoryEntry.objects.values_list('unit_type', flat=True).distinct())

            # Get cost ranges for quick filters
            cost_stats = InventoryEntry.objects.aggregate(
                min_cost=models.Min('total_cost'),
                max_cost=models.Max('total_cost'),
                avg_cost=models.Avg('total_cost')
            )

            # Get unique tags
            all_tags = []
            for tags_str in InventoryEntry.objects.exclude(tags='').values_list('tags', flat=True):
                if tags_str:
                    all_tags.extend([tag.strip() for tag in tags_str.split(',')])
            unique_tags = list(set(all_tags))

            return Response({
                'suppliers': suppliers,
                'categories': categories,
                'priorities': priorities,
                'unit_types': unit_types,
                'cost_stats': {
                    'min_cost': float(cost_stats['min_cost'] or 0),
                    'max_cost': float(cost_stats['max_cost'] or 0),
                    'avg_cost': float(cost_stats['avg_cost'] or 0)
                },
                'tags': unique_tags[:50]  # Limit to top 50 tags
            })

        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Failed to get filter options'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SpendingBudgetViewSet(viewsets.ModelViewSet):
    queryset = SpendingBudget.objects.all()
    serializer_class = SpendingBudgetSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """Allow admin users full access to budget management"""
        if (self.request.user.is_authenticated and 
            hasattr(self.request.user, 'role') and 
            self.request.user.role == 'admin'):
            return []
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def budget_summary(self, request):
        """Get budget utilization summary"""
        try:
            budgets = SpendingBudget.objects.filter(is_active=True)
            budget_data = []

            for budget in budgets:
                spent_amount = budget.get_spent_amount()
                remaining_amount = budget.get_remaining_amount()
                utilization_percentage = budget.get_utilization_percentage()

                budget_data.append({
                    'id': budget.id,
                    'name': budget.budget_name,
                    'category': budget.category.name if budget.category else 'All Categories',
                    'budget_amount': float(budget.budget_amount),
                    'spent_amount': float(spent_amount),
                    'remaining_amount': float(remaining_amount),
                    'utilization_percentage': utilization_percentage,
                    'period_type': budget.period_type,
                    'start_date': budget.start_date,
                    'end_date': budget.end_date,
                    'status': 'over_budget' if remaining_amount < 0 else 'on_track'
                })

            return Response({
                'budgets': budget_data,
                'total_budgets': len(budget_data),
                'over_budget_count': len([b for b in budget_data if b['status'] == 'over_budget'])
            })

        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Failed to get budget summary'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def spending_comparison(request):
    """Compare spending across different periods"""
    try:
        # Get comparison parameters
        period1_start = request.query_params.get('period1_start')
        period1_end = request.query_params.get('period1_end')
        period2_start = request.query_params.get('period2_start')
        period2_end = request.query_params.get('period2_end')

        if not all([period1_start, period1_end, period2_start, period2_end]):
            return Response({
                'error': 'All period dates are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Parse dates
        period1_start = datetime.strptime(period1_start, '%Y-%m-%d').date()
        period1_end = datetime.strptime(period1_end, '%Y-%m-%d').date()
        period2_start = datetime.strptime(period2_start, '%Y-%m-%d').date()
        period2_end = datetime.strptime(period2_end, '%Y-%m-%d').date()

        # Get spending for both periods
        period1_spent = InventoryEntry.objects.filter(
            purchase_date__gte=period1_start,
            purchase_date__lte=period1_end
        ).aggregate(total=Sum('total_cost'))['total'] or Decimal('0.00')

        period2_spent = InventoryEntry.objects.filter(
            purchase_date__gte=period2_start,
            purchase_date__lte=period2_end
        ).aggregate(total=Sum('total_cost'))['total'] or Decimal('0.00')

        # Calculate comparison metrics
        difference = period2_spent - period1_spent
        percentage_change = 0
        if period1_spent > 0:
            percentage_change = float((difference / period1_spent) * 100)

        return Response({
            'period1': {
                'start_date': period1_start,
                'end_date': period1_end,
                'total_spent': float(period1_spent)
            },
            'period2': {
                'start_date': period2_start,
                'end_date': period2_end,
                'total_spent': float(period2_spent)
            },
            'comparison': {
                'difference': float(difference),
                'percentage_change': percentage_change,
                'trend': 'increase' if difference > 0 else 'decrease' if difference < 0 else 'same'
            }
        })

    except Exception as e:
        return Response({
            'error': str(e),
            'message': 'Failed to generate spending comparison'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
