from django.urls import path
from .views import ProfileView
from .token_views import MyTokenObtainPairView

urlpatterns = [
    path('profile/', ProfileView.as_view(), name='profile'),
    path('token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
]

