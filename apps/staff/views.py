from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum, Avg
from datetime import datetime, date, timedelta
from .models import StaffProfile, Attendance, Payroll
from .serializers import StaffProfileSerializer, AttendanceSerializer, PayrollSerializer
from apps.users.models import CustomUser

class StaffProfileViewSet(viewsets.ModelViewSet):
    """FIXED - Complete Staff Profile Management ViewSet"""
    queryset = StaffProfile.objects.all()
    serializer_class = StaffProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = StaffProfile.objects.all()
        department = self.request.query_params.get('department')
        is_active = self.request.query_params.get('is_active')
        
        if department:
            queryset = queryset.filter(department=department)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
            
        return queryset.order_by('-created_at')
    
    @action(detail=True, methods=['get'])
    def attendance_summary(self, request, pk=None):
        """Get attendance summary for staff member"""
        staff = self.get_object()
        month = request.query_params.get('month', datetime.now().month)
        year = request.query_params.get('year', datetime.now().year)
        
        attendances = Attendance.objects.filter(
            staff=staff,
            date__month=month,
            date__year=year
        )
        
        summary = {
            'staff_id': staff.id,
            'staff_name': staff.name,
            'month': month,
            'year': year,
            'total_days': attendances.count(),
            'present_days': attendances.filter(status='present').count(),
            'absent_days': attendances.filter(status='absent').count(),
            'late_days': attendances.filter(status='late').count(),
            'total_hours': sum([att.total_hours for att in attendances if att.total_hours]),
            'overtime_hours': sum([att.overtime_hours for att in attendances if att.overtime_hours]),
        }
        
        return Response(summary)
    
    @action(detail=True, methods=['get'])
    def payroll_history(self, request, pk=None):
        """Get payroll history for staff member"""
        staff = self.get_object()
        payrolls = Payroll.objects.filter(staff=staff).order_by('-year', '-month')[:12]
        serializer = PayrollSerializer(payrolls, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def department_stats(self, request):
        """Get staff statistics by department"""
        from django.db.models import Count
        
        stats = StaffProfile.objects.values('department').annotate(
            total=Count('id'),
            active=Count('id', filter=Q(is_active=True))
        ).order_by('department')
        
        return Response(list(stats))

class AttendanceViewSet(viewsets.ModelViewSet):
    """Attendance Management ViewSet"""
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Attendance.objects.all()
        staff_id = self.request.query_params.get('staff_id')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
            
        return queryset.order_by('-date')
    
    @action(detail=False, methods=['post'])
    def mark_attendance(self, request):
        """Quick attendance marking for mobile interface"""
        staff_id = request.data.get('staff_id')
        action_type = request.data.get('action')  # 'check_in' or 'check_out'
        
        if not staff_id or not action_type:
            return Response(
                {'error': 'staff_id and action are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            staff = StaffProfile.objects.get(id=staff_id)
        except StaffProfile.DoesNotExist:
            return Response(
                {'error': 'Staff not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        today = datetime.now().date()
        current_time = datetime.now().time()
        
        attendance, created = Attendance.objects.get_or_create(
            staff=staff,
            date=today,
            defaults={'status': 'present'}
        )
        
        if action_type == 'check_in':
            attendance.check_in = current_time
            attendance.status = 'present'
        elif action_type == 'check_out':
            attendance.check_out = current_time
            attendance.calculate_hours()
        
        attendance.save()
        serializer = AttendanceSerializer(attendance)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def today_report(self, request):
        """Get today's attendance report"""
        today = date.today()
        attendances = Attendance.objects.filter(date=today)
        
        report = {
            'date': today,
            'total_staff': StaffProfile.objects.filter(is_active=True).count(),
            'checked_in': attendances.filter(check_in__isnull=False).count(),
            'present': attendances.filter(status='present').count(),
            'absent': attendances.filter(status='absent').count(),
            'late': attendances.filter(status='late').count(),
            'attendances': AttendanceSerializer(attendances, many=True).data
        }
        
        return Response(report)

class PayrollViewSet(viewsets.ModelViewSet):
    """Payroll Management ViewSet"""
    queryset = Payroll.objects.all()
    serializer_class = PayrollSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Payroll.objects.all()
        staff_id = self.request.query_params.get('staff_id')
        month = self.request.query_params.get('month')
        year = self.request.query_params.get('year')
        
        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)
        if month:
            queryset = queryset.filter(month=month)
        if year:
            queryset = queryset.filter(year=year)
            
        return queryset.order_by('-year', '-month')
    
    @action(detail=False, methods=['post'])
    def generate_monthly_payroll(self, request):
        """Generate payroll for all active staff for given month"""
        month = request.data.get('month', datetime.now().month)
        year = request.data.get('year', datetime.now().year)
        
        staff_members = StaffProfile.objects.filter(is_active=True)
        generated_payrolls = []
        
        for staff in staff_members:
            payroll, created = Payroll.objects.get_or_create(
                staff=staff,
                month=month,
                year=year,
                defaults={
                    'basic_amount': staff.basic_salary,
                    'net_amount': staff.basic_salary
                }
            )
            
            if created or not payroll.is_paid:
                payroll.calculate_payroll()
                generated_payrolls.append(payroll)
        
        serializer = PayrollSerializer(generated_payrolls, many=True)
        return Response({
            'message': f'Generated payroll for {len(generated_payrolls)} staff members',
            'payrolls': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """Mark payroll as paid"""
        payroll = self.get_object()
        payroll.is_paid = True
        payroll.payment_date = datetime.now().date()
        payroll.save()
        
        serializer = PayrollSerializer(payroll)
        return Response(serializer.data)
