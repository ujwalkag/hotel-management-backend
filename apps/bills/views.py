from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from io import BytesIO

from .models import Bill
from .serializers import BillSerializer


class BillCreateView(generics.CreateAPIView):
    queryset = Bill.objects.all()
    serializer_class = BillSerializer
    permission_classes = [permissions.IsAuthenticated]


class BillListView(generics.ListAPIView):
    queryset = Bill.objects.all().order_by('-created_at')
    serializer_class = BillSerializer
    permission_classes = [permissions.IsAdminUser]


class BillInvoicePDFView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            bill = Bill.objects.get(pk=pk)
        except Bill.DoesNotExist:
            return Response({"error": "Bill not found"}, status=status.HTTP_404_NOT_FOUND)

        buffer = BytesIO()
        p = canvas.Canvas(buffer)

        # Title
        p.setFont("Helvetica-Bold", 16)
        p.drawString(100, 800, f"Hotel Invoice - Bill #{bill.id}")

        # Basic info
        p.setFont("Helvetica", 12)
        p.drawString(100, 770, f"Date: {bill.created_at.strftime('%d-%m-%Y')}")
        p.drawString(100, 750, f"Created By: {bill.created_by.username if bill.created_by else 'N/A'}")

        if bill.room:
            p.drawString(100, 730, f"Room: {bill.room}")

        # Line items
        y = 700
        p.setFont("Helvetica-Bold", 12)
        p.drawString(100, y, "Items:")
        y -= 20

        p.setFont("Helvetica", 12)
        for item in bill.items.all():
            p.drawString(120, y, f"{item.quantity} x {item.item.name} - ₹{item.total_price}")
            y -= 20

        # Total
        p.setFont("Helvetica-Bold", 12)
        p.drawString(100, y - 10, f"Total Amount: ₹{bill.total_amount}")
        p.showPage()
        p.save()

        buffer.seek(0)
        return HttpResponse(buffer, content_type='application/pdf')

