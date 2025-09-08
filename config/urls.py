# config/urls.py - COMPLETE UPDATED VERSION
from django.contrib import admin
from django.urls import path, include
from apps.users.views import CustomTokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('api/auth/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('admin/', admin.site.urls),
    path('api/core/', include('apps.core.urls')),
    path('api/menu/', include('apps.menu.urls')),
    path('api/rooms/', include('apps.rooms.urls')),
    path('api/users/', include('apps.users.urls')),
    path('api/bills/', include('apps.bills.urls')),
    path('api/inventory/', include('apps.inventory.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/staff/', include('apps.staff.urls')),
    # NEW API ENDPOINTS
    path('api/mobile-orders/', include('apps.mobile_ordering.urls')),
    path('api/enhanced-billing/', include('apps.enhanced_billing.urls')),
    #path('api/tables/', include('apps.tables.urls')),
    
]

