from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

@override_settings(
    ROOT_URLCONF='config.urls',
    DEBUG=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class HealthEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_health_endpoint_is_public_and_structured(self):
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(response.data['status'], ['healthy', 'degraded'])
        self.assertEqual(response.data['service'], 'ep-basic-school-fees')
        self.assertIn('timestamp', response.data)
        self.assertIn('database', response.data['checks'])
        self.assertIn('cache', response.data['checks'])
        self.assertIn('disk', response.data['checks'])

    @patch('apps.users.health_views._check_cache')
    def test_health_endpoint_returns_degraded_when_cache_check_fails(self, mock_check_cache):
        mock_check_cache.return_value = {'service': 'cache', 'status': 'degraded', 'details': 'Cache unavailable'}
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'degraded')

    @patch('apps.users.health_views._check_database')
    def test_health_endpoint_returns_503_on_database_failure(self, mock_check_database):
        mock_check_database.return_value = {'service': 'database', 'status': 'unhealthy', 'details': 'Database unavailable'}
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data['status'], 'unhealthy')

    def test_metrics_requires_privileged_user(self):
        response = self.client.get('/metrics/')
        self.assertIn(response.status_code, [401, 403])

    def test_metrics_returns_counts_for_audit_viewer(self):
        user = get_user_model().objects.create_user(username='bursar', password='testpass123', role='BURSAR')
        self.client.force_authenticate(user=user)
        response = self.client.get('/metrics/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('users', response.data)
        self.assertIn('sessions', response.data)
        self.assertIn('audit', response.data)

