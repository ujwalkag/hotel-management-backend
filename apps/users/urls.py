from django.urls import path
from .views import LogoutView
#from .views import CustomTokenObtainPairView, StaffUserViewSet
from .views import (
    LogoutView,
    CustomTokenObtainPairView,
    StaffUserViewSet,
    verify_token,
    user_profile
)
staff_view = StaffUserViewSet.as_view({
    'get': 'list',
    'post': 'create',
})

staff_detail = StaffUserViewSet.as_view({
    'delete': 'destroy',
})

urlpatterns = [
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('staff/', staff_view, name='staff-list-create'),
    path('auth/verify/', verify_token, name='verify-token'),
    path('profile/', user_profile, name='user-profile'),
    path('staff/<int:pk>/', staff_detail, name='staff-delete'),
    path("logout/", LogoutView.as_view(), name="logout"),
]

