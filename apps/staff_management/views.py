from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count, Q
from datetime import datetime, date, timedelta
from calendar import monthrange

from .models import Employee, Designation, Attendance, MonthlyPayment
from .serializers import (
    EmployeeSerializer, DesignationSerializer, 
    AttendanceSerializer, EmployeeDetailSerializer,
    MonthlyPaymentSerializer, AttendanceWithPaymentSerializer
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
        """Enhanced employee details with custom time interval support"""
        employee = self.get_object()

        # Get query parameters for custom date range
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        year = request.GET.get('year')
        month = request.GET.get('month')

        # Prepare date range
        if start_date and end_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
        elif year and month:
            try:
                year = int(year)
                month = int(month)
                start_dt = date(year, month, 1)
                end_dt = date(year, month, monthrange(year, month)[1])
            except (ValueError, TypeError):
                return Response({'error': 'Invalid year or month'}, status=400)
        else:
            # Current month by default
            current_date = datetime.now()
            start_dt = date(current_date.year, current_date.month, 1)
            end_dt = date(current_date.year, current_date.month, monthrange(current_date.year, current_date.month)[1])

        # Get attendance statistics for the period
        attendance_stats = employee.get_attendance_stats(start_dt, end_dt)

        # Get attendance records for the period
        attendance_records = Attendance.objects.filter(
            employee=employee,
            date__range=[start_dt, end_dt]
        ).order_by('date')

        # Prepare response data
        response_data = {
            'employee': {
                'id': employee.id,
                'name': employee.name,
                'address': employee.address,
                'aadhar_number': employee.aadhar_number,
                'phone': employee.phone,
                'designation_name': employee.designation.name,
                'monthly_salary': float(employee.monthly_salary),
                'daily_wage': float(employee.get_effective_daily_wage()),
                'date_of_joining': employee.date_of_joining,
                'is_active': employee.is_active
            },
            'period': {
                'start_date': start_dt,
                'end_date': end_dt,
                'total_days': (end_dt - start_dt).days + 1
            },
            'attendance_summary': {
                'total_present': attendance_stats['total_present'],
                'total_absent': attendance_stats['total_absent'],
                'total_paid_days': attendance_stats['total_paid_days'],
                'total_pay': float(attendance_stats['total_pay']),
                'attendance_percentage': round((attendance_stats['total_present'] / ((end_dt - start_dt).days + 1)) * 100, 2) if (end_dt - start_dt).days + 1 > 0 else 0
            },
            'monthly_stats': self._get_monthly_yearly_stats(employee),
            'attendance_records': AttendanceWithPaymentSerializer(attendance_records, many=True).data,
            'recent_payments': self._get_recent_payments(employee)
        }

        return Response(response_data)

    def _get_monthly_yearly_stats(self, employee):
        """Get current month and year statistics"""
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month

        # Current month stats
        monthly_present = employee.get_monthly_present(current_year, current_month)
        monthly_absent = employee.get_monthly_absent(current_year, current_month)
        monthly_paid_days = employee.get_monthly_paid_days(current_year, current_month)
        monthly_pay = float(employee.get_monthly_pay_by_attendance(current_year, current_month))

        # Yearly stats
        yearly_stats = employee.get_attendance_stats(
            start_date=date(current_year, 1, 1),
            end_date=date(current_year, 12, 31)
        )

        return {
            'current_month': {
                'month': current_month,
                'year': current_year,
                'present_days': monthly_present,
                'absent_days': monthly_absent,
                'paid_days': monthly_paid_days,
                'total_pay': monthly_pay
            },
            'current_year': {
                'year': current_year,
                'total_present': yearly_stats['total_present'],
                'total_absent': yearly_stats['total_absent'],
                'total_paid_days': yearly_stats['total_paid_days'],
                'total_pay': float(yearly_stats['total_pay'])
            }
        }

    def _get_recent_payments(self, employee):
        """Get recent payment records"""
        payments = MonthlyPayment.objects.filter(employee=employee).order_by('-year', '-month')[:6]
        return MonthlyPaymentSerializer(payments, many=True).data

class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.select_related('employee', 'employee__designation').all()
    serializer_class = AttendanceWithPaymentSerializer
    permission_classes = [IsAuthenticated, IsAdminOnly]

    def perform_create(self, serializer):
        # Set _include_payment_explicitly_set flag if include_payment is provided
        if 'include_payment' in self.request.data:
            instance = serializer.save(marked_by=self.request.user)
            instance._include_payment_explicitly_set = True
            instance.save()
        else:
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
    """Get attendance for a specific date with payment control"""
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
            include_payment = attendance.include_payment
            remarks = attendance.remarks or ''
        except Attendance.DoesNotExist:
            is_present = False
            include_payment = True  # Default to include payment
            remarks = ''

        attendance_data.append({
            'employee_id': employee.id,
            'employee_name': employee.name,
            'designation': employee.designation.name,
            'monthly_salary': float(employee.monthly_salary),
            'daily_wage': float(employee.get_effective_daily_wage()),
            'is_present': is_present,
            'include_payment': include_payment,
            'remarks': remarks
        })

    return Response({
        'date': attendance_date,
        'attendance': attendance_data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminOnly])
def mark_attendance(request):
    """Mark attendance for multiple employees with payment control"""
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
        include_payment = item.get('include_payment', is_present)  # Default to match presence
        remarks = item.get('remarks', '')

        if employee_id:
            employee = get_object_or_404(Employee, id=employee_id)
            attendance, created = Attendance.objects.update_or_create(
                employee=employee,
                date=attendance_date,
                defaults={
                    'is_present': is_present,
                    'include_payment': include_payment,
                    'remarks': remarks,
                    'marked_by': request.user
                }
            )
            # Set the flag to indicate include_payment was explicitly set
            attendance._include_payment_explicitly_set = True
            attendance.save()

    return Response({'message': 'Attendance marked successfully'})

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOnly])
def payroll_summary(request):
    """Get enhanced payroll summary with custom time intervals"""
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
        'period_summary': {},
        'total_paid': {
            'current_month_attendance': 0,
            'current_month_salary': 0,
            'custom_period': 0,
            'till_date': 0
        }
    }

    # Get designation-wise summary
    designations = Designation.objects.all()
    for designation in designations:
        employees = Employee.objects.filter(designation=designation, is_active=True)

        if start_date and end_date:
            # Custom range calculation
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

                custom_period_pay = 0
                for employee in employees:
                    stats = employee.get_attendance_stats(start_dt, end_dt)
                    custom_period_pay += float(stats['total_pay'])

                period_summary = {
                    'start_date': start_dt,
                    'end_date': end_dt,
                    'total_pay': custom_period_pay
                }

            except ValueError:
                return Response({'error': 'Invalid date format'}, status=400)

        elif month and year:
            # Monthly calculation by attendance with payment control
            monthly_pay_attendance = 0
            monthly_salary_total = 0
            for employee in employees:
                monthly_pay_attendance += float(employee.get_monthly_pay_by_attendance(int(year), int(month)))
                monthly_salary_total += float(employee.monthly_salary)

            period_summary = {
                'year': int(year),
                'month': int(month),
                'attendance_based_pay': monthly_pay_attendance,
                'salary_based_pay': monthly_salary_total
            }
        else:
            monthly_pay_attendance = 0
            monthly_salary_total = 0
            period_summary = {}

        # Till date calculation (total paid via MonthlyPayment records or attendance)
        till_date_paid = MonthlyPayment.objects.filter(
            employee__designation=designation,
            employee__is_active=True
        ).aggregate(total=Sum('total_paid'))['total'] or 0

        # If no payment records, use attendance-based calculation
        if till_date_paid == 0:
            for employee in employees:
                till_date_paid += float(employee.get_total_pay())

        summary_data['designations'].append({
            'name': designation.name,
            'employee_count': employees.count(),
            'designation_daily_wage': float(designation.daily_wage),
            'designation_monthly_salary': float(designation.monthly_salary),
            'period_total': monthly_pay_attendance if month and year else (custom_period_pay if start_date and end_date else 0),
            'till_date_total': float(till_date_paid)
        })

    summary_data['period_summary'] = period_summary

    # Calculate overall totals
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
    summary_data['total_paid']['custom_period'] = custom_period_pay if start_date and end_date else monthly_pay_attendance
    summary_data['total_paid']['till_date'] = float(till_date_total)

    return Response(summary_data)

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOnly])
def employee_attendance_history(request, employee_id):
    """Get comprehensive attendance history for a specific employee"""
    employee = get_object_or_404(Employee, id=employee_id)

    current_date = datetime.now()
    month = request.GET.get('month', current_date.month)
    year = request.GET.get('year', current_date.year)
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date and end_date:
        # Custom date range
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
            attendance_records = Attendance.objects.filter(
                employee=employee,
                date__range=[start_dt, end_dt]
            ).order_by('date')
            stats = employee.get_attendance_stats(start_dt, end_dt)
        except ValueError:
            return Response({'error': 'Invalid date format'}, status=400)
    else:
        # Monthly data
        try:
            month = int(month)
            year = int(year)
            attendance_records = Attendance.objects.filter(
                employee=employee,
                date__year=year,
                date__month=month
            ).order_by('date')
            start_dt = date(year, month, 1)
            end_dt = date(year, month, monthrange(year, month)[1])
            stats = employee.get_attendance_stats(start_dt, end_dt)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid month or year'}, status=400)

    # Get payment record if exists
    if not start_date and not end_date:
        try:
            payment_record = MonthlyPayment.objects.get(
                employee=employee,
                year=year,
                month=month
            )
            payment_data = MonthlyPaymentSerializer(payment_record).data
        except MonthlyPayment.DoesNotExist:
            payment_data = None
    else:
        payment_data = None

    return Response({
        'employee': EmployeeSerializer(employee).data,
        'period': {
            'start_date': start_dt,
            'end_date': end_dt,
            'month': month if not (start_date and end_date) else None,
            'year': year if not (start_date and end_date) else None
        },
        'attendance_records': AttendanceWithPaymentSerializer(attendance_records, many=True).data,
        'stats': {
            'total_present': stats['total_present'],
            'total_absent': stats['total_absent'],
            'total_paid_days': stats['total_paid_days'],
            'total_pay': float(stats['total_pay']),
            'fixed_monthly_salary': float(employee.monthly_salary),
            'effective_daily_wage': float(employee.get_effective_daily_wage())
        },
        'payment_record': payment_data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminOnly])
def record_monthly_payment(request):
    """Record monthly payment for an employee with paid days tracking"""
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

        # Calculate present and paid days for the month
        present_days = employee.get_monthly_present(int(year), int(month))
        paid_days = employee.get_monthly_paid_days(int(year), int(month))

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
                'paid_days': paid_days,
                'working_days': working_days,
                'remarks': remarks,
                'paid_by': request.user
            }
        )

        return Response({
            'message': 'Payment recorded successfully',
            'payment_id': payment.id,
            'created': created,
            'present_days': present_days,
            'paid_days': paid_days
        })

    except Employee.DoesNotExist:
        return Response({'error': 'Employee not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=400)
