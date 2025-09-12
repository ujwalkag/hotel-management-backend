# apps/users/permissions.py

from rest_framework.permissions import BasePermission

class IsAdminOrStaff(BasePermission):
    def has_permission(self, request, view):
        # Allow any authenticated user to list and retrieve (safe methods)
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return request.user.is_authenticated
        # Only admin can create/update/delete users
        return request.user.is_authenticated and request.user.role == 'admin'

class IsAdminOnly(BasePermission):
    """Only admin users can access"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'

