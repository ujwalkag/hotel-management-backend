from django.urls import path
from . import views

urlpatterns = [
    path('book/', views.book_room, name='book_room'),
    path('cancel/', views.cancel_booking, name='cancel_booking'),
]
