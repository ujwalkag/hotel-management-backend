from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum, Count, Q, Avg
from datetime import datetime, timedelta
from .models import StaffDepartment, StaffEmployee, StaffAttendance, StaffPayroll, StaffAdvancePayment
from .serializers import (
    StaffDepartmentSerializer, StaffEmployeeListSerializer, StaffEmployeeDetailSerializer,
    StaffAttendanceSerializer, MobileAttendanceSerializer, StaffPayrollSerializer,
    StaffAdvancePaymentSerializer
)

class StaffDepartmentViewSet(viewsets.ModelViewSet):
    queryset = StaffDepartment.objects.all()
    serializer_class = StaffDepartmentSerializer
    permission_classes = [IsAuthenticated]

class StaffEmployeeViewSet(viewsets.ModelViewSet):
    queryset = StaffEmployee.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return StaffEmployeeListSerializer
        return StaffEmployeeDetailSerializer
    
    def get_queryset(self):
        queryset = StaffEmployee.objects.select_related('department', 'system_user')
        
        # Filter by department
        department = self.request.query_params.get('department', None)
        if department:
            queryset = queryset.filter(department_id=department)
            
        # Filter by status
        status = self.request.query_params.get('status', None)
        if status:
            queryset = queryset.filter(employment_status=status)
            
        # Search by name
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search) |
                Q(employee_id__icontains=search) |
                Q(phone__icontains=search)
            )
            
        return queryset.order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get dashboard statistics"""
        today = timezone.now().date()
        
        total_employees = StaffEmployee.objects.filter(is_active=True).count()
        active_employees = StaffEmployee.objects.filter(employment_status='active').count()
        
        # Today's attendance
        today_attendance = StaffAttendance.objects.filter(date=today)
        present_today = today_attendance.filter(status='present').count()
        on_leave = today_attendance.filter(status='leave').count()
        
        # Pending advance payments
        pending_advances = StaffAdvancePayment.objects.filter(status='pending').count()
        
        # This month's payroll
        current_month = timezone.now().month
        current_year = timezone.now().year
        payrolls_processed = StaffPayroll.objects.filter(
            month=current_month, year=current_year, status='paid'
        ).count()
        
        return Response({
            'total_employees': total_employees,
            'active_employees': active_employees,
            'present_today': present_today,
            'on_leave': on_leave,
            'absent_today': max(0, active_employees - present_today - on_leave),
            'pending_advances': pending_advances,
            'payrolls_processed': payrolls_processed,
            'date': today.strftime('%Y-%m-%d')
        })
        
    @action(detail=False, methods=['get'])
    def salary_report(self, request):
        """Get salary statistics by department"""
        departments = StaffDepartment.objects.annotate(
            total_employees=Count('staffemployee', filter=Q(staffemployee__is_active=True)),
            average_salary=Avg('staffemployee__base_salary', filter=Q(staffemployee__is_active=True)),
            total_salary_expense=Sum('staffemployee__base_salary', filter=Q(staffemployee__is_active=True))
        ).filter(is_active=True)
        
        report_data = []
        for dept in departments:
            report_data.append({
                'department_name': dept.name,
                'total_employees': dept.total_employees or 0,
                'average_salary': round(dept.average_salary or 0, 2),
                'total_salary_expense': round(dept.total_salary_expense or 0, 2)
            })
        
        return Response(report_data)

class StaffAttendanceViewSet(viewsets.ModelViewSet):
    queryset = StaffAttendance.objects.all()
    serializer_class = StaffAttendanceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = StaffAttendance.objects.select_related('employee', 'approved_by')
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
            
        # Filter by employee
        employee = self.request.query_params.get('employee', None)
        if employee:
            queryset = queryset.filter(employee_id=employee)
            
        return queryset.order_by('-date', 'employee__full_name')
    
    @action(detail=False, methods=['post'])
    def mobile_checkin(self, request):
        """Mobile check-in/check-out endpoint"""
        serializer = MobileAttendanceSerializer(data=request.data)
        if serializer.is_valid():
            employee_id = serializer.validated_data.get('employee_id')
            location = serializer.validated_data.get('location', '')
            device_info = serializer.validated_data.get('device_info', {})
            action = serializer.validated_data.get('action', 'check_in')
            
            try:
                employee = StaffEmployee.objects.get(employee_id=employee_id, is_active=True)
                today = timezone.now().date()
                current_time = timezone.now().time()
                
                attendance, created = StaffAttendance.objects.get_or_create(
                    employee=employee,
                    date=today,
                    defaults={
                        'status': 'present',
                        'ip_address': request.META.get('REMOTE_ADDR'),
                        'device_info': device_info
                    }
                )
                
                if action == 'check_in':
                    if attendance.check_in_time:
                        return Response({
                            'success': False,
                            'message': 'Already checked in today',
                            'check_in_time': attendance.check_in_time.strftime('%H:%M')
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    attendance.check_in_time = current_time
                    attendance.check_in_location = location
                    attendance.save()
                    
                    return Response({
                        'success': True,
                        'message': f'Checked in successfully at {current_time.strftime("%H:%M")}',
                        'employee_name': employee.full_name,
                        'check_in_time': current_time.strftime('%H:%M'),
                        'location': location
                    })
                    
                elif action == 'check_out':
                    if not attendance.check_in_time:
                        return Response({
                            'success': False,
                            'message': 'Must check in first'
                        }, status=status.HTTP_400_BAD_REQUEST)
                        
                    if attendance.check_out_time:
                        return Response({
                            'success': False,
                            'message': 'Already checked out today',
                            'check_out_time': attendance.check_out_time.strftime('%H:%M')
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    attendance.check_out_time = current_time
                    attendance.check_out_location = location
                    attendance.save()
                    
                    # Calculate hours
                    attendance.calculate_hours()
                    
                    return Response({
                        'success': True,
                        'message': f'Checked out successfully at {current_time.strftime("%H:%M")}',
                        'employee_name': employee.full_name,
                        'check_out_time': current_time.strftime('%H:%M'),
                        'total_hours': float(attendance.total_hours),
                        'location': location
                    })
                
            except StaffEmployee.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Employee not found or inactive'
                }, status=status.HTTP_404_NOT_FOUND)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def today_summary(self, request):
        """Get today's attendance summary"""
        today = timezone.now().date()
        attendance_records = StaffAttendance.objects.filter(date=today).select_related('employee')
        
        summary = {
            'date': today.strftime('%Y-%m-%d'),
            'total_employees': StaffEmployee.objects.filter(is_active=True).count(),
            'present': attendance_records.filter(status='present').count(),
            'absent': 0,  # Will calculate
            'on_leave': attendance_records.filter(status='leave').count(),
            'late': attendance_records.filter(status='late').count(),
            'records': []
        }
        
        summary['absent'] = summary['total_employees'] - summary['present'] - summary['on_leave']
        
        for record in attendance_records:
            summary['records'].append({
                'employee_id': record.employee.employee_id,
                'employee_name': record.employee.full_name,
                'status': record.status,
                'check_in_time': record.check_in_time.strftime('%H:%M') if record.check_in_time else None,
                'check_out_time': record.check_out_time.strftime('%H:%M') if record.check_out_time else None,
                'total_hours': float(record.total_hours)
            })
        
        return Response(summary)

