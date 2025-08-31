# apps/tables/permissions.py
from rest_framework.permissions import BasePermission

class CanCreateOrders(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            (request.user.role == 'admin' or 
             (request.user.role == 'waiter' and request.user.can_create_orders))
        )

class CanGenerateBills(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            (request.user.role == 'admin' or 
             (request.user.role in ['biller', 'staff'] and request.user.can_generate_bills))
        )

class CanAccessKitchen(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            (request.user.role == 'admin' or request.user.can_access_kitchen)
        )

class IsAdminOrStaff(BasePermission):
    """
    Permission that allows admin and staff users to perform operations.
    Same permission structure as your existing bills app.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.role in ['admin', 'staff']
        )

class IsManagerOrAdmin(BasePermission):
    """
    Permission for management-level operations like staff management, 
    inventory management, etc.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.role == 'admin'
        )

class IsKitchenStaffOrAdmin(BasePermission):
    """
    Permission for kitchen operations - viewing and updating order status.
    """
    def has_permission(self, request, view):
        # Kitchen staff, admin, and regular staff can access kitchen display
        return (
            request.user.is_authenticated and 
            request.user.role in ['admin', 'staff']
        )

class CanViewKitchenDisplay(BasePermission):
    """
    Permission for viewing kitchen display - broader access for kitchen operations.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.role in ['admin', 'staff']
        )
