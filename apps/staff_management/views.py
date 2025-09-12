from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count, Q
from datetime import datetime, date
from calendar import monthrange

from .models import Employee, Designation, Attendance, MonthlyPayment
from .serializers import (
    EmployeeSerializer, DesignationSerializer, 
    AttendanceSerializer, EmployeeDetailSerializer,
    MonthlyPaymentSerializer
)
from apps.users.permissions import IsAdminOnly

class DesignationViewSet(viewsets.ModelViewSet):
    queryset = Designation.objects.all()
    serializer_class = DesignationSerializer
    permission_classes = [IsAuthenticated, IsAdminOnly]

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.select_related('designation').all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated, IsAdminOnly]
    
    @action(detail=True, methods=['get'])
    def detail_stats(self, request, pk=None):
        employee = self.get_object()
        serializer = EmployeeDetailSerializer(employee)
        return Response(serializer.data)

class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.select_related('employee', 'employee__designation').all()
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated, IsAdminOnly]
    
    def perform_create(self, serializer):
        serializer.save(marked_by=self.request.user)

class MonthlyPaymentViewSet(viewsets.ModelViewSet):
    queryset = MonthlyPayment.objects.select_related('employee', 'employee__designation').all()
    serializer_class = MonthlyPaymentSerializer
    permission_classes = [IsAuthenticated, IsAdminOnly]
    
    def perform_create(self, serializer):
        serializer.save(paid_by=self.request.user)

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOnly])
def attendance_sheet(request):
    """Get attendance for a specific date"""
    date_str = request.GET.get('date', str(date.today()))
    try:
        attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
    
    employees = Employee.objects.filter(is_active=True).select_related('designation')
    attendance_data = []
    
    for employee in employees:
        try:
            attendance = Attendance.objects.get(employee=employee, date=attendance_date)
            is_present = attendance.is_present
            remarks = attendance.remarks or ''
        except Attendance.DoesNotExist:
            is_present = False
            remarks = ''
        
        attendance_data.append({
            'employee_id': employee.id,
            'employee_name': employee.name,
            'designation': employee.designation.name,
            'monthly_salary': float(employee.monthly_salary),
            'daily_wage': float(employee.get_effective_daily_wage()),
            'is_present': is_present,
            'remarks': remarks
        })
    
    return Response({
        'date': attendance_date,
        'attendance': attendance_data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminOnly])