class StaffPayrollViewSet(viewsets.ModelViewSet):
    queryset = StaffPayroll.objects.all()
    serializer_class = StaffPayrollSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = StaffPayroll.objects.select_related('employee', 'calculated_by', 'approved_by')
        
        # Filter by month/year
        month = self.request.query_params.get('month', None)
        year = self.request.query_params.get('year', None)
        
        if month:
            queryset = queryset.filter(month=month)
        if year:
            queryset = queryset.filter(year=year)
            
        # Filter by status
        payroll_status = self.request.query_params.get('status', None)
        if payroll_status:
            queryset = queryset.filter(status=payroll_status)
            
        return queryset.order_by('-year', '-month', 'employee__full_name')
    
    @action(detail=True, methods=['post'])
    def calculate(self, request, pk=None):
        """Calculate payroll for an employee"""
        payroll = self.get_object()
        
        if payroll.status != 'draft':
            return Response({
                'success': False,
                'message': 'Payroll can only be calculated in draft status'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        payroll.calculated_by = request.user
        payroll.calculate_payroll()
        
        return Response({
            'success': True,
            'message': 'Payroll calculated successfully',
            'payroll': StaffPayrollSerializer(payroll).data
        })
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve calculated payroll"""
        payroll = self.get_object()
        
        if payroll.status != 'calculated':
            return Response({
                'success': False,
                'message': 'Payroll must be calculated before approval'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        payroll.status = 'approved'
        payroll.approved_by = request.user
        payroll.approval_date = timezone.now()
        payroll.save()
        
        return Response({
            'success': True,
            'message': 'Payroll approved successfully'
        })
    
    @action(detail=False, methods=['post'])
    def bulk_generate(self, request):
        """Generate payroll for all employees for a month"""
        month = request.data.get('month')
        year = request.data.get('year')
        
        if not month or not year:
            return Response({
                'success': False,
                'message': 'Month and year are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get pay period dates (1st to last day of month)
        try:
            start_date = datetime(int(year), int(month), 1).date()
            if int(month) == 12:
                end_date = datetime(int(year) + 1, 1, 1).date() - timedelta(days=1)
            else:
                end_date = datetime(int(year), int(month) + 1, 1).date() - timedelta(days=1)
        except ValueError:
            return Response({
                'success': False,
                'message': 'Invalid month or year'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get active employees
        employees = StaffEmployee.objects.filter(is_active=True, employment_status='active')
        created_count = 0
        
        for employee in employees:
            payroll, created = StaffPayroll.objects.get_or_create(
                employee=employee,
                month=int(month),
                year=int(year),
                defaults={
                    'pay_period_start': start_date,
                    'pay_period_end': end_date,
                    'created_by': request.user
                }
            )
            if created:
                created_count += 1
        
        return Response({
            'success': True,
            'message': f'Generated {created_count} payroll records',
            'total_employees': employees.count(),
            'created_count': created_count
        })

class StaffAdvancePaymentViewSet(viewsets.ModelViewSet):
    queryset = StaffAdvancePayment.objects.all()
    serializer_class = StaffAdvancePaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = StaffAdvancePayment.objects.select_related('employee', 'approved_by', 'disbursed_by')
        
        # Filter by status
        advance_status = self.request.query_params.get('status', None)
        if advance_status:
            queryset = queryset.filter(status=advance_status)
            
        # Filter by employee
        employee = self.request.query_params.get('employee', None)
        if employee:
            queryset = queryset.filter(employee_id=employee)
            
        return queryset.order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve advance payment request"""
        advance = self.get_object()
        notes = request.data.get('notes', '')
        
        if advance.approve_advance(request.user, notes):
            return Response({
                'success': True,
                'message': 'Advance payment approved successfully'
            })
        else:
            return Response({
                'success': False,
                'message': 'Cannot approve this advance payment'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def disburse(self, request, pk=None):
        """Disburse approved advance payment"""
        advance = self.get_object()
        method = request.data.get('method', 'bank_transfer')
        
        if advance.disburse_advance(request.user, method):
            return Response({
                'success': True,
                'message': 'Advance payment disbursed successfully'
            })
        else:
            return Response({
                'success': False,
                'message': 'Cannot disburse this advance payment'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def pending_summary(self, request):
        """Get summary of pending advance payments"""
        pending = StaffAdvancePayment.objects.filter(status='pending')
        
        summary = {
            'total_count': pending.count(),
            'total_amount': pending.aggregate(total=Sum('amount'))['total'] or 0,
            'urgent_count': pending.filter(urgency_level='urgent').count(),
            'high_priority_count': pending.filter(urgency_level='high').count()
        }
        
        return Response(summary)

