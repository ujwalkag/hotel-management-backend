# apps/inventory/permissions.py
from rest_framework import permissions

class IsAdminOnly(permissions.BasePermission):
    """
    Custom permission to only allow admin users to access inventory.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'role') and
            request.user.role == 'admin'
        )
