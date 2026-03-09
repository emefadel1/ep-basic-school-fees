from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session as AuthSession
from django.test import TestCase
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.audit.services import run_retention_cleanup
from apps.notifications.models import Notification, NotificationType

User = get_user_model()


class RetentionCleanupTests(TestCase):
    def test_cleanup_removes_old_read_notifications_and_expired_sessions(self):
        user = User.objects.create_user(username="cleanup_user", password="pass12345", role=User.Role.BURSAR)
        old_notification = Notification.objects.create(
            user=user,
            title="Old",
            message="Old message",
            notification_type=NotificationType.SESSION_APPROVED,
            is_read=True,
            read_at=timezone.now() - timedelta(days=120),
        )
        Notification.objects.create(
            user=user,
            title="Unread",
            message="Keep",
            notification_type=NotificationType.SESSION_APPROVED,
        )

        session_store = SessionStore()
        session_store["user_id"] = user.id
        session_store.create()
        AuthSession.objects.filter(session_key=session_store.session_key).update(expire_date=timezone.now() - timedelta(days=1))

        result = run_retention_cleanup(user=user)

        self.assertEqual(result["notifications_deleted"], 1)
        self.assertEqual(result["expired_sessions_deleted"], 1)
        self.assertFalse(Notification.objects.filter(id=old_notification.id).exists())
        self.assertEqual(Notification.objects.count(), 1)
        self.assertFalse(AuthSession.objects.filter(session_key=session_store.session_key).exists())
        self.assertTrue(AuditLog.objects.filter(table_name="retention_cleanup", action=AuditLog.Action.DELETE).exists())
