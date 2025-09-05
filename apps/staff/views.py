from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import PayrollStaff
import uuid

# ADD THESE FUNCTIONS AT THE END OF apps/staff/views.py

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def payroll_staff_management(request):
    """Separate payroll staff management (not linked to base users)"""
    
    if request.method == 'GET':
        # Get all payroll staff
        payroll_staff = PayrollStaff.objects.all().order_by('-created_at')
        
        staff_data = []
        for staff in payroll_staff:
            staff_data.append({
                'id': staff.id,
                'full_name': staff.full_name,
                'phone': staff.phone,
                'employee_id': staff.employee_id,
                'department': staff.department,
                'position': staff.position,
                'base_salary': float(staff.base_salary),
                'hourly_rate': float(staff.hourly_rate),
                'created_at': staff.created_at.isoformat()
            })
        
        return Response(staff_data)
    
    elif request.method == 'POST':
        # Create new payroll staff
        data = request.data
        
        try:
            payroll_staff = PayrollStaff.objects.create(
                full_name=data['full_name'],
                phone=data['phone'],
                department=data.get('department', 'service'),
                position=data.get('position', ''),
                base_salary=data.get('base_salary', 0),
                hourly_rate=data.get('hourly_rate', 0),
                created_by=request.user
            )
            
            return Response({
                'success': True,
                'message': 'Payroll staff created',
                'staff_id': payroll_staff.id
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_payroll_staff(request, staff_id):
    """Delete payroll staff member"""
    try:
        staff = get_object_or_404(PayrollStaff, id=staff_id)
        staff_name = staff.full_name
        staff.delete()
        
        return Response({
            'success': True,
            'message': f'{staff_name} deleted successfully'
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
