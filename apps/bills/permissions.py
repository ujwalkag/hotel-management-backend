from rest_framework.permissions import BasePermission

class IsAdminOrStaff(BasePermission):
    """
    Allows access only to admin and staff users.
    """
    def has_permission(self, request, view):
        print("STAFF DEBUG:", request.user, getattr(request.user, "role", None))
        return request.user.is_authenticated and getattr(request.user, "role", None) in ['admin', 'staff']
