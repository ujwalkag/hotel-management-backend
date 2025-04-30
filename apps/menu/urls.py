from django.urls import path
from .views import (
    MenuListView,
    CreateMenuItemView,
    MenuItemListView,
    UpdateMenuItemView,
    DeleteMenuItemView,
)

urlpatterns = [
    path("list/", MenuListView.as_view(), name="menu-list"),  # ✅ Needed for frontend
    path("create/", CreateMenuItemView.as_view(), name="menu-create"),
    path("admin-list/", MenuItemListView.as_view(), name="menu-admin-list"),
    path("update/<int:id>/", UpdateMenuItemView.as_view(), name="menu-update"),
    path("delete/<int:id>/", DeleteMenuItemView.as_view(), name="menu-delete"),
]

