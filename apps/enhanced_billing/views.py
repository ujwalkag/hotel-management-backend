
# apps/enhanced_billing/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum, Count, Q
from .models import EnhancedBill, EnhancedBillItem, BillPaymentRecord, BillingSession
from .serializers import (
    EnhancedBillSerializer, EnhancedBillItemSerializer, BillPaymentRecordSerializer,
    BillingSessionSerializer, PaymentProcessSerializer, BillFromSessionSerializer
)

class EnhancedBillViewSet(viewsets.ModelViewSet):
    queryset = EnhancedBill.objects.all()
    serializer_class = EnhancedBillSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def create_from_session(self, request):
        """Create bill from table session - MOBILE ORDER INTEGRATION"""
        serializer = BillFromSessionSerializer(data=request.data)
        if serializer.is_valid():
            table_session_id = serializer.validated_data['table_session_id']
            customer_name = serializer.validated_data['customer_name']
            customer_phone = serializer.validated_data.get('customer_phone', '')
            discount_percentage = serializer.validated_data['discount_percentage']

            # Create enhanced bill
            bill = EnhancedBill.objects.create(
                customer_name=customer_name,
                customer_phone=customer_phone,
                discount_percentage=discount_percentage,
                created_by=request.user
            )

            # Add orders from session
            bill.add_orders_from_session(table_session_id)

            return Response({
                'success': True,
                'bill': EnhancedBillSerializer(bill).data,
                'message': 'Bill created from table session successfully'
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def create_manual(self, request):
        """Create manual bill (traditional billing)"""
        customer_name = request.data.get('customer_name', 'Guest')
        customer_phone = request.data.get('customer_phone', '')
        items_data = request.data.get('items', [])

        # Create enhanced bill
        bill = EnhancedBill.objects.create(
            customer_name=customer_name,
            customer_phone=customer_phone,
            created_by=request.user
        )

        # Add manual items
        bill.add_manual_items(items_data)

        return Response({
            'success': True,
            'bill': EnhancedBillSerializer(bill).data,
            'message': 'Manual bill created successfully'
        })

    @action(detail=True, methods=['post'])
    def process_payment(self, request, pk=None):
        """Process payment for bill - MULTI-PAYMENT SUPPORT"""
        bill = self.get_object()
        serializer = PaymentProcessSerializer(data=request.data)

        if serializer.is_valid():
            payment_method = serializer.validated_data['payment_method']
            cash_amount = serializer.validated_data['cash_amount']
            card_amount = serializer.validated_data['card_amount']
            upi_amount = serializer.validated_data['upi_amount']

            success = bill.process_payment(
                payment_method=payment_method,
                cash=cash_amount,
                card=card_amount,
                upi=upi_amount,
                processed_by=request.user
            )

            if success:
                return Response({
                    'success': True,
                    'message': 'Payment processed successfully',
                    'bill': EnhancedBillSerializer(bill).data
                })
            else:
                return Response({
                    'success': True,
                    'message': 'Partial payment processed',
                    'bill': EnhancedBillSerializer(bill).data
                })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def receipt_data(self, request, pk=None):
        """Get receipt data for printing"""
        bill = self.get_object()
        return Response(bill.generate_receipt_data())

    @action(detail=False, methods=['get'])
    def pending_bills(self, request):
        """Get bills ready for payment"""
        bills = EnhancedBill.objects.filter(
            status__in=['draft', 'ready']
        ).order_by('-created_at')
        serializer = self.get_serializer(bills, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def today_summary(self, request):
        """Get today's billing summary"""
        today = timezone.now().date()
        bills = EnhancedBill.objects.filter(bill_date=today)

        total_bills = bills.count()
        paid_bills = bills.filter(status='paid').count()
        total_amount = bills.aggregate(Sum('final_amount'))['final_amount__sum'] or 0
        cash_collected = bills.aggregate(Sum('cash_amount'))['cash_amount__sum'] or 0
        card_collected = bills.aggregate(Sum('card_amount'))['card_amount__sum'] or 0
        upi_collected = bills.aggregate(Sum('upi_amount'))['upi_amount__sum'] or 0

        return Response({
            'total_bills': total_bills,
            'paid_bills': paid_bills,
            'pending_bills': total_bills - paid_bills,
            'total_amount': total_amount,
            'cash_collected': cash_collected,
            'card_collected': card_collected,
            'upi_collected': upi_collected
        })

class BillPaymentRecordViewSet(viewsets.ModelViewSet):
    queryset = BillPaymentRecord.objects.all()
    serializer_class = BillPaymentRecordSerializer
    permission_classes = [IsAuthenticated]

class BillingSessionViewSet(viewsets.ModelViewSet):
    queryset = BillingSession.objects.all()
    serializer_class = BillingSessionSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def start_session(self, request):
        """Start a new billing session"""
        session = BillingSession.objects.create(
            biller=request.user,
            device_info=request.data.get('device_info', {}),
            ip_address=request.META.get('REMOTE_ADDR')
        )

        return Response({
            'success': True,
            'session': BillingSessionSerializer(session).data,
            'message': 'Billing session started'
        })

    @action(detail=True, methods=['post'])
    def end_session(self, request, pk=None):
        """End billing session"""
        session = self.get_object()
        session.end_session()

        return Response({
            'success': True,
            'session': BillingSessionSerializer(session).data,
            'message': 'Billing session ended'
        })

