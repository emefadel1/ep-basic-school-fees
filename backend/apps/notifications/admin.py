from django.contrib import admin

from apps.notifications.models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'notification_type', 'channel', 'priority', 'is_read', 'created_at']
    list_filter = ['notification_type', 'channel', 'priority', 'is_read']
    search_fields = ['user__username', 'user__email', 'title', 'message']
    ordering = ['-created_at']
