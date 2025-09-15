# apps/restaurant/routing.py - WebSocket URL routing
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/kds/$', consumers.KitchenDisplayConsumer.as_asgi()),
    re_path(r'ws/ordering/$', consumers.OrderingConsumer.as_asgi()),
    re_path(r'ws/table-management/$', consumers.TableManagementConsumer.as_asgi()),
]

