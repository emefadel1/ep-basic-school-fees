from django.test import TestCase, override_settings
from rest_framework.test import APIClient


@override_settings(ROOT_URLCONF="core.tests.urls")
class ExceptionHandlerTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def assert_error_shape(self, response, code, status_code):
        self.assertEqual(response.status_code, status_code)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["error"]["code"], code)
        self.assertEqual(response.data["error"]["status"], status_code)
        self.assertIn("message", response.data["error"])
        self.assertIn("timestamp", response.data)
        self.assertEqual(response.data["context"]["method"], "GET")
        self.assertTrue(response.data["context"]["path"].startswith("/exception-probe/"))

    def test_custom_app_exception_is_normalized(self):
        response = self.client.get("/exception-probe/app/")
        self.assert_error_shape(response, "session_locked", 423)
        self.assertEqual(response.data["error"]["extra"]["session_id"], 123)

    def test_django_validation_error_is_normalized(self):
        response = self.client.get("/exception-probe/django/")
        self.assert_error_shape(response, "validation_error", 400)
        self.assertEqual(response.data["error"]["errors"]["field"][0], "Invalid field")

    def test_drf_validation_error_is_normalized(self):
        response = self.client.get("/exception-probe/drf/")
        self.assert_error_shape(response, "validation_error", 400)
        self.assertEqual(response.data["error"]["errors"]["field"][0], "This field is required.")

    def test_integrity_error_is_normalized(self):
        response = self.client.get("/exception-probe/integrity/")
        self.assert_error_shape(response, "integrity_error", 409)

    def test_unexpected_error_is_normalized(self):
        response = self.client.get("/exception-probe/unexpected/")
        self.assert_error_shape(response, "internal_server_error", 500)
        self.assertIn("extra", response.data["error"])
