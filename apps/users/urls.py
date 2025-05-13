from django.urls import path
from .views import CustomTokenObtainPairView

urlpatterns = [
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
]

