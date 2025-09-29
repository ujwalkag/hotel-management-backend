from django.urls import path
from .views import (
    AdvanceBookingListCreateView,
    AdvanceBookingDetailView,
    booking_dashboard_stats,
    record_payment,
    update_booking_status,
    booking_analytics,
)

app_name = 'advance_booking'

urlpatterns = [
    # Main CRUD endpoints
    path('', AdvanceBookingListCreateView.as_view(), name='booking-list-create'),
    path('<int:pk>/', AdvanceBookingDetailView.as_view(), name='booking-detail'),
    
    # Dashboard stats (accessible by all authenticated users)
    path('dashboard-stats/', booking_dashboard_stats, name='dashboard-stats'),
    
    # Admin-only actions
    path('<int:booking_id>/record-payment/', record_payment, name='record-payment'),
    path('<int:booking_id>/update-status/', update_booking_status, name='update-status'),
    path('analytics/', booking_analytics, name='analytics'),
]
