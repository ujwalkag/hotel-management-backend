from django.urls import path
from authentication.views import LoginView, CreateStaffUserView, ResetPasswordView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('create-staff/', CreateStaffUserView.as_view(), name='create_staff'),
    path('reset-password/<int:user_id>/', ResetPasswordView.as_view(), name='reset_password'),
]
