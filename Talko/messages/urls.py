from django.urls import path
from . import views

app_name = "messages"

urlpatterns = [
    path("", views.home, name="home"),
    path("chat/<int:chat_id>/send/", views.send_message, name="send_message"),
    path("chat/<int:chat_id>/upload/", views.upload_file, name="upload_file"),
    path("chat/<int:chat_id>/delete/<int:message_id>/", views.delete_message, name="delete_message"),
    path("group/create/", views.create_group, name="create_group"),
    path("group/<int:group_id>/join/", views.join_group, name="join_group"),
    path("group/<int:group_id>/leave/", views.leave_group, name="leave_group"),
    path("group/<int:group_id>/settings/", views.group_settings, name="group_settings"),
]
