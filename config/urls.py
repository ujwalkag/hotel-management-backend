# config/urls.py - COMPLETE UPDATED VERSION
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from apps.users.views import CustomTokenObtainPairView ,  verify_token
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
    path('api/rooms/bookings/', include('apps.rooms.urls')),
    path('api/auth/verify/', verify_token, name='token_verify'),
    path('api/staff-management/', include('apps.staff_management.urls')),
    path('api/restaurant/', include('apps.restaurant.urls')),
    path('api/advance-booking/', include('apps.advance_booking.urls')),
    #router.register(r"admin/tables", AdminTableViewSet, basename="admin-table")
  # This makes frontend calls work!
    #path('api/staff-management/', include('apps.staff_management.urls')),

    #path('api/staff/', include('apps.staff.urls')), 
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
