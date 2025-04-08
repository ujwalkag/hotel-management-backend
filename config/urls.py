from django.contrib import admin
from django.urls import path, include
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions  # <-- Add this
from apps.admin_dashboard import views as dashboard_views

# API schema settings
schema_view = get_schema_view(
    openapi.Info(
        title="Hotel Management API",
        default_version="v1",
        description="API documentation for Hotel Management System",
        terms_of_service="https://www.hotelrshammad.co.in/terms/",
        contact=openapi.Contact(email="support@hotelrshammad.co.in"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
        
    path('admin/', admin.site.urls),  # Admin path
    path('api/auth/', include('apps.authentication.urls')),  # Auth JWT paths
    path('api/menu/', include('apps.menu.urls')),
    path('api/bookings/', include('apps.bookings.urls')),  # Bookings app
    path('api/payments/', include('apps.payments.urls')),  # Payments app
    path('api/notifications/', include('apps.notifications.urls')),  # Notifications app
    path('dashboard/', include('apps.admin_dashboard.urls')),  # Admin dashboard
    path("api/bill/", include("apps.bills.urls")),
    #path('api/bill/create/',apps.BillCreateAPIView.as_view(), name='create-bill'),
    # ✅ Add this line below:
    path('api/admin-dashboard/', include('apps.admin_dashboard.urls')),

    # API documentation
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='api-docs'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='api-redoc'),
]

