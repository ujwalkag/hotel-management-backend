from django.urls import path
from . import views

urlpatterns = [
    path('notify/', views.notify_admin, name='notify_admin'),
]
