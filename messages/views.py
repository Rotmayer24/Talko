from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, JsonResponse
from django.contrib.auth.models import User
from accounts.models import get_friends, Notification

from .models import Chat, Message


def create_notification(user, notification_type, title, message, link=''):
    Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link
    )


@login_required
def users_list(request):
    users = User.objects.exclude(id=request.user.id)
    return render(request, "accounts/users_list.html", {"users": users})


@login_required
def home(request):
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


@require_POST
@login_required
def send_message(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id, users=request.user)

    text = request.POST.get("text")
    if text:
        Message.objects.create(chat=chat, sender=request.user, content=text)

    return redirect(f"/?chat={chat.id}")


@login_required
def create_group(request):
    if request.method == 'POST':
        group_name = request.POST.get('group_name')
        selected_users = request.POST.getlist('users')
        
        if not group_name:
            return redirect('messages:create_group')
        
        group = Chat.objects.create(
            is_group=True,
            group_name=group_name,
            created_by=request.user
        )
        
        group.users.add(request.user)
        for user_id in selected_users:
            try:
                user = User.objects.get(id=user_id)
                group.users.add(user)
                create_notification(
                    user,
                    'group_invite',
                    'Added to Group',
                    f'{request.user.username} added you to {group_name}',
                    f'/?chat={group.id}'
                )
            except User.DoesNotExist:
                pass
        
        group.admins.add(request.user)
        
        return redirect(f'/?chat={group.id}')
    
    friends = get_friends(request.user)
    return render(request, 'messages/create_group.html', {'friends': friends})


@login_required
def join_group(request, group_id):
    group = get_object_or_404(Chat, id=group_id, is_group=True)
    
    if request.user not in group.users.all():
        group.users.add(request.user)
    
    return redirect(f'/?chat={group.id}')


@login_required
def leave_group(request, group_id):
    group = get_object_or_404(Chat, id=group_id, is_group=True, users=request.user)
    
    group.users.remove(request.user)
    
    if group.created_by == request.user and group.users.count() > 0:
        new_admin = group.users.first()
        group.created_by = new_admin
        if new_admin not in group.admins.all():
            group.admins.add(new_admin)
        group.save()
    elif group.users.count() == 0:
        group.delete()
    
    return redirect('/')


@login_required
def group_settings(request, group_id):
    group = get_object_or_404(Chat, id=group_id, is_group=True)
    
    if request.user not in group.admins.all():
        return redirect('/')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_info':
            group_name = request.POST.get('group_name')
            if group_name:
                group.group_name = group_name
            
            if 'group_avatar' in request.FILES:
                group.group_avatar = request.FILES['group_avatar']
            
            group.save()
        
        elif action == 'add_member':
            user_id = request.POST.get('user_id')
            try:
                user = User.objects.get(id=user_id)
                if user not in group.users.all():
                    group.users.add(user)
                    create_notification(
                        user,
                        'group_invite',
                        'Added to Group',
                        f'{request.user.username} added you to {group.group_name}',
                        f'/?chat={group.id}'
                    )
            except User.DoesNotExist:
                pass
        
        elif action == 'remove_member':
            user_id = request.POST.get('user_id')
            try:
                user = User.objects.get(id=user_id)
                if user != group.created_by:
                    group.users.remove(user)
                    group.admins.remove(user)
            except User.DoesNotExist:
                pass
        
        elif action == 'promote_admin':
            user_id = request.POST.get('user_id')
            try:
                user = User.objects.get(id=user_id)
                if user in group.users.all():
                    group.admins.add(user)
            except User.DoesNotExist:
                pass
        
        elif action == 'demote_admin':
            user_id = request.POST.get('user_id')
            try:
                user = User.objects.get(id=user_id)
                if user != group.created_by:
                    group.admins.remove(user)
            except User.DoesNotExist:
                pass
        
        return redirect('messages:group_settings', group_id=group_id)
    
    members = group.users.all()
    admins = group.admins.all()
    friends = get_friends(request.user).exclude(id__in=members.values_list('id', flat=True))
    
    return render(request, 'messages/group_settings.html', {
        'group': group,
        'members': members,
        'admins': admins,
        'friends': friends,
        'is_creator': request.user == group.created_by
    })


@require_POST
@login_required
def upload_file(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id, users=request.user)
    
    file = request.FILES.get('file')
    image = request.FILES.get('image')
    
    if image:
        if image.size > 10 * 1024 * 1024:
            return JsonResponse({'error': 'Image too large (max 10MB)'}, status=400)
        
        message = Message.objects.create(
            chat=chat,
            sender=request.user,
            message_type='image',
            image=image,
            file_name=image.name,
            file_size=image.size
        )
        
        return JsonResponse({
            'status': 'ok',
            'message_id': message.id,
            'type': 'image',
            'url': message.image.url
        })
    
    elif file:
        if file.size > 10 * 1024 * 1024:
            return JsonResponse({'error': 'File too large (max 10MB)'}, status=400)
        
        message = Message.objects.create(
            chat=chat,
            sender=request.user,
            message_type='file',
            file=file,
            file_name=file.name,
            file_size=file.size
        )
        
        return JsonResponse({
            'status': 'ok',
            'message_id': message.id,
            'type': 'file',
            'url': message.file.url,
            'name': file.name,
            'size': file.size
        })
    
    return JsonResponse({'error': 'No file provided'}, status=400)
