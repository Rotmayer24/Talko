from django.urls import re_path
from messages.consumers import ChatConsumer

ws_urlpatterns = [
    re_path(r"ws/chat/(?P<room_name>\w+)/$", ChatConsumer.as_asgi()),
]
