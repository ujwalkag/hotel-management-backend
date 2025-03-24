from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)

urlpatterns = [
    # JWT Token URLs
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # Get access & refresh token
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # Get new access token
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),  # Verify token validity
]

