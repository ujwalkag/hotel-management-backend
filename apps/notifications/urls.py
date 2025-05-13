from django.urls import path
from .views import NotificationRecipientListCreateView, NotificationRecipientRetrieveUpdateDestroyView

urlpatterns = [
    path('', NotificationRecipientListCreateView.as_view(), name='notification-recipient-list-create'),
    path('<int:pk>/', NotificationRecipientRetrieveUpdateDestroyView.as_view(), name='notification-recipient-detail'),
]

