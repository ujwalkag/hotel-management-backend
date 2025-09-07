from django.urls import path
from .enhanced_views import EnhancedBillingViewSet

urlpatterns = [
    path('dashboard/', EnhancedBillingViewSet.as_view({'get': 'active_tables_dashboard'}), name='billing-dashboard'),
    path('create-table-bill/', EnhancedBillingViewSet.as_view({'post': 'create_table_bill'}), name='create-table-bill'),
    path('add-item/', EnhancedBillingViewSet.as_view({'post': 'add_item_to_bill'}), name='add-bill-item'),
    path('apply-gst/', EnhancedBillingViewSet.as_view({'post': 'apply_gst_to_bill'}), name='apply-gst'),
    path('delete-item/', EnhancedBillingViewSet.as_view({'delete': 'delete_bill_item'}), name='delete-bill-item'),
    path('finalize-bill/', EnhancedBillingViewSet.as_view({'post': 'finalize_bill_and_release_table'}), name='finalize-bill'),
]
