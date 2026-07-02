def notifications_count(request):
    if request.user.is_authenticated:
        from .models import Notification
        count = Notification.objects.filter(
            user=request.user, 
            is_read=False
        ).count()
        return {'unread_notifications_count': count}
    return {'unread_notifications_count': 0}

# Theming is handled entirely client-side via per-theme stylesheets in
# static/css/themes/ and localStorage (see templates/index.html). No server
# state is involved.