def mark_attendance(request):
    """Mark attendance for multiple employees"""
    date_str = request.data.get('date')
    attendance_data = request.data.get('attendance', [])
    
    if not date_str:
        return Response({'error': 'Date is required'}, status=400)
    
    try:
        attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
    
    for item in attendance_data:
        employee_id = item.get('employee_id')
        is_present = item.get('is_present', False)
        remarks = item.get('remarks', '')
        
        if employee_id:
            employee = get_object_or_404(Employee, id=employee_id)
            attendance, created = Attendance.objects.update_or_create(
                employee=employee,
                date=attendance_date,
                defaults={
                    'is_present': is_present,
                    'remarks': remarks,
                    'marked_by': request.user
                }
            )
    
    return Response({'message': 'Attendance marked successfully'})

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOnly])
def payroll_summary(request):
    """Get payroll summary with various filters"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    month = request.GET.get('month')
    year = request.GET.get('year')
    
    current_date = datetime.now()
    current_year = current_date.year
    current_month = current_date.month
    
    # Default to current month if no filters provided
    if not any([start_date, end_date, month, year]):
        year = current_year
        month = current_month
    
    summary_data = {
        'total_employees': Employee.objects.filter(is_active=True).count(),
        'designations': [],
        'monthly_summary': {},
        'total_paid': {
            'current_month_attendance': 0,
            'current_month_salary': 0,
            'till_date': 0
        }
    }
    
    # Get designation-wise summary
    designations = Designation.objects.all()
    for designation in designations:
        employees = Employee.objects.filter(designation=designation, is_active=True)
        
        if month and year:
            # Monthly calculation by attendance
            monthly_pay_attendance = 0
            monthly_salary_total = 0
            for employee in employees:
                monthly_pay_attendance += float(employee.get_monthly_pay_by_attendance(int(year), int(month)))
                monthly_salary_total += float(employee.monthly_salary)
            
            # Till date calculation (total paid via MonthlyPayment records)
            till_date_paid = MonthlyPayment.objects.filter(
                employee__designation=designation,
                employee__is_active=True
            ).aggregate(total=Sum('total_paid'))['total'] or 0
            
            # If no payment records, use attendance-based calculation
            if till_date_paid == 0:
                for employee in employees:
                    till_date_paid += float(employee.get_total_pay())
        
        elif start_date and end_date:
            # Custom range calculation
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                range_pay = 0
                for employee in employees:
                    attendance_count = Attendance.objects.filter(
                        employee=employee,
                        date__range=[start_dt, end_dt],
                        is_present=True
                    ).count()
                    range_pay += attendance_count * float(employee.get_effective_daily_wage())
                
                monthly_pay_attendance = range_pay
                monthly_salary_total = 0
                till_date_paid = 0
                
            except ValueError:
                return Response({'error': 'Invalid date format'}, status=400)
        else:
            monthly_pay_attendance = 0
            monthly_salary_total = 0
            till_date_paid = 0
        
        summary_data['designations'].append({
            'name': designation.name,
            'employee_count': employees.count(),
            'designation_daily_wage': float(designation.daily_wage),
            'designation_monthly_salary': float(designation.monthly_salary),
            'monthly_total_by_attendance': monthly_pay_attendance,
            'monthly_total_by_salary': monthly_salary_total,
            'till_date_total': float(till_date_paid)
        })
    
    # Calculate overall totals
    if month and year:
        # Current month totals
        current_month_attendance_total = 0
        current_month_salary_total = 0
        all_employees = Employee.objects.filter(is_active=True)
        
        for employee in all_employees:
            current_month_attendance_total += float(employee.get_monthly_pay_by_attendance(current_year, current_month))
            current_month_salary_total += float(employee.monthly_salary)
        
        # Till date total from payment records
        till_date_total = MonthlyPayment.objects.filter(
            employee__is_active=True
        ).aggregate(total=Sum('total_paid'))['total'] or 0
        
        # If no payment records, use attendance-based calculation
        if till_date_total == 0:
            for employee in all_employees:
                till_date_total += float(employee.get_total_pay())
        
        summary_data['total_paid']['current_month_attendance'] = current_month_attendance_total
        summary_data['total_paid']['current_month_salary'] = current_month_salary_total
        summary_data['total_paid']['till_date'] = float(till_date_total)
    
    return Response(summary_data)

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOnly])
def employee_attendance_history(request, employee_id):
    """Get attendance history for a specific employee"""
    employee = get_object_or_404(Employee, id=employee_id)
    
    current_date = datetime.now()
    month = request.GET.get('month', current_date.month)
    year = request.GET.get('year', current_date.year)
    
    try:
        month = int(month)
        year = int(year)
    except (ValueError, TypeError):
        return Response({'error': 'Invalid month or year'}, status=400)
    
    # Get attendance records for the month
    attendance_records = Attendance.objects.filter(
        employee=employee,
        date__year=year,
        date__month=month
    ).order_by('date')
    
    # Calculate monthly stats
    present_days = employee.get_monthly_present(year, month)
    absent_days = employee.get_monthly_absent(year, month)
    monthly_pay_attendance = float(employee.get_monthly_pay_by_attendance(year, month))
    monthly_salary = float(employee.monthly_salary)
    total_pay = float(employee.get_total_pay())
    
    # Get payment record if exists
    try:
        payment_record = MonthlyPayment.objects.get(
            employee=employee,
            year=year,
            month=month
        )
        payment_data = MonthlyPaymentSerializer(payment_record).data
    except MonthlyPayment.DoesNotExist:
        payment_data = None
    
    return Response({
        'employee': EmployeeSerializer(employee).data,
        'month': month,
        'year': year,
        'attendance_records': AttendanceSerializer(attendance_records, many=True).data,
        'stats': {
            'present_days': present_days,
            'absent_days': absent_days,
            'monthly_pay_by_attendance': monthly_pay_attendance,
            'fixed_monthly_salary': monthly_salary,
            'total_pay': total_pay
        },
        'payment_record': payment_data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminOnly])
def record_monthly_payment(request):
    """Record monthly payment for an employee"""
    employee_id = request.data.get('employee_id')
    year = request.data.get('year')
    month = request.data.get('month')
    base_salary = request.data.get('base_salary')
    attendance_bonus = request.data.get('attendance_bonus', 0)
    deductions = request.data.get('deductions', 0)
    total_paid = request.data.get('total_paid')
    payment_date = request.data.get('payment_date')
    remarks = request.data.get('remarks', '')
    
    if not all([employee_id, year, month, base_salary, total_paid, payment_date]):
        return Response({'error': 'Missing required fields'}, status=400)
    
    try:
        employee = Employee.objects.get(id=employee_id)
        
        # Calculate present days for the month
        present_days = employee.get_monthly_present(int(year), int(month))
        
        # Get total working days in month (can be customized)
        working_days = monthrange(int(year), int(month))[1]
        
        payment, created = MonthlyPayment.objects.update_or_create(
            employee=employee,
            year=int(year),
            month=int(month),
            defaults={
                'base_salary': base_salary,
                'attendance_bonus': attendance_bonus,
                'deductions': deductions,
                'total_paid': total_paid,
                'payment_date': payment_date,
                'present_days': present_days,
                'working_days': working_days,
                'remarks': remarks,
                'paid_by': request.user
            }
        )
        
        return Response({
            'message': 'Payment recorded successfully',
            'payment_id': payment.id,
            'created': created
        })
        
    except Employee.DoesNotExist:
        return Response({'error': 'Employee not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=400)

