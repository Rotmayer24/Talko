from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "accounts"

urlpatterns = [
    path("register", views.RegisterView.as_view(), name="register"),
    path(
        "login",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path(
        "logout",
        auth_views.LogoutView.as_view(
            template_name="accounts/logged_out.html",
        ),
        name="logout",
    ),
    path("search/", views.search_users_and_groups, name="search"),
    path("users/", views.users_list, name="users_list"),
    path("add/<int:user_id>/", views.send_friend_request, name="add_friend"),
    path("requests/", views.incoming_requests, name="requests"),
    path("accept/<int:request_id>/", views.accept_friend_request, name="accept_friend"),
    path("reject/<int:request_id>/", views.reject_friend_request, name="reject_friend"),
    path("notifications/", views.notifications_list, name="notifications"),
    path("notifications/<int:notification_id>/read/", views.mark_notification_read, name="mark_notification_read"),
    path("notifications/read-all/", views.mark_all_notifications_read, name="mark_all_notifications_read"),
    path("profile/", views.profile_view, name="profile"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path("password/change/", views.change_password, name="change_password"),
    path("verify-email/<str:token>/", views.verify_email, name="verify_email"),
    path("resend-verification/", views.resend_verification_email, name="resend_verification"),
]
