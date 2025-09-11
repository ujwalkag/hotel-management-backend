# apps/staff/views.py - COMPLETE UPDATED VERSION WITH ENHANCED DEBUGGING AND FIXES
from django.shortcuts import get_object_or_404
from datetime import date
import calendar
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum, Count, Q, Avg
from datetime import datetime, timedelta
import traceback
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

    def get_permissions(self):
        """Enhanced permission check with detailed logging"""
        try:
            # Check if request exists and user is authenticated
            if not hasattr(self, 'request') or not self.request:
                print("No request object found")
                return [IsAuthenticated()]

            user = self.request.user

            # If user is not authenticated, require authentication
            if not user or not user.is_authenticated:
                print("User not authenticated")
                return [IsAuthenticated()]

            # Enhanced logging
            print(f"Permission check for user: {user.email}")
            print(f"User authenticated: {user.is_authenticated}")
            print(f"User has role attr: {hasattr(user, 'role')}")
            if hasattr(user, 'role'):
                print(f"User role: {user.role}")

            # Check if user has role attribute
            if not hasattr(user, 'role'):
                print(f"User {user.email} has no role attribute")
                return [IsAuthenticated()]

            # Admin users bypass all permissions
            if user.role == 'admin':
                print(f"✅ Admin user {user.email} granted access")
                return []  # No permissions required

            # All other users need authentication
            print(f"Non-admin user {user.email} (role: {user.role}) requires authentication")
            return [IsAuthenticated()]

        except Exception as e:
            print(f"Permission check error: {str(e)}")
            print(f"Full traceback: {traceback.format_exc()}")
            return [IsAuthenticated()]


