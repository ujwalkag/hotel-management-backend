from django.db import models
from apps.users.models import CustomUser
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import datetime, date, timedelta

class InventoryCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def total_entries(self):
        return self.entries.count()

    @property
    def total_spent(self):
        return self.entries.aggregate(
            total=models.Sum('total_cost')
        )['total'] or Decimal('0.00')

    def get_spent_by_period(self, start_date=None, end_date=None):
        """Get total spent in specific period"""
        queryset = self.entries.all()
        if start_date:
            queryset = queryset.filter(purchase_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(purchase_date__lte=end_date)
        return queryset.aggregate(total=Sum('total_cost'))['total'] or Decimal('0.00')

    def get_monthly_spent(self, year, month):
        """Get total spent in specific month"""
        return self.entries.filter(
            purchase_date__year=year,
            purchase_date__month=month
        ).aggregate(total=Sum('total_cost'))['total'] or Decimal('0.00')

    class Meta:
        db_table = 'inventory_category'
        verbose_name = 'Inventory Category'
        verbose_name_plural = 'Inventory Categories'
        ordering = ['name']

class InventoryEntry(models.Model):
    # Existing fields
    category = models.ForeignKey(
        InventoryCategory, 
        on_delete=models.CASCADE, 
        related_name='entries'
    )
    item_name = models.CharField(max_length=200)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2)
    purchase_date = models.DateField()
    supplier_name = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Enhanced fields for better filtering and analysis
    unit_type = models.CharField(max_length=50, default='pieces', help_text='kg, ltr, pieces, etc.')
    is_recurring = models.BooleanField(default=False, help_text='Is this a regular purchase?')
    priority = models.CharField(
        max_length=20, 
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('urgent', 'Urgent')
        ],
        default='medium'
    )
    tags = models.CharField(max_length=500, blank=True, help_text='Comma-separated tags for filtering')

    def save(self, *args, **kwargs):
        # Auto-calculate total cost
        self.total_cost = self.price_per_unit * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item_name} - {self.category.name} - ₹{self.total_cost}"

    @classmethod
    def get_spending_analytics(cls, filters=None):
        """Get comprehensive spending analytics"""
        queryset = cls.objects.all()

        if filters:
            # Apply date filters
            if filters.get('start_date'):
                queryset = queryset.filter(purchase_date__gte=filters['start_date'])
            if filters.get('end_date'):
                queryset = queryset.filter(purchase_date__lte=filters['end_date'])

            # Apply category filter
            if filters.get('category'):
                queryset = queryset.filter(category_id=filters['category'])

            # Apply supplier filter
            if filters.get('supplier'):
                queryset = queryset.filter(supplier_name__icontains=filters['supplier'])

            # Apply priority filter
            if filters.get('priority'):
                queryset = queryset.filter(priority=filters['priority'])

            # Apply cost range filter
            if filters.get('min_cost'):
                queryset = queryset.filter(total_cost__gte=filters['min_cost'])
            if filters.get('max_cost'):
                queryset = queryset.filter(total_cost__lte=filters['max_cost'])

            # Apply search filter
            if filters.get('search'):
                search = filters['search']
                queryset = queryset.filter(
                    Q(item_name__icontains=search) |
                    Q(supplier_name__icontains=search) |
                    Q(notes__icontains=search) |
                    Q(tags__icontains=search)
                )

        # Calculate analytics
        total_spent = queryset.aggregate(total=Sum('total_cost'))['total'] or Decimal('0.00')
        total_entries = queryset.count()
        avg_cost_per_entry = total_spent / total_entries if total_entries > 0 else Decimal('0.00')

        # Category-wise breakdown
        category_breakdown = queryset.values('category__name').annotate(
            total_spent=Sum('total_cost'),
            entry_count=Count('id')
        ).order_by('-total_spent')

        # Supplier-wise breakdown
        supplier_breakdown = queryset.values('supplier_name').annotate(
            total_spent=Sum('total_cost'),
            entry_count=Count('id')
        ).order_by('-total_spent')

        # Monthly trend (last 12 months)
        monthly_trend = []
        for i in range(12):
            month_date = datetime.now() - timedelta(days=30*i)
            month_spent = queryset.filter(
                purchase_date__year=month_date.year,
                purchase_date__month=month_date.month
            ).aggregate(total=Sum('total_cost'))['total'] or Decimal('0.00')

            monthly_trend.append({
                'month': month_date.strftime('%b %Y'),
                'spent': float(month_spent)
            })

        # Priority-wise breakdown
        priority_breakdown = queryset.values('priority').annotate(
            total_spent=Sum('total_cost'),
            entry_count=Count('id')
        ).order_by('-total_spent')

        return {
            'total_spent': float(total_spent),
            'total_entries': total_entries,
            'avg_cost_per_entry': float(avg_cost_per_entry),
            'category_breakdown': list(category_breakdown),
            'supplier_breakdown': list(supplier_breakdown),
            'monthly_trend': monthly_trend[::-1],  # Reverse to show oldest first
            'priority_breakdown': list(priority_breakdown),
            'filters_applied': filters or {}
        }

    class Meta:
        db_table = 'inventory_entry'
        verbose_name = 'Inventory Entry'
        verbose_name_plural = 'Inventory Entries'
        ordering = ['-created_at']

class SpendingBudget(models.Model):
    """Budget tracking for inventory spending"""
    category = models.ForeignKey(InventoryCategory, on_delete=models.CASCADE, null=True, blank=True)
    budget_name = models.CharField(max_length=200)
    budget_amount = models.DecimalField(max_digits=12, decimal_places=2)
    period_type = models.CharField(
        max_length=20,
        choices=[
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('yearly', 'Yearly'),
            ('custom', 'Custom Period')
        ],
        default='monthly'
    )
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.budget_name} - ₹{self.budget_amount}"

    def get_spent_amount(self):
        """Get total spent against this budget"""
        queryset = InventoryEntry.objects.filter(
            purchase_date__gte=self.start_date,
            purchase_date__lte=self.end_date
        )

        if self.category:
            queryset = queryset.filter(category=self.category)

        return queryset.aggregate(total=Sum('total_cost'))['total'] or Decimal('0.00')

    def get_remaining_amount(self):
        """Get remaining budget amount"""
        spent = self.get_spent_amount()
        return self.budget_amount - spent

    def get_utilization_percentage(self):
        """Get budget utilization percentage"""
        spent = self.get_spent_amount()
        if self.budget_amount > 0:
            return float((spent / self.budget_amount) * 100)
        return 0.0

    class Meta:
        db_table = 'inventory_spending_budget'
        verbose_name = 'Spending Budget'
        verbose_name_plural = 'Spending Budgets'
        ordering = ['-created_at']
