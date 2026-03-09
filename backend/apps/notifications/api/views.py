from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.api.serializers import NotificationBulkReadSerializer, NotificationReadSerializer, NotificationSerializer
from apps.notifications.models import Notification
from apps.notifications.services import get_unread_count, mark_all_as_read, mark_as_read, notification_queryset_for_user

class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        params = self.request.query_params
        queryset = notification_queryset_for_user(self.request.user, target_user_id=params.get('user_id'), include_all=params.get('audit') == 'true')
        if params.get('notification_type'):
            queryset = queryset.filter(notification_type=params['notification_type'])
        if params.get('channel'):
            queryset = queryset.filter(channel=params['channel'])
        if params.get('priority'):
            queryset = queryset.filter(priority=params['priority'])
        if params.get('is_read') in {'true', 'false'}:
            queryset = queryset.filter(is_read=params['is_read'] == 'true')
        return queryset.order_by('-created_at')

class NotificationUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response({'unread_count': get_unread_count(request.user)})

class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id, *args, **kwargs):
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        return Response(NotificationReadSerializer(mark_as_read(notification)).data)

class NotificationMarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        updated_count = mark_all_as_read(request.user)
        return Response(NotificationBulkReadSerializer({'updated_count': updated_count}).data)
