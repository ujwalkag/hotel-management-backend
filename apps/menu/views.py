# apps/menu/views.py
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from django.utils import timezone
from .models import MenuItem, MenuCategory
from .serializers import MenuItemSerializer, MenuCategorySerializer


class IsAdminOrReadOnly(permissions.BasePermission):
    """Admin users can create/update/delete, others (staff) can only view."""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.role == 'admin'

class MenuItemViewSet(viewsets.ModelViewSet):
    serializer_class = MenuItemSerializer
    permission_classes = [IsAdminOrReadOnly]
    
    def get_queryset(self):
        """Filter out discontinued items by default"""
        show_all = self.request.query_params.get('show_all', 'false').lower() == 'true'
        if show_all:
            return MenuItem.objects.all().order_by('-created_at')
        return MenuItem.objects.filter(is_discontinued=False).order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except ValueError as e:
            # Log the error
            print(f"List MenuItem error: {e}")
            # Fallback: raw SQL to fetch only ID, names, price, available
            cursor = connection.cursor()
            cursor.execute("""
                SELECT id, name_en, name_hi, price, available 
                FROM menu_menuitem 
                WHERE is_active = TRUE
                ORDER BY created_at DESC
            """)
            rows = cursor.fetchall()
            data = [
                {
                    "id": row[0],
                    "name_en": row[1],
                    "name_hi": row[2],
                    "price": row[3],
                    "available": row[4],
                }
                for row in rows
            ]
            return Response(data, status=status.HTTP_200_OK)
    def destroy(self, request, *args, **kwargs):
        """Enhanced delete with soft delete support"""
        try:
            instance = self.get_object()
            
            # Check if item can be safely hard deleted
            if instance.can_be_hard_deleted():
                # Safe to hard delete - no order references
                instance.delete()
                return Response({
                    'success': True,
                    'message': f'Menu item "{instance.name_en}" deleted successfully',
                    'type': 'hard_delete'
                }, status=status.HTTP_200_OK)
            else:
                # Item has order history - soft delete
                reason = request.data.get('reason', 'Item has order history')
                instance.soft_delete(reason)
                
                return Response({
                    'success': True,
                    'message': f'Menu item "{instance.name_en}" marked as discontinued',
                    'detail': 'Item has order history so it was deactivated instead of deleted',
                    'type': 'soft_delete',
                    'discontinued_at': instance.discontinued_at,
                    'reason': instance.discontinue_reason
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Failed to delete menu item',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrReadOnly])
    def reactivate(self, request, pk=None):
        """Reactivate a discontinued item"""
        try:
            instance = self.get_object()
            if instance.is_discontinued:
                instance.is_active = True
                instance.is_discontinued = False
                instance.discontinued_at = None
                instance.discontinue_reason = ""
                instance.save()
                
                return Response({
                    'success': True,
                    'message': f'Menu item "{instance.name_en}" reactivated successfully'
                })
            else:
                return Response({
                    'success': False,
                    'message': 'Item is not discontinued'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Failed to reactivate item',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MenuCategoryViewSet(viewsets.ModelViewSet):
    queryset = MenuCategory.objects.all()
    serializer_class = MenuCategorySerializer
    permission_classes = [IsAdminOrReadOnly]

