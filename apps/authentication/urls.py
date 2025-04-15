from django.urls import path
from .views import CustomLoginView  # ✅ Correct import name
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)

urlpatterns = [
    path('token/', CustomLoginView.as_view(), name='token_obtain_pair'),  # ✅ Proper JWT login view
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]

