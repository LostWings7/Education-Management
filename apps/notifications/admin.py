from django.contrib import admin
from .models import Notification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'notification_type', 'priority', 'title', 'is_read', 'created_at']
    list_filter = ['priority', 'notification_type', 'is_read', 'created_at']
    search_fields = ['recipient__email', 'title', 'message', 'event_hash']
    readonly_fields = ['created_at', 'updated_at', 'event_hash', 'read_at']


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'digest_frequency', 'enable_academic_alerts', 'enable_attendance_warnings']
    search_fields = ['user__email']
