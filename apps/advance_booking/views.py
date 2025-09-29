from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import timedelta
from .models import AdvanceBooking, BookingPayment, BookingStatusHistory
from .serializers import (
    AdvanceBookingSerializer, 
    AdvanceBookingListSerializer,
    BookingPaymentSerializer
)
from .permissions import IsAdminUser, IsStaffOrReadOnly

class AdvanceBookingListCreateView(generics.ListCreateAPIView):
    """
    List all advance bookings or create a new one - Admin only
    """
    queryset = AdvanceBooking.objects.all()
    serializer_class = AdvanceBookingSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['booking_date', 'status', 'customer_phone']

    def get_queryset(self):
        """Filter queryset based on query parameters"""
        queryset = AdvanceBooking.objects.select_related('created_by').prefetch_related(
            'payments', 'status_history'
        )
        
        # Search filter
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(customer_name__icontains=search) |
                Q(customer_phone__icontains=search) |
                Q(customer_aadhar__icontains=search)
            )
            
        # Date range filters
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(booking_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(booking_date__lte=date_to)
            
        # Payment status filter
        payment_status = self.request.query_params.get('payment_status')
        if payment_status == 'pending':
            queryset = queryset.filter(remaining_amount__gt=0)
        elif payment_status == 'paid':
            queryset = queryset.filter(remaining_amount=0)
            
        return queryset.order_by('booking_date', 'booking_time')

    def perform_create(self, serializer):
        """Save with current user as creator"""
        serializer.save(created_by=self.request.user)


class AdvanceBookingDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete an advance booking - Admin only
    """
    queryset = AdvanceBooking.objects.select_related('created_by').prefetch_related(
        'payments', 'status_history'
    )
    serializer_class = AdvanceBookingSerializer
    permission_classes = [IsAdminUser]

    def destroy(self, request, *args, **kwargs):
        """Delete booking with proper response"""
        instance = self.get_object()
        customer_name = instance.customer_name
        self.perform_destroy(instance)
        return Response(
            {'message': f'Advance booking for {customer_name} deleted successfully'},
            status=status.HTTP_200_OK
        )


@api_view(['GET'])
@permission_classes([IsStaffOrReadOnly])
def booking_dashboard_stats(request):
    """
    Get advance booking statistics for dashboard widgets
    Accessible by admin, staff, and waiters
    """
    try:
        today = timezone.now().date()
        tomorrow = today + timedelta(days=1)
        week_ahead = today + timedelta(days=7)
        
        # Today's bookings
        today_bookings = AdvanceBooking.objects.filter(
            booking_date=today,
            status='confirmed'
        ).order_by('booking_time')
        
        # Statistics
        stats = {
            'today_bookings_count': today_bookings.count(),
            'tomorrow_bookings_count': AdvanceBooking.objects.filter(
                booking_date=tomorrow, status='confirmed'
            ).count(),
            'week_bookings_count': AdvanceBooking.objects.filter(
                booking_date__range=[today, week_ahead], status='confirmed'
            ).count(),
            'pending_payments_count': AdvanceBooking.objects.filter(
                remaining_amount__gt=0, status='confirmed', booking_date__gte=today
            ).count(),
            'pending_payments_amount': float(
                AdvanceBooking.objects.filter(
                    remaining_amount__gt=0, status='confirmed', booking_date__gte=today
                ).aggregate(total=Sum('remaining_amount'))['total'] or 0
            ),
            'today_bookings': AdvanceBookingListSerializer(
                today_bookings[:10], many=True
            ).data
        }
        
        # Additional admin-only stats
        if request.user.is_staff:
            stats.update({
                'total_bookings': AdvanceBooking.objects.count(),
                'total_revenue': float(
                    AdvanceBooking.objects.aggregate(
                        total=Sum('total_amount')
                    )['total'] or 0
                ),
            })
        
        return Response(stats)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to load booking statistics: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def record_payment(request, booking_id):
    """
    Record additional payment for a booking - Admin only
    """
    try:
        booking = AdvanceBooking.objects.get(id=booking_id)
        payment_amount = float(request.data.get('amount', 0))
        payment_method = request.data.get('payment_method', 'cash')
        transaction_ref = request.data.get('transaction_reference', '')
        notes = request.data.get('notes', '')
        
        if payment_amount <= 0:
            return Response(
                {'error': 'Payment amount must be positive'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if payment_amount > float(booking.remaining_amount):
            return Response(
                {'error': 'Payment amount cannot exceed remaining amount'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create payment record
        BookingPayment.objects.create(
            booking=booking,
            amount=payment_amount,
            payment_method=payment_method,
            transaction_reference=transaction_ref,
            notes=notes,
            recorded_by=request.user
        )
        
        # Update booking advance amount
        booking.advance_paid += payment_amount
        booking.save()  # This will recalculate remaining_amount
        
        serializer = AdvanceBookingSerializer(booking)
        return Response({
            'message': f'Payment of ₹{payment_amount} recorded successfully',
            'booking': serializer.data
        })
        
    except AdvanceBooking.DoesNotExist:
        return Response(
            {'error': 'Booking not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'Failed to record payment: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def update_booking_status(request, booking_id):
    """
    Update booking status with reason tracking - Admin only
    """
    try:
        booking = AdvanceBooking.objects.get(id=booking_id)
        new_status = request.data.get('status')
        reason = request.data.get('reason', '')
        
        if not new_status:
            return Response(
                {'error': 'Status is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        valid_statuses = [choice for choice in AdvanceBooking.BOOKING_STATUS_CHOICES]
        if new_status not in valid_statuses:
            return Response(
                {'error': f'Invalid status. Must be one of: {valid_statuses}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_status = booking.status
        booking.status = new_status
        booking.save()
        
        # Record status change
        BookingStatusHistory.objects.create(
            booking=booking,
            old_status=old_status,
            new_status=new_status,
            changed_by=request.user,
            reason=reason
        )
        
        serializer = AdvanceBookingSerializer(booking)
        return Response({
            'message': f'Booking status updated to {new_status}',
            'booking': serializer.data
        })
        
    except AdvanceBooking.DoesNotExist:
        return Response(
            {'error': 'Booking not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'Failed to update status: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def booking_analytics(request):
    """
    Get detailed booking analytics - Admin only
    """
    try:
        today = timezone.now().date()
        last_30_days = today - timedelta(days=30)
        
        # Revenue analytics
        revenue_stats = AdvanceBooking.objects.filter(
            booking_date__gte=last_30_days
        ).aggregate(
            total_revenue=Sum('total_amount'),
            total_advance=Sum('advance_paid'),
            total_pending=Sum('remaining_amount')
        )
        
        # Status distribution
        status_counts = AdvanceBooking.objects.values('status').annotate(
            count=Count('id')
        )
        
        # Monthly trends
        monthly_stats = []
        for i in range(6):
            month_start = today.replace(day=1) - timedelta(days=30 * i)
            next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            month_end = next_month - timedelta(days=1)
            
            month_bookings = AdvanceBooking.objects.filter(
                booking_date__range=[month_start, month_end]
            )
            
            monthly_stats.append({
                'month': month_start.strftime('%B %Y'),
                'bookings_count': month_bookings.count(),
                'total_revenue': float(month_bookings.aggregate(Sum('total_amount'))['total_amount__sum'] or 0)
            })
        
        analytics = {
            'revenue_stats': {
                'total_revenue': float(revenue_stats['total_revenue'] or 0),
                'total_advance': float(revenue_stats['total_advance'] or 0),
                'total_pending': float(revenue_stats['total_pending'] or 0),
            },
            'status_distribution': list(status_counts),
            'monthly_trends': monthly_stats
        }
        
        return Response(analytics)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to load analytics: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
