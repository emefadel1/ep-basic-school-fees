from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.fees.models import Session
from apps.notifications.models import Notification, NotificationPriority, NotificationType
from apps.notifications.services import create_notification, notify_users

User = get_user_model()

def make_user(username, role, **extra):
    defaults = {'password': 'password123', 'email': f'{username}@example.com', 'role': role}
    defaults.update(extra)
    return User.objects.create_user(username=username, **defaults)

class NotificationServiceTests(TestCase):
    def test_creates_in_app_notification(self):
        user = make_user('teacher1', User.Role.TEACHER)
        notification = create_notification(user, 'Hello', 'World', NotificationType.SESSION_APPROVED, priority=NotificationPriority.HIGH, metadata={'session_id': 1})
        self.assertEqual(Notification.objects.count(), 1 )
        self.assertEqual(notification.user, user)
        self.assertEqual(notification.metadata['session_id'], 1 )
        self.assertFalse(notification.is_read)

    @patch('apps.notifications.services.async_task')
    def test_queues_email_task(self, async_task_mock):
        user = make_user('bursar1', User.Role.BURSAR)
        notify_users([user], 'Session submitted', 'Please review.', NotificationType.SESSION_SUBMITTED, send_email=True)
        async_task_mock.assert_called_once()
        task_name, subject, message, recipient_list = async_task_mock.call_args.args
        self.assertEqual(task_name, 'apps.notifications.tasks.send_notification_email')
        self.assertEqual(subject, 'Session submitted')
        self.assertEqual(message, 'Please review.')
        self.assertEqual(recipient_list, [user.email])

    def test_session_approval_and_rejection_create_notifications(self):
        headteacher = make_user('headteacher1', User.Role.HEADTEACHER)
        bursar = make_user('bursar2', User.Role.BURSAR)
        submitter = make_user('teacher2', User.Role.TEACHER)
        approved_session = Session.objects.create(date=timezone.now().date(), session_type=Session.SessionType.REGULAR, status=Session.Status.PENDING_APPROVAL, submitted_by=submitter, submitted_at=timezone.now())
        approved_session.approve(user=bursar, notes='Looks good')
        approval_notification = Notification.objects.get(user=headteacher, notification_type=NotificationType.SESSION_APPROVED)
        self.assertIn('approved', approval_notification.message.lower())
        rejected_session = Session.objects.create(date=timezone.now().date() - timezone.timedelta(days=1), session_type=Session.SessionType.REGULAR, status=Session.Status.PENDING_APPROVAL, submitted_by=submitter, submitted_at=timezone.now())
        rejected_session.reject(user=bursar, reason='Totals do not balance')
        rejected_notifications = Notification.objects.filter(notification_type=NotificationType.SESSION_REJECTED)
        self.assertEqual(rejected_notifications.count(), 2 )
        self.assertTrue(rejected_notifications.filter(user=headteacher).exists())
        self.assertTrue(rejected_notifications.filter(user=submitter).exists())
