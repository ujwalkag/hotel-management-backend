# apps/bills/enhanced_urls.py - FIXED TO MATCH FRONTEND CALLS
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .enhanced_views import EnhancedBillingViewSet

# Create router for viewset actions
router = DefaultRouter()
router.register(r'enhanced-billing', EnhancedBillingViewSet, basename='enhanced-billing')

urlpatterns = [
    # Enhanced billing endpoints that match your frontend calls exactly
    path('enhanced/active_tables_dashboard/', 
         EnhancedBillingViewSet.as_view({'get': 'active_tables_dashboard'}), 
         name='active-tables-dashboard'),

    path('enhanced/update_customer_details/', 
         EnhancedBillingViewSet.as_view({'post': 'update_customer_details'}), 
         name='update-customer-details'),

    path('enhanced/add_custom_item_to_table/', 
         EnhancedBillingViewSet.as_view({'post': 'add_custom_item_to_table'}), 
         name='add-custom-item'),

    path('enhanced/delete_item_from_table/', 
         EnhancedBillingViewSet.as_view({'delete': 'delete_item_from_table'}), 
         name='delete-item'),

    path('enhanced/update_item_quantity/', 
         EnhancedBillingViewSet.as_view({'patch': 'update_item_quantity'}), 
         name='update-quantity'),

    path('enhanced/calculate_bill_with_gst/', 
         EnhancedBillingViewSet.as_view({'post': 'calculate_bill_with_gst'}), 
         name='calculate-bill'),

    path('enhanced/generate_final_bill/', 
         EnhancedBillingViewSet.as_view({'post': 'generate_final_bill'}), 
         name='generate-bill'),

    # Include the router URLs for RESTful access
    path('', include(router.urls)),
]

