from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', admin.site.urls),  # Admin path
    path('auth/', include('apps.authentication.urls')),  # Auth app
    path('bookings/', include('apps.bookings.urls')),    # Bookings app
    path('payments/', include('apps.payments.urls')),    # Payments app
    path('notifications/', include('apps.notifications.urls')),  # Notifications app
]
