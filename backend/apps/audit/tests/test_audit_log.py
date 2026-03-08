# apps/audit/tests/test_audit_log.py

from django.test import TestCase

from apps.audit.models import AuditLog


class AuditLogModelTests(TestCase):
    def test_log_action_creates_audit_row(self):
        log = AuditLog.log_action(
            action=AuditLog.Action.CREATE,
            table_name="sessions",
            record_id=1,
            previous_value=None,
            new_value={"status": "DRAFT"},
            notes="Session created",
            ip_address="127.0.0.1",
            user_agent="pytest-agent",
        )

        self.assertIsNotNone(log.id)
        self.assertEqual(log.action, AuditLog.Action.CREATE)
        self.assertEqual(log.table_name, "sessions")
        self.assertEqual(log.record_id, 1)
        self.assertEqual(log.new_value["status"], "DRAFT")
        self.assertEqual(log.notes, "Session created")
        self.assertEqual(log.ip_address, "127.0.0.1")

    def test_string_representation(self):
        log = AuditLog.objects.create(
            action=AuditLog.Action.UPDATE,
            table_name="fee_collections",
            record_id=12,
        )

        self.assertIn("UPDATE", str(log))
        self.assertIn("fee_collections", str(log))