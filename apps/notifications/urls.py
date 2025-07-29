from django.urls import path
from .views import (
    NotificationRecipientListCreateView,
    NotificationRecipientRetrieveUpdateDestroyView,
    twilio_delivery_status,
)

urlpatterns = [
    path('', NotificationRecipientListCreateView.as_view(), name='notification-recipient-list-create'),
    path('<int:pk>/', NotificationRecipientRetrieveUpdateDestroyView.as_view(), name='notification-recipient-detail'),
    path('twilio/delivery/', twilio_delivery_status, name='twilio_delivery_status'),
]