class StaffEmployeeViewSet(viewsets.ModelViewSet):
    queryset = StaffEmployee.objects.all()
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """Enhanced permission check with detailed logging"""
        try:
            # Check if request exists and user is authenticated
            if not hasattr(self, 'request') or not self.request:
                print("No request object found")
                return [IsAuthenticated()]

            user = self.request.user

            # If user is not authenticated, require authentication
            if not user or not user.is_authenticated:
                print("User not authenticated")
                return [IsAuthenticated()]

            # Enhanced logging
            print(f"Permission check for user: {user.email}")
            print(f"User authenticated: {user.is_authenticated}")
            print(f"User has role attr: {hasattr(user, 'role')}")
            if hasattr(user, 'role'):
                print(f"User role: {user.role}")

            # Check if user has role attribute
            if not hasattr(user, 'role'):
                print(f"User {user.email} has no role attribute")
                return [IsAuthenticated()]

            # Admin users bypass all permissions
            if user.role == 'admin':
                print(f"✅ Admin user {user.email} granted access")
                return []  # No permissions required

            # All other users need authentication
            print(f"Non-admin user {user.email} (role: {user.role}) requires authentication")
            return [IsAuthenticated()]

        except Exception as e:
            print(f"Permission check error: {str(e)}")
            print(f"Full traceback: {traceback.format_exc()}")
            return [IsAuthenticated()]

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
        status_param = self.request.query_params.get('status', None)
        if status_param:
            queryset = queryset.filter(employment_status=status_param)

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
        """Get dashboard statistics - ENHANCED WITH COMPREHENSIVE DEBUGGING"""
        try:
            print(f"🔍 Dashboard stats requested by: {request.user.email} (role: {getattr(request.user, 'role', 'NO_ROLE')})")
            print(f"🔍 User authenticated: {request.user.is_authenticated}")
            print(f"🔍 User active: {getattr(request.user, 'is_active', 'NO_ACTIVE_ATTR')}")
            print(f"🔍 User ID: {getattr(request.user, 'id', 'NO_ID')}")

            today = timezone.now().date()

            # Basic employee counts with error handling
            try:
                total_employees = StaffEmployee.objects.filter(is_active=True).count()
                active_employees = StaffEmployee.objects.filter(employment_status='active').count()
                print(f"📊 Employee counts - Total: {total_employees}, Active: {active_employees}")
            except Exception as e:
                print(f"❌ Employee count error: {str(e)}")
                total_employees = 0
                active_employees = 0

            # Today's attendance with error handling
            try:
                today_attendance = StaffAttendance.objects.filter(date=today)
                present_today = today_attendance.filter(status='present').count()
                on_leave = today_attendance.filter(status='leave').count()
                print(f"📊 Attendance - Present: {present_today}, On leave: {on_leave}")
            except Exception as e:
                print(f"❌ Attendance query error: {str(e)}")
                present_today = 0
                on_leave = 0

            # Pending advance payments with error handling
            try:
                pending_advances = StaffAdvancePayment.objects.filter(status='pending').count()
                print(f"📊 Pending advances: {pending_advances}")
            except Exception as e:
                print(f"❌ Advances query error: {str(e)}")
                pending_advances = 0

            # This month's payroll with error handling
            try:
                current_month = timezone.now().month
                current_year = timezone.now().year
                payrolls_processed = StaffPayroll.objects.filter(
                    month=current_month, year=current_year, status='paid'
                ).count()
                print(f"📊 Payrolls processed: {payrolls_processed}")
            except Exception as e:
                print(f"❌ Payroll query error: {str(e)}")
                payrolls_processed = 0

            response_data = {
                'total_employees': total_employees,
                'active_employees': active_employees,
                'present_today': present_today,
                'on_leave': on_leave,
                'absent_today': max(0, active_employees - present_today - on_leave),
                'pending_advances': pending_advances,
                'payrolls_processed': payrolls_processed,
                'date': today.strftime('%Y-%m-%d'),
                'debug_info': {
                    'user_email': request.user.email,
                    'user_role': getattr(request.user, 'role', 'unknown'),
                    'user_authenticated': request.user.is_authenticated,
                    'timestamp': timezone.now().isoformat()
                }
            }

            print(f"✅ Dashboard stats successful: {response_data}")
            return Response(response_data)

        except Exception as e:
            print(f"❌ Dashboard stats error: {str(e)}")
            print(f"❌ Full traceback: {traceback.format_exc()}")
            return Response({
                'error': 'Failed to load dashboard statistics',
                'detail': str(e),
                'total_employees': 0,
                'active_employees': 0,
                'present_today': 0,
                'on_leave': 0,
                'absent_today': 0,
                'pending_advances': 0,
                'payrolls_processed': 0,
                'date': timezone.now().date().strftime('%Y-%m-%d'),
                'debug_info': {
                    'user_authenticated': request.user.is_authenticated if hasattr(request, 'user') else False,
                    'user_id': request.user.id if hasattr(request, 'user') and request.user.is_authenticated else None,
                    'error_type': type(e).__name__,
                    'timestamp': timezone.now().isoformat()
                }
            }, status=200)  # Return 200 with error data instead of 500

    @action(detail=False, methods=['get'])
    def salary_report(self, request):
        """Get salary statistics by department - ENHANCED WITH COMPREHENSIVE DEBUGGING"""
        try:
            print(f"🔍 Salary report requested by: {request.user.email} (role: {getattr(request.user, 'role', 'NO_ROLE')})")

            # Use simpler approach to avoid complex annotation issues
            departments = StaffDepartment.objects.filter(is_active=True)
            report_data = []

            print(f"📊 Processing {departments.count()} departments")

            for dept in departments:
                try:
                    # Get employees for this department
                    dept_employees = StaffEmployee.objects.filter(
                        department=dept,
                        is_active=True
                    )

                    total_employees = dept_employees.count()
                    print(f"📊 Department {dept.name}: {total_employees} employees")

                    if total_employees > 0:
                        # Calculate salaries manually to avoid annotation issues
                        salaries = []
                        for emp in dept_employees:
                            if emp.base_salary:
                                salaries.append(float(emp.base_salary))

                        if salaries:
                            average_salary = sum(salaries) / len(salaries)
                            total_salary_expense = sum(salaries)
                        else:
                            average_salary = 0
                            total_salary_expense = 0
                    else:
                        average_salary = 0
                        total_salary_expense = 0

                    dept_data = {
                        'department_name': dept.name,
                        'total_employees': total_employees,
                        'average_salary': round(average_salary, 2),
                        'total_salary_expense': round(total_salary_expense, 2)
                    }

                    report_data.append(dept_data)
                    print(f"✅ Added department data: {dept_data}")

                except Exception as e:
                    print(f"❌ Error processing department {dept.name}: {str(e)}")
                    # Add empty data for this department
                    empty_data = {
                        'department_name': dept.name,
                        'total_employees': 0,
                        'average_salary': 0,
                        'total_salary_expense': 0
                    }
                    report_data.append(empty_data)
                    continue

            print(f"✅ Salary report returning: {len(report_data)} departments")
            return Response(report_data)

        except Exception as e:
            print(f"❌ Salary report error: {str(e)}")
            print(f"❌ Full traceback: {traceback.format_exc()}")
            return Response({
                'error': 'Failed to load salary report',
                'detail': str(e)
            }, status=200)  # Return empty array instead of 500 error


