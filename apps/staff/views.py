# apps/staff/views.py - COMPLETE UPDATED VERSION WITH PERMISSION FIXES
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

    def get_permissions(self):
        """Allow admin users full access to staff management"""
        if (self.request.user.is_authenticated and 
            hasattr(self.request.user, 'role') and 
            self.request.user.role == 'admin'):
            return []  # No additional permissions needed for admin
        return [IsAuthenticated()]


class StaffEmployeeViewSet(viewsets.ModelViewSet):
    queryset = StaffEmployee.objects.all()
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """Allow admin users full access to staff management"""
        if (self.request.user.is_authenticated and 
            hasattr(self.request.user, 'role') and 
            self.request.user.role == 'admin'):
            return []  # No additional permissions needed for admin
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
        """Get dashboard statistics - ENHANCED WITH ERROR HANDLING"""
        try:
            print(f"Dashboard stats requested by: {request.user.email} (role: {getattr(request.user, 'role', 'NO_ROLE')})")

            today = timezone.now().date()

            # Basic employee counts
            total_employees = StaffEmployee.objects.filter(is_active=True).count()
            active_employees = StaffEmployee.objects.filter(employment_status='active').count()

            # Today's attendance with error handling
            try:
                today_attendance = StaffAttendance.objects.filter(date=today)
                present_today = today_attendance.filter(status='present').count()
                on_leave = today_attendance.filter(status='leave').count()
            except Exception as e:
                print(f"Attendance query error: {str(e)}")
                present_today = 0
                on_leave = 0

            # Pending advance payments with error handling
            try:
                pending_advances = StaffAdvancePayment.objects.filter(status='pending').count()
            except Exception as e:
                print(f"Advances query error: {str(e)}")
                pending_advances = 0

            # This month's payroll with error handling
            try:
                current_month = timezone.now().month
                current_year = timezone.now().year
                payrolls_processed = StaffPayroll.objects.filter(
                    month=current_month, year=current_year, status='paid'
                ).count()
            except Exception as e:
                print(f"Payroll query error: {str(e)}")
                payrolls_processed = 0

            response_data = {
                'total_employees': total_employees,
                'active_employees': active_employees,
                'present_today': present_today,
                'on_leave': on_leave,
                'absent_today': max(0, active_employees - present_today - on_leave),
                'pending_advances': pending_advances,
                'payrolls_processed': payrolls_processed,
                'date': today.strftime('%Y-%m-%d')
            }

            print(f"Dashboard stats returning: {response_data}")
            return Response(response_data)

        except Exception as e:
            print(f"Dashboard stats error: {str(e)}")
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
                'date': timezone.now().date().strftime('%Y-%m-%d')
            }, status=200)  # Return 200 with error data instead of 500

    @action(detail=False, methods=['get'])
    def salary_report(self, request):
        """Get salary statistics by department - ENHANCED WITH ERROR HANDLING"""
        try:
            print(f"Salary report requested by: {request.user.email}")

            # Use simpler approach to avoid complex annotation issues
            departments = StaffDepartment.objects.filter(is_active=True)
            report_data = []

            for dept in departments:
                try:
                    # Get employees for this department
                    dept_employees = StaffEmployee.objects.filter(
                        department=dept, 
                        is_active=True
                    )

                    total_employees = dept_employees.count()

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

                    report_data.append({
                        'department_name': dept.name,
                        'total_employees': total_employees,
                        'average_salary': round(average_salary, 2),
                        'total_salary_expense': round(total_salary_expense, 2)
                    })

                except Exception as e:
                    print(f"Error processing department {dept.name}: {str(e)}")
                    # Add empty data for this department
                    report_data.append({
                        'department_name': dept.name,
                        'total_employees': 0,
                        'average_salary': 0,
                        'total_salary_expense': 0
                    })
                    continue

            print(f"Salary report returning: {len(report_data)} departments")
            return Response(report_data)

        except Exception as e:
            print(f"Salary report error: {str(e)}")
            return Response({
                'error': 'Failed to load salary report',
                'detail': str(e)
            }, status=200)  # Return empty array instead of 500 error


