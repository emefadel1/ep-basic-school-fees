from datetime import timedelta

from django.conf import settings
from django.contrib.sessions.models import Session as AuthSession
from django.utils import timezone

from apps.notifications.models import Notification

from .models import AuditLog


def run_retention_cleanup(*, user=None):
    notification_cutoff = timezone.now() - timedelta(days=getattr(settings, "READ_NOTIFICATION_RETENTION_DAYS", 90))

    notification_qs = Notification.objects.filter(is_read=True, read_at__lt=notification_cutoff)
    notifications_deleted = notification_qs.count()
    notification_qs.delete()

    expired_session_qs = AuthSession.objects.filter(expire_date__lt=timezone.now())
    expired_sessions_deleted = expired_session_qs.count()
    expired_session_qs.delete()

    AuditLog.log_action(
        action=AuditLog.Action.DELETE,
        table_name="retention_cleanup",
        user=user,
        new_value={
            "notifications_deleted": notifications_deleted,
            "expired_sessions_deleted": expired_sessions_deleted,
            "notification_cutoff": notification_cutoff.isoformat(),
        },
        notes="Retention cleanup executed",
    )

    return {
        "notifications_deleted": notifications_deleted,
        "expired_sessions_deleted": expired_sessions_deleted,
        "notification_cutoff": notification_cutoff,
    }
