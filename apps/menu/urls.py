from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MenuItemViewSet, MenuCategoryViewSet

router = DefaultRouter()
router.register(r'items', MenuItemViewSet, basename='menu-item')
router.register(r'categories', MenuCategoryViewSet, basename='menu-category')

urlpatterns = [
    path('', include(router.urls)),
]

