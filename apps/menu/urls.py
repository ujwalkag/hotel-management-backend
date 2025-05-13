from rest_framework.routers import DefaultRouter
from .views import MenuItemViewSet, MenuCategoryViewSet

router = DefaultRouter()
router.register(r'items', MenuItemViewSet, basename='menu-items')
router.register(r'categories', MenuCategoryViewSet, basename='menu-categories')

urlpatterns = router.urls

