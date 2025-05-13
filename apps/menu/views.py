from rest_framework import viewsets, permissions
from .models import MenuItem, MenuCategory
from .serializers import MenuItemSerializer, MenuCategorySerializer

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Admin users can create/update/delete, others (staff) can only view.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.role == 'admin'

class MenuItemViewSet(viewsets.ModelViewSet):
    queryset = MenuItem.objects.all().order_by('-created_at')
    serializer_class = MenuItemSerializer
    permission_classes = [IsAdminOrReadOnly]

class MenuCategoryViewSet(viewsets.ModelViewSet):
    queryset = MenuCategory.objects.all()
    serializer_class = MenuCategorySerializer
    permission_classes = [IsAdminOrReadOnly]

