from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.audit.models import AuditLog

User = get_user_model()


@override_settings(ROOT_URLCONF="config.api_urls")
class AuditApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.bursar = User.objects.create_user(username="bursar_audit", password="pass12345", role=User.Role.BURSAR)
        self.teacher = User.objects.create_user(username="teacher_audit", password="pass12345", role=User.Role.TEACHER)
        AuditLog.log_action(action=AuditLog.Action.APPROVAL, table_name="sessions", record_id=1, user=self.bursar, notes="Approved")
        AuditLog.log_action(action=AuditLog.Action.REJECTION, table_name="sessions", record_id=2, user=self.teacher, notes="Rejected")

    def test_bursar_can_list_audit_logs(self):
        self.client.force_authenticate(self.bursar)
        response = self.client.get("/audit/?action=APPROVAL")
        self.assertEqual(response.status_code, 200)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["action"], AuditLog.Action.APPROVAL)

    def test_non_audit_user_is_denied(self):
        self.client.force_authenticate(self.teacher)
        response = self.client.get("/audit/")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["error"]["status"], 403)
