from django.urls import path , include
from .views import LogoutView
from rest_framework.routers import DefaultRouter
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
router = DefaultRouter()
router.register('staff', StaffUserViewSet, basename='staff')
urlpatterns = [
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/verify/', verify_token, name='verify-token'),
    path('profile/', user_profile, name='user-profile'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('', include(router.urls)),

]

