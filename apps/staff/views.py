# apps/staff/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Sum, Count
from datetime import datetime, timedelta
from .models import StaffProfile, Attendance, PaymentRecord, AdvancePayment
from .serializers import (
    StaffProfileSerializer,
    AttendanceSerializer,
    AttendanceCreateSerializer,
    BulkAttendanceSerializer,
    PaymentRecordSerializer,
    AdvancePaymentSerializer,
    StaffSummarySerializer,
    AttendanceSummarySerializer
)
from .permissions import IsAdminOnly, IsAdminOrStaff, CanMarkAttendance

class StaffProfileViewSet(viewsets.ModelViewSet):
    queryset = StaffProfile.objects.filter(is_active=True)
    serializer_class = StaffProfileSerializer
    permission_classes = [IsAuthenticated, IsAdminOnly]  # Admin only for staff management

    def get_queryset(self):
        queryset = StaffProfile.objects.all()
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Filter by position
        position = self.request.query_params.get('position', None)
        if position:
            queryset = queryset.filter(position=position)
        
        # Search by name, employee_id, or phone
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(user__email__icontains=search) |
                Q(employee_id__icontains=search) |
                Q(phone__icontains=search)
            )
            
        return queryset.select_related('user').order_by('employee_id')

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get staff summary for dashboard"""
        queryset = self.get_queryset()
        serializer = StaffSummarySerializer(queryset, many=True)
        
        # Add summary statistics
        total_staff = queryset.count()
        active_staff = queryset.filter(is_active=True).count()
        total_pending_salary = sum(staff.pending_salary for staff in queryset)
        
        # Position breakdown
        position_breakdown = queryset.values('position').annotate(
            count=Count('id')
        ).order_by('position')
        
        return Response({
            'staff': serializer.data,
            'summary': {
                'total_staff': total_staff,
                'active_staff': active_staff,
                'inactive_staff': total_staff - active_staff,
                'total_pending_salary': float(total_pending_salary),
                'position_breakdown': list(position_breakdown)
            }
        })

    @action(detail=True, methods=['get'])
    def attendance_history(self, request, pk=None):
        """Get attendance history for a staff member"""
        staff = self.get_object()
        
        # Date filters
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        
        queryset = staff.attendance_records.all()
        
        if from_date:
            try:
                from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
                queryset = queryset.filter(date__gte=from_date_obj)
            except ValueError:
                pass
                
        if to_date:
            try:
                to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
                queryset = queryset.filter(date__lte=to_date_obj)
            except ValueError:
                pass
            
        serializer = AttendanceSerializer(queryset, many=True)
        
        # Calculate summary
        total_days = queryset.count()
        present_days = queryset.filter(status='present').count()
        absent_days = queryset.filter(status='absent').count()
        total_earned = queryset.aggregate(total=Sum('salary_amount'))['total'] or 0
        
        return Response({
            'attendance_records': serializer.data,
            'summary': {
                'total_days': total_days,
                'present_days': present_days,
                'absent_days': absent_days,
                'attendance_percentage': round((present_days / total_days * 100), 2) if total_days > 0 else 0,
                'total_earned': float(total_earned)
            }
        })

    @action(detail=True, methods=['get'])
    def payment_history(self, request, pk=None):
        """Get payment history for a staff member"""
        staff = self.get_object()
        payments = staff.payment_records.all()
        serializer = PaymentRecordSerializer(payments, many=True)
        
        # Calculate summary
        total_paid = payments.aggregate(total=Sum('amount_paid'))['total'] or 0
        
        return Response({
            'payment_records': serializer.data,
            'summary': {
                'total_payments': payments.count(),
                'total_amount_paid': float(total_paid)
            }
        })

    @action(detail=True, methods=['get'])
    def advance_history(self, request, pk=None):
        """Get advance payment history for a staff member"""
        staff = self.get_object()
        advances = staff.advance_payments.all()
        serializer = AdvancePaymentSerializer(advances, many=True)
        
        # Calculate summary
        total_advances = advances.aggregate(total=Sum('amount'))['total'] or 0
        pending_advances = advances.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0
        
        return Response({
            'advance_records': serializer.data,
            'summary': {
                'total_advances': advances.count(),
                'total_advance_amount': float(total_advances),
                'pending_advance_amount': float(pending_advances)
            }
        })

class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all()
    permission_classes = [IsAuthenticated, CanMarkAttendance]

    def get_serializer_class(self):
        if self.action == 'create':
            return AttendanceCreateSerializer
        return AttendanceSerializer

    def get_queryset(self):
        queryset = Attendance.objects.select_related('staff__user', 'marked_by')
        
        # Filter by date
        date_filter = self.request.query_params.get('date')
        if date_filter:
            try:
                date_obj = datetime.strptime(date_filter, '%Y-%m-%d').date()
                queryset = queryset.filter(date=date_obj)
            except ValueError:
                pass
        
        # Filter by staff
        staff_id = self.request.query_params.get('staff')
        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)
            
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by date range
        from_date = self.request.query_params.get('from_date')
        to_date = self.request.query_params.get('to_date')
        
        if from_date:
            try:
                from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
                queryset = queryset.filter(date__gte=from_date_obj)
            except ValueError:
                pass
                
        if to_date:
            try:
                to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
                queryset = queryset.filter(date__lte=to_date_obj)
            except ValueError:
                pass
            
        return queryset.order_by('-date', 'staff__employee_id')

    def perform_create(self, serializer):
        serializer.save(marked_by=self.request.user)

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Bulk create attendance records for a date"""
        serializer = BulkAttendanceSerializer(data=request.data)
        
        if serializer.is_valid():
            date = serializer.validated_data['date']
            records = serializer.validated_data['attendance_records']
            
            created_records = []
            updated_records = []
            errors = []
            
            for record_data in records:
                try:
                    staff = StaffProfile.objects.get(id=record_data['staff_id'])
                    
                    # Check if attendance already exists for this date
                    existing = Attendance.objects.filter(
                        staff=staff, 
                        date=date
                    ).first()
                    
                    attendance_data = {
                        'status': record_data['status'],
                        'check_in_time': record_data.get('check_in_time'),
                        'check_out_time': record_data.get('check_out_time'),
                        'total_hours': record_data.get('total_hours', 8),
                        'overtime_hours': record_data.get('overtime_hours', 0),
                        'notes': record_data.get('notes', ''),
                        'marked_by': request.user
                    }
                    
                    if existing:
                        # Update existing record
                        for key, value in attendance_data.items():
                            if key != 'marked_by' and value is not None:
                                setattr(existing, key, value)
                        existing.marked_by = request.user
                        existing.save()
                        updated_records.append(existing)
                    else:
                        # Create new record
                        attendance = Attendance.objects.create(
                            staff=staff,
                            date=date,
                            **attendance_data
                        )
                        created_records.append(attendance)
                        
                except StaffProfile.DoesNotExist:
                    errors.append(f"Staff with ID {record_data['staff_id']} not found")
                except Exception as e:
                    errors.append(f"Error processing staff {record_data['staff_id']}: {str(e)}")
            
            return Response({
                'message': f'{len(created_records)} created, {len(updated_records)} updated',
                'created_count': len(created_records),
                'updated_count': len(updated_records),
                'errors': errors
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def daily_report(self, request):
        """Get daily attendance report"""
        date_str = request.query_params.get('date', timezone.now().date())
        
        if isinstance(date_str, str):
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Invalid date format'}, status=400)
        else:
            date = date_str

        all_staff = StaffProfile.objects.filter(is_active=True)
        attendance_records = Attendance.objects.filter(date=date).select_related('staff__user')
        
        # Create attendance mapping
        attendance_map = {record.staff.id: record for record in attendance_records}
        
        report_data = []
        summary = {
            'present': 0, 'absent': 0, 'half_day': 0, 
            'leave': 0, 'overtime': 0, 'total': 0,
            'total_salary': 0
        }
        
        for staff in all_staff:
            attendance = attendance_map.get(staff.id)
            
            if attendance:
                status_val = attendance.status
                record_data = AttendanceSerializer(attendance).data
            else:
                status_val = 'absent'
                record_data = {
                    'id': None,
                    'staff': staff.id,
                    'staff_name': staff.user.email,
                    'employee_id': staff.employee_id,
                    'position': staff.position,
                    'date': date,
                    'status': 'absent',
                    'salary_amount': '0.00'
                }
            
            report_data.append(record_data)
            summary[status_val] = summary.get(status_val, 0) + 1
            summary['total'] += 1
            summary['total_salary'] += float(record_data.get('salary_amount', 0))
        
        return Response({
            'date': date,
            'attendance': report_data,
            'summary': summary
        })

    @action(detail=False, methods=['get'])
    def monthly_summary(self, request):
        """Get monthly attendance summary"""
        year = int(request.query_params.get('year', timezone.now().year))
        month = int(request.query_params.get('month', timezone.now().month))
        
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        attendance_data = Attendance.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).values('date').annotate(
            total_staff=Count('id'),
            present_count=Count('id', filter=Q(status='present')),
            absent_count=Count('id', filter=Q(status='absent')),
            half_day_count=Count('id', filter=Q(status='half_day')),
            leave_count=Count('id', filter=Q(status='leave')),
            overtime_count=Count('id', filter=Q(status='overtime')),
            total_salary=Sum('salary_amount')
        ).order_by('date')
        
        return Response({
            'month': month,
            'year': year,
            'summary': list(attendance_data)
        })

class PaymentRecordViewSet(viewsets.ModelViewSet):
    queryset = PaymentRecord.objects.all()
    serializer_class = PaymentRecordSerializer
    permission_classes = [IsAuthenticated, IsAdminOnly]  # Admin only for payments

    def get_queryset(self):
        queryset = PaymentRecord.objects.select_related('staff__user', 'paid_by')
        
        # Filter by staff
        staff_id = self.request.query_params.get('staff')
        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)
            
        # Filter by payment type
        payment_type = self.request.query_params.get('payment_type')
        if payment_type:
            queryset = queryset.filter(payment_type=payment_type)
            
        # Filter by date range
        from_date = self.request.query_params.get('from_date')
        to_date = self.request.query_params.get('to_date')
        
        if from_date:
            try:
                from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
                queryset = queryset.filter(payment_date__gte=from_date_obj)
            except ValueError:
                pass
                
        if to_date:
            try:
                to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
                queryset = queryset.filter(payment_date__lte=to_date_obj)
            except ValueError:
                pass
            
        return queryset.order_by('-payment_date')

    def perform_create(self, serializer):
        serializer.save(paid_by=self.request.user)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get payment summary"""
        queryset = self.get_queryset()
        
        total_payments = queryset.count()
        total_amount = queryset.aggregate(total=Sum('amount_paid'))['total'] or 0
        
        # Payment type breakdown
        payment_breakdown = queryset.values('payment_type').annotate(
            count=Count('id'),
            total_amount=Sum('amount_paid')
        ).order_by('payment_type')
        
        return Response({
            'total_payments': total_payments,
            'total_amount': float(total_amount),
            'payment_breakdown': list(payment_breakdown)
        })

class AdvancePaymentViewSet(viewsets.ModelViewSet):
    queryset = AdvancePayment.objects.all()
    serializer_class = AdvancePaymentSerializer
    permission_classes = [IsAuthenticated, IsAdminOnly]  # Admin only for advances

    def get_queryset(self):
        queryset = AdvancePayment.objects.select_related('staff__user', 'approved_by')
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            
        # Filter by staff
        staff_id = self.request.query_params.get('staff')
        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)
            
        return queryset.order_by('-advance_date')

    def perform_create(self, serializer):
        serializer.save(approved_by=self.request.user)

    @action(detail=True, methods=['post'])
    def adjust_advance(self, request, pk=None):
        """Adjust advance payment"""
        advance = self.get_object()
        adjustment_amount = request.data.get('adjustment_amount', 0)
        
        try:
            adjustment_amount = float(adjustment_amount)
            if adjustment_amount <= 0:
                return Response({'error': 'Adjustment amount must be positive'}, 
                              status=status.HTTP_400_BAD_REQUEST)
            
            # Check if adjustment exceeds remaining amount
            if adjustment_amount > advance.remaining_amount:
                return Response({'error': 'Adjustment exceeds remaining advance amount'}, 
                              status=status.HTTP_400_BAD_REQUEST)
            
            advance.total_adjusted += adjustment_amount
            
            # Update status if fully adjusted
            if advance.total_adjusted >= advance.amount:
                advance.status = 'adjusted'
            else:
                advance.status = 'adjusting'
            
            advance.save()
            
            return Response({
                'message': 'Advance adjusted successfully',
                'remaining_amount': float(advance.remaining_amount),
                'total_adjusted': float(advance.total_adjusted),
                'status': advance.status
            })
            
        except (ValueError, TypeError):
            return Response({'error': 'Invalid adjustment amount'}, 
                          status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get advance payments summary"""
        queryset = self.get_queryset()
        
        total_advances = queryset.count()
        total_amount = queryset.aggregate(total=Sum('amount'))['total'] or 0
        pending_amount = queryset.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0
        adjusted_amount = queryset.filter(status='adjusted').aggregate(total=Sum('amount'))['total'] or 0
        
        return Response({
            'total_advances': total_advances,
            'total_amount': float(total_amount),
            'pending_amount': float(pending_amount),
            'adjusted_amount': float(adjusted_amount)
        })
