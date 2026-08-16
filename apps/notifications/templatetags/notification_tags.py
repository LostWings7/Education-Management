from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def unread_notifications_count(context):
    request = context.get('request')
    if request and request.user.is_authenticated:
        return request.user.notifications.filter(is_read=False).count()
    return 0


@register.simple_tag(takes_context=True)
def recent_notifications(context, limit=5):
    request = context.get('request')
    if request and request.user.is_authenticated:
        return request.user.notifications.all()[:limit]
    return []
