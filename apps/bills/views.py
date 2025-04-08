from rest_framework import generics, permissions
from .models import Bill
from .serializers import BillSerializer

class BillCreateView(generics.CreateAPIView):
    queryset = Bill.objects.all()
    serializer_class = BillSerializer
    permission_classes = [permissions.IsAuthenticated]


class BillListView(generics.ListAPIView):
    queryset = Bill.objects.all().order_by('-created_at')
    serializer_class = BillSerializer
    permission_classes = [permissions.IsAdminUser]  # Optional

