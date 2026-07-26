from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.views.generic import CreateView
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import uuid
from messages.models import Chat
from .forms import CustomUserRegisterForm, UserLoginForm
from .models import FriendRequest, UserProfile, get_friends, Notification

EMAIL_VERIFICATION_TTL = timedelta(hours=24)
EMAIL_RESEND_COOLDOWN = timedelta(minutes=5)


def create_notification(user, notification_type, title, message, link=""):
    Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link,
    )


def send_verification_email(request, user):
    """Generate a fresh token and email a verification link to the user."""
    if not user.email:
        return False

    profile = user.profile
    token = str(uuid.uuid4())
    profile.email_verification_token = token
    profile.email_verification_sent_at = timezone.now()
    profile.save()

    verification_link = request.build_absolute_uri(
        reverse("accounts:verify_email", kwargs={"token": token})
    )

    send_mail(
        "Verify your email - Talko",
        f"Click this link to verify your email: {verification_link}",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
    return True


class RegisterView(CreateView):
    form_class = CustomUserRegisterForm
    template_name = "accounts/register.html"

    def form_valid(self, form):
        self.object = form.save()
        send_verification_email(self.request, self.object)
        return render(
            self.request,
            "accounts/email_verification_sent.html",
            {"email": self.object.email},
        )


def login_view(request):
    if request.method == "POST":
        form = UserLoginForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("index")
    else:
        form = UserLoginForm()

    return render(request, "accounts/login.html", {"form": form})


@login_required
def search_users_and_groups(request):
    query = request.GET.get("q", "").strip()

    user_data = []
    group_data = []

    if query and len(query) >= 2:
        users = User.objects.filter(username__icontains=query).exclude(
            id=request.user.id
        )[:10]

        friends = get_friends(request.user)
        sent_requests = FriendRequest.objects.filter(
            from_user=request.user, status="pending"
        ).values_list("to_user_id", flat=True)

        for user in users:
            status = "add"
            if user in friends:
                status = "friend"
            elif user.id in sent_requests:
                status = "pending"

            user_data.append({"user": user, "status": status})

        groups = Chat.objects.filter(is_group=True, group_name__icontains=query)[:10]

        for group in groups:
            is_member = request.user in group.users.all()
            group_data.append({"group": group, "is_member": is_member})

    return render(
        request,
        "accounts/search.html",
        {"query": query, "users": user_data, "groups": group_data},
    )


@login_required
def send_friend_request(request, user_id):
    to_user = get_object_or_404(User, id=user_id)

    if to_user == request.user:
        return redirect("accounts:search")

    existing_request = FriendRequest.objects.filter(
        from_user=request.user, to_user=to_user
    ).first()

    if not existing_request:
        try:
            FriendRequest.objects.create(from_user=request.user, to_user=to_user)
            create_notification(
                to_user,
                "friend_request",
                "New Friend Request",
                f"{request.user.username} sent you a friend request",
                "/accounts/requests/",
            )
        except ValueError:
            pass

    return redirect("accounts:search")


@login_required
def users_list(request):
    return redirect("accounts:search")


@login_required
def incoming_requests(request):
    requests = FriendRequest.objects.filter(to_user=request.user, status="pending")
    return render(request, "accounts/requests.html", {"requests": requests})


@login_required
def accept_friend_request(request, request_id):
    fr = get_object_or_404(
        FriendRequest, id=request_id, to_user=request.user, status="pending"
    )

    fr.status = "accepted"
    fr.save()

    existing_chat = (
        Chat.objects.filter(users=fr.from_user).filter(users=fr.to_user).first()
    )

    if not existing_chat:
        chat = Chat.objects.create()
        chat.users.add(fr.from_user, fr.to_user)

    create_notification(
        fr.from_user,
        "friend_accepted",
        "Friend Request Accepted",
        f"{request.user.username} accepted your friend request",
        "/",
    )

    return redirect("accounts:requests")


@login_required
def reject_friend_request(request, request_id):
    fr = get_object_or_404(
        FriendRequest, id=request_id, to_user=request.user, status="pending"
    )

    fr.status = "rejected"
    fr.save()

    return redirect("accounts:requests")


@login_required
def notifications_list(request):
    notifications = Notification.objects.filter(user=request.user)
    unread_count = notifications.filter(is_read=False).count()
    return render(
        request,
        "accounts/notifications.html",
        {"notifications": notifications, "unread_count": unread_count},
    )


@login_required
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(
        Notification, id=notification_id, user=request.user
    )
    notification.is_read = True
    notification.save()

    if notification.link:
        return redirect(notification.link)
    return redirect("accounts:notifications")


@login_required
def mark_all_notifications_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect("accounts:notifications")


@login_required
def chat_view(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id, users=request.user)
    messages = chat.messages.all()
    return render(request, "chat.html", {"chat": chat, "messages": messages})


@login_required
def profile_view(request):
    profile = request.user.profile
    return render(request, "accounts/profile.html", {"profile": profile})


@login_required
def edit_profile(request):
    profile = request.user.profile

    if request.method == "POST":
        from .forms import UserProfileForm

        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect("accounts:profile")
    else:
        from .forms import UserProfileForm

        form = UserProfileForm(instance=profile)

    return render(request, "accounts/edit_profile.html", {"form": form})


@login_required
def change_password(request):
    if request.method == "POST":
        from .forms import CustomPasswordChangeForm

        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            from django.contrib.auth import update_session_auth_hash

            update_session_auth_hash(request, user)
            return redirect("accounts:profile")
    else:
        from .forms import CustomPasswordChangeForm

        form = CustomPasswordChangeForm(request.user)

    return render(request, "accounts/change_password.html", {"form": form})


def verify_email(request, token):
    profile = (
        UserProfile.objects.filter(email_verification_token=token).first()
        if token
        else None
    )
    if profile is None:
        return render(request, "accounts/email_verified.html", {"success": False})

    sent_at = profile.email_verification_sent_at
    if sent_at and timezone.now() - sent_at > EMAIL_VERIFICATION_TTL:
        return render(request, "accounts/email_verified.html", {"success": False})

    profile.email_verified = True
    profile.email_verification_token = ""
    profile.email_verification_sent_at = None
    profile.save()
    return render(request, "accounts/email_verified.html", {"success": True})


@login_required
def resend_verification_email(request):
    profile = request.user.profile

    if profile.email_verified:
        return redirect("accounts:profile")

    if profile.email_verification_sent_at:
        if timezone.now() - profile.email_verification_sent_at < EMAIL_RESEND_COOLDOWN:
            return render(request, "accounts/email_verification_wait.html")

    if not send_verification_email(request, request.user):
        return redirect("accounts:profile")

    return render(
        request,
        "accounts/email_verification_sent.html",
        {"email": request.user.email},
    )
