from rest_framework import serializers

from apps.notifications.models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'user_name', 'title', 'message', 'notification_type',
            'channel', 'priority', 'is_read', 'read_at', 'related_model',
            'related_id', 'action_url', 'metadata', 'created_at',
        ]
        read_only_fields = fields

    def get_user_name(self, obj):
        return obj.user.get_full_name() if hasattr(obj.user, 'get_full_name') else obj.user.username

class NotificationReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'is_read', 'read_at']
        read_only_fields = fields

class NotificationBulkReadSerializer(serializers.Serializer):
    updated_count = serializers.IntegerField(read_only=True)
