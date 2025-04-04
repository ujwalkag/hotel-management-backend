from django.shortcuts import render
from django.http import JsonResponse
from apps.bookings.models import Order, MenuItem, RoomService
from django.db.models import Sum, Count
from datetime import timedelta, datetime

def dashboard_home(request):
    return render(request, 'admin_dashboard/dashboard_home.html')

# Order Summary
def order_summary(request):
    
   
    orders = Order.objects.all().count()
    completed_orders = Order.objects.filter(status='completed').count()
    pending_orders = Order.objects.filter(status='pending').count()

    data = {
        'total_orders': orders,
        'completed_orders': completed_orders,
        'pending_orders': pending_orders,
    }
    return JsonResponse(data)

# Sales Overview
def sales_overview(request):
    today = datetime.now()
    daily_sales = Order.objects.filter(created_at__date=today).aggregate(Sum('total_price'))['total_price__sum'] or 0
    weekly_sales = Order.objects.filter(created_at__gte=today - timedelta(days=7)).aggregate(Sum('total_price'))['total_price__sum'] or 0
    monthly_sales = Order.objects.filter(created_at__gte=today - timedelta(days=30)).aggregate(Sum('total_price'))['total_price__sum'] or 0

    data = {
        'daily_sales': daily_sales,
        'weekly_sales': weekly_sales,
        'monthly_sales': monthly_sales,
    }
    return JsonResponse(data)

# Top Items
def top_items(request):
    #top_items = RestaurantItem.objects.annotate(order_count=Count('order')).order_by('-order_count')[:5]
    top_items = MenuItem.objects.annotate(order_count=Count('order')).order_by('-order_count')[:5]
    data = [{'name': item.name, 'orders': item.order_count} for item in top_items]
    return JsonResponse(data, safe=False)

# Revenue Analytics
def revenue_analytics(request):
    daily_revenue = Order.objects.filter(created_at__date=datetime.now()).aggregate(Sum('total_price'))['total_price__sum'] or 0
    data = {
        'daily_revenue': daily_revenue,
        'message': 'Revenue analytics successfully fetched.'
    }
    return JsonResponse(data)

