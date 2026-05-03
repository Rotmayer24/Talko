from django.shortcuts import render, get_object_or_404
from messages.models import Chat


def index(request):
    if not request.user.is_authenticated:
        return render(request, "welcome.html")
    
    chats = Chat.objects.filter(users=request.user).order_by("-created_at")
    
    active_chat_id = request.GET.get("chat")
    active_chat = None
    messages = []
    
    if active_chat_id:
        active_chat = get_object_or_404(Chat, id=active_chat_id, users=request.user)
        messages = active_chat.messages.select_related("sender").all()
    
    return render(
        request,
        "home.html",
        {
            "chats": chats,
            "active_chat": active_chat,
            "messages": messages,
        },
    )


def login(request):
    return render(request, "accounts/login.html")


def register(request):
    return render(request, "accounts/register.html")