class StaffAttendanceViewSet(viewsets.ModelViewSet):
    queryset = StaffAttendance.objects.all()
    serializer_class = StaffAttendanceSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """Enhanced permission check with detailed logging"""
        try:
            # Check if request exists and user is authenticated
            if not hasattr(self, 'request') or not self.request:
                print("No request object found")
                return [IsAuthenticated()]

            user = self.request.user

            # If user is not authenticated, require authentication
            if not user or not user.is_authenticated:
                print("User not authenticated")
                return [IsAuthenticated()]

            # Enhanced logging
            print(f"Permission check for user: {user.email}")
            print(f"User authenticated: {user.is_authenticated}")
            print(f"User has role attr: {hasattr(user, 'role')}")
            if hasattr(user, 'role'):
                print(f"User role: {user.role}")

            # Check if user has role attribute
            if not hasattr(user, 'role'):
                print(f"User {user.email} has no role attribute")
                return [IsAuthenticated()]

            # Admin users bypass all permissions
            if user.role == 'admin':
                print(f"✅ Admin user {user.email} granted access")
                return []  # No permissions required

            # All other users need authentication
            print(f"Non-admin user {user.email} (role: {user.role}) requires authentication")
            return [IsAuthenticated()]

        except Exception as e:
            print(f"Permission check error: {str(e)}")
            print(f"Full traceback: {traceback.format_exc()}")
            return [IsAuthenticated()]

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
        try:
            print(f"🔍 Mobile checkin requested by: {request.user.email}")

            serializer = MobileAttendanceSerializer(data=request.data)
            if serializer.is_valid():
                employee_id = serializer.validated_data.get('employee_id')
                location = serializer.validated_data.get('location', '')
                device_info = serializer.validated_data.get('device_info', {})
                action_param = serializer.validated_data.get('action', 'check_in')

                print(f"📊 Checkin details - Employee: {employee_id}, Action: {action_param}")

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

                    if action_param == 'check_in':
                        if attendance.check_in_time:
                            return Response({
                                'success': False,
                                'message': 'Already checked in today',
                                'check_in_time': attendance.check_in_time.strftime('%H:%M')
                            }, status=status.HTTP_400_BAD_REQUEST)

                        attendance.check_in_time = current_time
                        attendance.check_in_location = location
                        attendance.save()

                        print(f"✅ Check-in successful for {employee.full_name}")
                        return Response({
                            'success': True,
                            'message': f'Checked in successfully at {current_time.strftime("%H:%M")}',
                            'employee_name': employee.full_name,
                            'check_in_time': current_time.strftime('%H:%M'),
                            'location': location
                        })

                    elif action_param == 'check_out':
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

                        print(f"✅ Check-out successful for {employee.full_name}")
                        return Response({
                            'success': True,
                            'message': f'Checked out successfully at {current_time.strftime("%H:%M")}',
                            'employee_name': employee.full_name,
                            'check_out_time': current_time.strftime('%H:%M'),
                            'total_hours': float(attendance.total_hours),
                            'location': location
                        })

                except StaffEmployee.DoesNotExist:
                    print(f"❌ Employee not found: {employee_id}")
                    return Response({
                        'success': False,
                        'message': 'Employee not found or inactive'
                    }, status=status.HTTP_404_NOT_FOUND)

            print(f"❌ Serializer errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print(f"❌ Mobile checkin error: {str(e)}")
            print(f"❌ Full traceback: {traceback.format_exc()}")
            return Response({
                'success': False,
                'message': 'System error during check-in/out',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def today_summary(self, request):
        """Get today's attendance summary - ENHANCED WITH COMPREHENSIVE DEBUGGING"""
        try:
            print(f"🔍 Today summary requested by: {request.user.email} (role: {getattr(request.user, 'role', 'NO_ROLE')})")

            today = timezone.now().date()

            # Get attendance records with error handling
            try:
                attendance_records = StaffAttendance.objects.filter(date=today).select_related('employee')
                total_employees = StaffEmployee.objects.filter(is_active=True).count()

                print(f"📊 Found {attendance_records.count()} attendance records for {today}")
                print(f"📊 Total active employees: {total_employees}")

            except Exception as e:
                print(f"❌ Database query error: {str(e)}")
                return Response({
                    'error': 'Database access failed',
                    'detail': str(e)
                }, status=500)

            summary = {
                'date': today.strftime('%Y-%m-%d'),
                'total_employees': total_employees,
                'present': attendance_records.filter(status='present').count(),
                'absent': 0,  # Will calculate
                'on_leave': attendance_records.filter(status='leave').count(),
                'late': attendance_records.filter(status='late').count(),
                'records': []
            }

            summary['absent'] = summary['total_employees'] - summary['present'] - summary['on_leave']

            print(f"📊 Summary calculated: Present: {summary['present']}, Absent: {summary['absent']}, On leave: {summary['on_leave']}")

            # Add individual records (limit to prevent large responses)
            record_count = 0
            for record in attendance_records[:20]:  # Limit to 20 records
                try:
                    record_data = {
                        'employee_id': record.employee.employee_id,
                        'employee_name': record.employee.full_name,
                        'status': record.status,
                        'check_in_time': record.check_in_time.strftime('%H:%M') if record.check_in_time else None,
                        'check_out_time': record.check_out_time.strftime('%H:%M') if record.check_out_time else None,
                        'total_hours': float(record.total_hours) if record.total_hours else 0
                    }
                    summary['records'].append(record_data)
                    record_count += 1
                except Exception as e:
                    print(f"❌ Error processing attendance record: {str(e)}")
                    continue

            print(f"✅ Today summary successful: {summary['present']} present, {summary['absent']} absent, {record_count} records")
            return Response(summary)

        except Exception as e:
            print(f"❌ Today summary error: {str(e)}")
            print(f"❌ Full traceback: {traceback.format_exc()}")
            return Response({
                'error': 'Failed to load attendance summary',
                'detail': str(e),
                'date': timezone.now().date().strftime('%Y-%m-%d'),
                'total_employees': 0,
                'present': 0,
                'absent': 0,
                'on_leave': 0,
                'late': 0,
                'records': []
            }, status=200)  # Return empty data instead of 500 error


class StaffPayrollViewSet(viewsets.ModelViewSet):
    queryset = StaffPayroll.objects.all()
    serializer_class = StaffPayrollSerializer
    permission_classes = [IsAuthenticated]
    @action(detail=False, methods=['post'], url_path='bulk_generate')
    def bulk_generate(self, request):
        """Bulk generate payroll for multiple employees"""
        try:
            employee_ids = request.data.get('employee_ids', [])
            month = request.data.get('month')
            year = request.data.get('year')
            auto_calculate = request.data.get('auto_calculate', True)

            if not employee_ids or not month or not year:
                return Response(
                    {'error': 'employee_ids, month, and year are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get employees
            employees = StaffEmployee.objects.filter(id__in=employee_ids, is_active=True)
            if not employees.exists():
                return Response(
                    {'error': 'No active employees found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            created_payrolls = []
            errors = []

            for employee in employees:
                try:
                    # Check if payroll already exists
                    existing_payroll = StaffPayroll.objects.filter(
                        employee=employee,
                        month=month,
                        year=year
                    ).first()

                    if existing_payroll:
                        errors.append(f"Payroll already exists for {employee.full_name}")
                        continue

                    # Calculate pay period dates
                    _, last_day = calendar.monthrange(int(year), int(month))
                    pay_period_start = date(int(year), int(month), 1)
                    pay_period_end = date(int(year), int(month), last_day)

                    # Get attendance data for the month
                    attendance_records = StaffAttendance.objects.filter(
                        employee=employee,
                        date__range=[pay_period_start, pay_period_end]
                    )

                    # Calculate hours
                    total_regular_hours = sum(record.regular_hours for record in attendance_records)
                    total_overtime_hours = sum(record.overtime_hours for record in attendance_records)
                    total_night_shift_hours = sum(
                        record.total_hours for record in attendance_records
                        if record.is_night_shift
                    )
                    total_weekend_hours = sum(
                        record.total_hours for record in attendance_records
                        if record.is_weekend
                    )
                    total_holiday_hours = sum(
                        record.total_hours for record in attendance_records
                        if record.is_holiday
                    )

                    # Calculate pay components
                    base_pay = float(employee.base_salary)
                    hourly_rate = float(employee.hourly_rate) if employee.hourly_rate else base_pay / 160  # Assume 160 hours/month
                    overtime_rate = float(employee.overtime_rate) if employee.overtime_rate else hourly_rate * 1.5

                    # Calculate earnings
                    overtime_pay = total_overtime_hours * overtime_rate
                    night_shift_pay = total_night_shift_hours * float(employee.night_shift_allowance)
                    weekend_pay = total_weekend_hours * hourly_rate * 1.2  # 20% extra for weekends
                    holiday_pay = total_holiday_hours * hourly_rate * 2.0  # Double pay for holidays

                    # Allowances
                    hra = float(employee.house_rent_allowance)
                    transport_allowance = float(employee.transport_allowance)
                    medical_allowance = float(employee.medical_allowance)
                    performance_bonus = 0  # Can be set based on performance metrics

                    gross_pay = (base_pay + overtime_pay + night_shift_pay + weekend_pay +
                               holiday_pay + hra + transport_allowance + medical_allowance +
                               performance_bonus)

                    # Calculate deductions
                    advance_deduction = 0
                    # Get pending advance deductions
                    pending_advances = StaffAdvancePayment.objects.filter(
                        employee=employee,
                        status='disbursed',
                        monthly_deduction_amount__gt=0
                    )
                    for advance in pending_advances:
                        advance_deduction += float(advance.monthly_deduction_amount)

                    loan_deduction = 0  # Can be implemented if loan system exists
                    provident_fund = gross_pay * 0.12  # 12% of gross pay
                    professional_tax = 200 if gross_pay > 15000 else 0  # Basic PT calculation
                    income_tax = 0  # Can be calculated based on tax slabs
                    other_deductions = 0

                    total_deductions = (advance_deduction + loan_deduction + provident_fund +
                                      professional_tax + income_tax + other_deductions)

                    net_pay = gross_pay - total_deductions

                    # Create payroll record
                    payroll = StaffPayroll.objects.create(
                        employee=employee,
                        month=month,
                        year=year,
                        pay_period_start=pay_period_start,
                        pay_period_end=pay_period_end,
                        base_pay=base_pay,
                        overtime_pay=overtime_pay,
                        night_shift_pay=night_shift_pay,
                        weekend_pay=weekend_pay,
                        holiday_pay=holiday_pay,
                        hra=hra,
                        transport_allowance=transport_allowance,
                        medical_allowance=medical_allowance,
                        performance_bonus=performance_bonus,
                        gross_pay=gross_pay,
                        advance_deduction=advance_deduction,
                        loan_deduction=loan_deduction,
                        provident_fund=provident_fund,
                        professional_tax=professional_tax,
                        income_tax=income_tax,
                        other_deductions=other_deductions,
                        total_deductions=total_deductions,
                        net_pay=net_pay,
                        regular_hours_worked=total_regular_hours,
                        overtime_hours_worked=total_overtime_hours,
                        night_shift_hours=total_night_shift_hours,
                        weekend_hours=total_weekend_hours,
                        holiday_hours=total_holiday_hours,
                        status='calculated' if auto_calculate else 'draft'
                    )

                    created_payrolls.append({
                        'id': payroll.id,
                        'employee': employee.full_name,
                        'gross_pay': gross_pay,
                        'net_pay': net_pay,
                        'status': payroll.status
                    })

                except Exception as e:
                    errors.append(f"Error creating payroll for {employee.full_name}: {str(e)}")

            return Response({
                'success': True,
                'created_count': len(created_payrolls),
                'created_payrolls': created_payrolls,
                'errors': errors
            })

        except Exception as e:
            return Response(
                {'error': f'Bulk generation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='calculate')
    def calculate(self, request, pk=None):
        """Recalculate payroll for a specific record"""
        try:
            payroll = get_object_or_404(StaffPayroll, pk=pk)

            # Recalculate all values (similar logic as bulk_generate)
            # This is a simplified version - you can expand based on requirements
            payroll.status = 'calculated'
            payroll.calculated_at = timezone.now()
            payroll.save()

            from .serializers import StaffPayrollSerializer
            serializer = StaffPayrollSerializer(payroll)
            return Response({
                'success': True,
                'message': 'Payroll calculated successfully',
                'payroll': serializer.data
            })

        except Exception as e:
            return Response(
                {'error': f'Calculation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        """Approve a payroll record"""
        try:
            payroll = get_object_or_404(StaffPayroll, pk=pk)
            notes = request.data.get('notes', '')

            if payroll.status not in ['calculated', 'draft']:
                return Response(
                    {'error': 'Only calculated or draft payrolls can be approved'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            payroll.status = 'approved'
            payroll.approval_date = timezone.now()
            payroll.approved_by = request.user
            payroll.approval_notes = notes
            payroll.save()

            from .serializers import StaffPayrollSerializer
            serializer = StaffPayrollSerializer(payroll)
            return Response({
                'success': True,
                'message': 'Payroll approved successfully',
                'payroll': serializer.data
            })

        except Exception as e:
            return Response(
                {'error': f'Approval failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get_permissions(self):
        """Enhanced permission check with detailed logging"""
        try:
            # Check if request exists and user is authenticated
            if not hasattr(self, 'request') or not self.request:
                print("No request object found")
                return [IsAuthenticated()]

            user = self.request.user

            # If user is not authenticated, require authentication
            if not user or not user.is_authenticated:
                print("User not authenticated")
                return [IsAuthenticated()]

            # Enhanced logging
            print(f"Permission check for user: {user.email}")
            print(f"User authenticated: {user.is_authenticated}")
            print(f"User has role attr: {hasattr(user, 'role')}")
            if hasattr(user, 'role'):
                print(f"User role: {user.role}")

            # Check if user has role attribute
            if not hasattr(user, 'role'):
                print(f"User {user.email} has no role attribute")
                return [IsAuthenticated()]

            # Admin users bypass all permissions
            if user.role == 'admin':
                print(f"✅ Admin user {user.email} granted access")
                return []  # No permissions required

            # All other users need authentication
            print(f"Non-admin user {user.email} (role: {user.role}) requires authentication")
            return [IsAuthenticated()]

        except Exception as e:
            print(f"Permission check error: {str(e)}")
            print(f"Full traceback: {traceback.format_exc()}")
            return [IsAuthenticated()]

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
        try:
            print(f"🔍 Payroll calculation requested by: {request.user.email} for payroll ID: {pk}")

            payroll = self.get_object()

            if payroll.status != 'draft':
                print(f"❌ Payroll {pk} not in draft status: {payroll.status}")
                return Response({
                    'success': False,
                    'message': 'Payroll can only be calculated in draft status'
                }, status=status.HTTP_400_BAD_REQUEST)

            payroll.calculated_by = request.user
            payroll.calculate_payroll()

            print(f"✅ Payroll {pk} calculated successfully")
            return Response({
                'success': True,
                'message': 'Payroll calculated successfully',
                'payroll': StaffPayrollSerializer(payroll).data
            })

        except Exception as e:
            print(f"❌ Payroll calculation error: {str(e)}")
            print(f"❌ Full traceback: {traceback.format_exc()}")
            return Response({
                'success': False,
                'message': 'Error calculating payroll',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve calculated payroll"""
        try:
            print(f"🔍 Payroll approval requested by: {request.user.email} for payroll ID: {pk}")

            payroll = self.get_object()

            if payroll.status != 'calculated':
                print(f"❌ Payroll {pk} not in calculated status: {payroll.status}")
                return Response({
                    'success': False,
                    'message': 'Payroll must be calculated before approval'
                }, status=status.HTTP_400_BAD_REQUEST)

            payroll.status = 'approved'
            payroll.approved_by = request.user
            payroll.approval_date = timezone.now()
            payroll.save()

            print(f"✅ Payroll {pk} approved successfully")
            return Response({
                'success': True,
                'message': 'Payroll approved successfully'
            })

        except Exception as e:
            print(f"❌ Payroll approval error: {str(e)}")
            print(f"❌ Full traceback: {traceback.format_exc()}")
            return Response({
                'success': False,
                'message': 'Error approving payroll',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def bulk_generate(self, request):
        """Generate payroll for all employees for a month"""
        try:
            month = request.data.get('month')
            year = request.data.get('year')

            print(f"🔍 Bulk payroll generation requested by: {request.user.email} for {month}/{year}")

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

            print(f"📊 Processing {employees.count()} employees for bulk payroll generation")

            for employee in employees:
                try:
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
                        print(f"✅ Created payroll for {employee.full_name}")
                    else:
                        print(f"📋 Payroll already exists for {employee.full_name}")

                except Exception as e:
                    print(f"❌ Error creating payroll for {employee.full_name}: {str(e)}")
                    continue

            print(f"✅ Bulk generation complete: {created_count}/{employees.count()} payrolls created")
            return Response({
                'success': True,
                'message': f'Generated {created_count} payroll records',
                'total_employees': employees.count(),
                'created_count': created_count
            })

        except Exception as e:
            print(f"❌ Bulk generate error: {str(e)}")
            print(f"❌ Full traceback: {traceback.format_exc()}")
            return Response({
                'success': False,
                'message': 'Error generating payroll records',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StaffAdvancePaymentViewSet(viewsets.ModelViewSet):
    queryset = StaffAdvancePayment.objects.all()
    serializer_class = StaffAdvancePaymentSerializer
    permission_classes = [IsAuthenticated]
    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        """Approve an advance payment request"""
        try:
            advance = get_object_or_404(StaffAdvancePayment, pk=pk)
            notes = request.data.get('notes', '')

            if advance.status != 'pending':
                return Response(
                    {'error': 'Only pending advances can be approved'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Calculate monthly deduction amount
            monthly_deduction = float(advance.amount) / advance.deduction_months

            advance.status = 'approved'
            advance.approval_date = timezone.now()
            advance.approved_by = request.user
            advance.approval_notes = notes
            advance.monthly_deduction_amount = monthly_deduction
            advance.save()

            from .serializers import StaffAdvancePaymentSerializer
            serializer = StaffAdvancePaymentSerializer(advance)
            return Response({
                'success': True,
                'message': 'Advance approved successfully',
                'advance': serializer.data
            })

        except Exception as e:
            return Response(
                {'error': f'Approval failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='disburse')
    def disburse(self, request, pk=None):
        """Disburse an approved advance payment"""
        try:
            advance = get_object_or_404(StaffAdvancePayment, pk=pk)
            method = request.data.get('method', 'bank_transfer')

            if advance.status != 'approved':
                return Response(
                    {'error': 'Only approved advances can be disbursed'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            advance.status = 'disbursed'
            advance.disbursement_date = timezone.now()
            advance.disbursed_by = request.user
            advance.disbursement_method = method
            advance.save()

            from .serializers import StaffAdvancePaymentSerializer
            serializer = StaffAdvancePaymentSerializer(advance)
            return Response({
                'success': True,
                'message': 'Advance disbursed successfully',
                'advance': serializer.data
            })

        except Exception as e:
            return Response(
                {'error': f'Disbursement failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        """Reject an advance payment request"""
        try:
            advance = get_object_or_404(StaffAdvancePayment, pk=pk)
            reason = request.data.get('reason', 'No reason provided')

            if advance.status not in ['pending', 'approved']:
                return Response(
                    {'error': 'Only pending or approved advances can be rejected'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            advance.status = 'rejected'
            advance.rejection_date = timezone.now()
            advance.rejected_by = request.user
            advance.rejection_reason = reason
            advance.save()

            from .serializers import StaffAdvancePaymentSerializer
            serializer = StaffAdvancePaymentSerializer(advance)
            return Response({
                'success': True,
                'message': 'Advance rejected successfully',
                'advance': serializer.data
            })

        except Exception as e:
            return Response(
                {'error': f'Rejection failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get_permissions(self):
        """Enhanced permission check with detailed logging"""
        try:
            # Check if request exists and user is authenticated
            if not hasattr(self, 'request') or not self.request:
                print("No request object found")
                return [IsAuthenticated()]

            user = self.request.user

            # If user is not authenticated, require authentication
            if not user or not user.is_authenticated:
                print("User not authenticated")
                return [IsAuthenticated()]

            # Enhanced logging
            print(f"Permission check for user: {user.email}")
            print(f"User authenticated: {user.is_authenticated}")
            print(f"User has role attr: {hasattr(user, 'role')}")
            if hasattr(user, 'role'):
                print(f"User role: {user.role}")

            # Check if user has role attribute
            if not hasattr(user, 'role'):
                print(f"User {user.email} has no role attribute")
                return [IsAuthenticated()]

            # Admin users bypass all permissions
            if user.role == 'admin':
                print(f"✅ Admin user {user.email} granted access")
                return []  # No permissions required

            # All other users need authentication
            print(f"Non-admin user {user.email} (role: {user.role}) requires authentication")
            return [IsAuthenticated()]

        except Exception as e:
            print(f"Permission check error: {str(e)}")
            print(f"Full traceback: {traceback.format_exc()}")
            return [IsAuthenticated()]

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
        try:
            print(f"🔍 Advance approval requested by: {request.user.email} for advance ID: {pk}")

            advance = self.get_object()
            notes = request.data.get('notes', '')

            if advance.approve_advance(request.user, notes):
                print(f"✅ Advance {pk} approved successfully")
                return Response({
                    'success': True,
                    'message': 'Advance payment approved successfully'
                })
            else:
                print(f"❌ Cannot approve advance {pk}")
                return Response({
                    'success': False,
                    'message': 'Cannot approve this advance payment'
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print(f"❌ Advance approval error: {str(e)}")
            print(f"❌ Full traceback: {traceback.format_exc()}")
            return Response({
                'success': False,
                'message': 'Error approving advance payment',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def disburse(self, request, pk=None):
        """Disburse approved advance payment"""
        try:
            print(f"🔍 Advance disbursement requested by: {request.user.email} for advance ID: {pk}")

            advance = self.get_object()
            method = request.data.get('method', 'bank_transfer')

            if advance.disburse_advance(request.user, method):
                print(f"✅ Advance {pk} disbursed successfully")
                return Response({
                    'success': True,
                    'message': 'Advance payment disbursed successfully'
                })
            else:
                print(f"❌ Cannot disburse advance {pk}")
                return Response({
                    'success': False,
                    'message': 'Cannot disburse this advance payment'
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print(f"❌ Advance disbursement error: {str(e)}")
            print(f"❌ Full traceback: {traceback.format_exc()}")
            return Response({
                'success': False,
                'message': 'Error disbursing advance payment',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def pending_summary(self, request):
        """Get summary of pending advance payments"""
        try:
            print(f"🔍 Pending advances summary requested by: {request.user.email}")

            pending = StaffAdvancePayment.objects.filter(status='pending')

            summary = {
                'total_count': pending.count(),
                'total_amount': pending.aggregate(total=Sum('amount'))['total'] or 0,
                'urgent_count': pending.filter(urgency_level='urgent').count(),
                'high_priority_count': pending.filter(urgency_level='high').count()
            }

            print(f"✅ Pending advances summary: {summary}")
            return Response(summary)

        except Exception as e:
            print(f"❌ Pending summary error: {str(e)}")
            print(f"❌ Full traceback: {traceback.format_exc()}")
            return Response({
                'error': 'Failed to load pending advances summary',
                'detail': str(e),
                'total_count': 0,
                'total_amount': 0,
                'urgent_count': 0,
                'high_priority_count': 0
            }, status=200)  # Return empty data instead of error


ubuntu@hotel-management-server:~/hotel-management-backend$

