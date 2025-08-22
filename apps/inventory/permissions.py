# apps/inventory/permissions.py - Create admin-only permission for inventory
from rest_framework import permissions
from apps.users.models import CustomUser

class IsAdminOnly(permissions.BasePermission):
    """
    Custom permission to only allow admin users to access inventory.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'admin'
        )

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Admin can do everything, others can only read (if needed for reports)
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin can do everything
        if request.user.role == 'admin':
            return True
            
        # Staff can only read (for reports/viewing)
        if request.user.role == 'staff' and request.method in permissions.SAFE_METHODS:
            return True
            
        return False