class StaffAttendanceViewSet(viewsets.ModelViewSet):
    queryset = StaffAttendance.objects.all()
    serializer_class = StaffAttendanceSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """Allow admin users full access to staff management"""
        if (self.request.user.is_authenticated and 
            hasattr(self.request.user, 'role') and 
            self.request.user.role == 'admin'):
            return []  # No additional permissions needed for admin
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
            serializer = MobileAttendanceSerializer(data=request.data)
            if serializer.is_valid():
                employee_id = serializer.validated_data.get('employee_id')
                location = serializer.validated_data.get('location', '')
                device_info = serializer.validated_data.get('device_info', {})
                action_param = serializer.validated_data.get('action', 'check_in')

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

        except Exception as e:
            print(f"Mobile checkin error: {str(e)}")
            return Response({
                'success': False,
                'message': 'System error during check-in/out',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def today_summary(self, request):
        """Get today's attendance summary - ENHANCED WITH ERROR HANDLING"""
        try:
            print(f"Today summary requested by: {request.user.email}")

            today = timezone.now().date()

            # Get attendance records with error handling
            try:
                attendance_records = StaffAttendance.objects.filter(date=today).select_related('employee')
                total_employees = StaffEmployee.objects.filter(is_active=True).count()
            except Exception as e:
                print(f"Database query error: {str(e)}")
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

            # Add individual records (limit to prevent large responses)
            for record in attendance_records[:20]:  # Limit to 20 records
                try:
                    summary['records'].append({
                        'employee_id': record.employee.employee_id,
                        'employee_name': record.employee.full_name,
                        'status': record.status,
                        'check_in_time': record.check_in_time.strftime('%H:%M') if record.check_in_time else None,
                        'check_out_time': record.check_out_time.strftime('%H:%M') if record.check_out_time else None,
                        'total_hours': float(record.total_hours) if record.total_hours else 0
                    })
                except Exception as e:
                    print(f"Error processing attendance record: {str(e)}")
                    continue

            print(f"Today summary returning: {summary['present']} present, {summary['absent']} absent")
            return Response(summary)

        except Exception as e:
            print(f"Today summary error: {str(e)}")
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

    def get_permissions(self):
        """Allow admin users full access to staff management"""
        if (self.request.user.is_authenticated and 
            hasattr(self.request.user, 'role') and 
            self.request.user.role == 'admin'):
            return []  # No additional permissions needed for admin
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

        except Exception as e:
            print(f"Payroll calculation error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Error calculating payroll',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve calculated payroll"""
        try:
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

        except Exception as e:
            print(f"Payroll approval error: {str(e)}")
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
                except Exception as e:
                    print(f"Error creating payroll for {employee.full_name}: {str(e)}")
                    continue

            return Response({
                'success': True,
                'message': f'Generated {created_count} payroll records',
                'total_employees': employees.count(),
                'created_count': created_count
            })

        except Exception as e:
            print(f"Bulk generate error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Error generating payroll records',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StaffAdvancePaymentViewSet(viewsets.ModelViewSet):
    queryset = StaffAdvancePayment.objects.all()
    serializer_class = StaffAdvancePaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """Allow admin users full access to staff management"""
        if (self.request.user.is_authenticated and 
            hasattr(self.request.user, 'role') and 
            self.request.user.role == 'admin'):
            return []  # No additional permissions needed for admin
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

        except Exception as e:
            print(f"Advance approval error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Error approving advance payment',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def disburse(self, request, pk=None):
        """Disburse approved advance payment"""
        try:
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

        except Exception as e:
            print(f"Advance disbursement error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Error disbursing advance payment',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def pending_summary(self, request):
        """Get summary of pending advance payments"""
        try:
            pending = StaffAdvancePayment.objects.filter(status='pending')

            summary = {
                'total_count': pending.count(),
                'total_amount': pending.aggregate(total=Sum('amount'))['total'] or 0,
                'urgent_count': pending.filter(urgency_level='urgent').count(),
                'high_priority_count': pending.filter(urgency_level='high').count()
            }

            return Response(summary)

        except Exception as e:
            print(f"Pending summary error: {str(e)}")
            return Response({
                'error': 'Failed to load pending advances summary',
                'detail': str(e),
                'total_count': 0,
                'total_amount': 0,
                'urgent_count': 0,
                'high_priority_count': 0
            }, status=200)  # Return empty data instead of error

