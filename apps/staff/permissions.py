# apps/staff/permissions.py
from rest_framework.permissions import BasePermission

class IsAdminOnly(BasePermission):
    """
    Permission that allows only admin users.
    Staff management should be admin-only for security.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.role == 'admin'
        )

class IsAdminOrStaff(BasePermission):
    """
    Permission for basic staff operations - viewing their own data.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.role in ['admin', 'staff']
        )

class CanMarkAttendance(BasePermission):
    """
    Permission for marking attendance - admin can mark for anyone,
    staff can mark their own.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.role in ['admin', 'staff']
        )

    def has_object_permission(self, request, view, obj):
        # Admin can access any attendance record
        if request.user.role == 'admin':
            return True
        
        # Staff can only access their own attendance records
        if request.user.role == 'staff':
            # Check if the user has a staff profile and if this attendance belongs to them
            try:
                staff_profile = request.user.staff_profile
                return obj.staff == staff_profile
            except:
                return False
        
        return False
