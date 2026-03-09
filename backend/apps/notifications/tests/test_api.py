from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.notifications.models import Notification, NotificationType

User = get_user_model()

def make_user(username, role, **extra):
    defaults = {'password': 'password123', 'email': f'{username}@example.com', 'role': role}
    defaults.update(extra)
    return User.objects.create_user(username=username, **defaults)

class NotificationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user('teacher3', User.Role.TEACHER)
        self.other_user = make_user('teacher4', User.Role.TEACHER)
        self.client.force_authenticate(self.user)

    def _create_notification(self, user, **overrides):
        payload = {'user': user, 'title': 'Notice', 'message': 'Check this', 'notification_type': NotificationType.SESSION_APPROVED}
        payload.update(overrides)
        return Notification.objects.create(**payload)

    def test_user_only_sees_own_notifications(self):
        self._create_notification(self.user, title='Mine')
        self._create_notification(self.other_user, title='Other')
        response = self.client.get('/api/v1/notifications/')
        self.assertEqual(response.status_code, 200 )
        data = response.data.get('results', response.data)
        self.assertEqual(len(data), 1 )
        self.assertEqual(data[0]['title'], 'Mine')

    def test_mark_read_works(self):
        notification = self._create_notification(self.user)
        response = self.client.post(f'/api/v1/notifications/{notification.id}/mark-read/')
        self.assertEqual(response.status_code, 200 )
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)

    def test_unread_count_works(self):
        self._create_notification(self.user)
        self._create_notification(self.user, is_read=True)
        self._create_notification(self.other_user)
        response = self.client.get('/api/v1/notifications/unread-count/')
        self.assertEqual(response.status_code, 200 )
        self.assertEqual(response.data['unread_count'], 1 )

    def test_mark_all_read_marks_only_current_user_notifications(self):
        own_notification = self._create_notification(self.user)
        other_notification = self._create_notification(self.other_user)
        response = self.client.post('/api/v1/notifications/mark-all-read/')
        self.assertEqual(response.status_code, 200 )
        self.assertEqual(response.data['updated_count'], 1 )
        own_notification.refresh_from_db()
        other_notification.refresh_from_db()
        self.assertTrue(own_notification.is_read)
        self.assertFalse(other_notification.is_read)
