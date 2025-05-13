from rest_framework import generics, permissions
from .models import NotificationRecipient
from .serializers import NotificationRecipientSerializer

class NotificationRecipientListCreateView(generics.ListCreateAPIView):
    queryset = NotificationRecipient.objects.all()
    serializer_class = NotificationRecipientSerializer
    permission_classes = [permissions.IsAuthenticated]

class NotificationRecipientRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = NotificationRecipient.objects.all()
    serializer_class = NotificationRecipientSerializer
    permission_classes = [permissions.IsAuthenticated]

