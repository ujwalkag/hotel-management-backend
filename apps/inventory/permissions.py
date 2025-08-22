# apps/inventory/permissions.py
from rest_framework.permissions import BasePermission

class IsAdminOnly(BasePermission):
    """
    Permission that allows only admin users.
    Inventory management should be admin-only for cost control.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.role == 'admin'
        )

class IsAdminOrStaffReadOnly(BasePermission):
    """
    Permission for viewing inventory - staff can view but not modify.
    Admin can do everything, staff can only read.
    """
    def has_permission(self, request, view):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            # Staff can view inventory
            return (
                request.user.is_authenticated and 
                request.user.role in ['admin', 'staff']
            )
        else:
            # Only admin can modify inventory
            return (
                request.user.is_authenticated and 
                request.user.role == 'admin'
            )

class CanViewInventory(BasePermission):
    """
    Permission for viewing inventory items - both admin and staff.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.role in ['admin', 'staff']
        )
