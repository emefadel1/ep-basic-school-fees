# apps/fees/tests/test_service_audit.py

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from apps.audit.models import AuditLog
from apps.fees.models import Session
from apps.fees.services.distribution import DistributionResult, FeeDistributionEngine
from apps.fees.services.session_service import SessionService
from apps.fees.services.validators import ValidationResult


class SessionServiceAuditTests(TestCase):
    def test_approve_creates_audit_log(self):
        session = Session.objects.create(
            date=date.today(),
            session_type=Session.SessionType.REGULAR,
            status=Session.Status.PENDING_APPROVAL,
        )

        service = SessionService(session=session)
        service.approve(
            user=None,
            notes="Approved after verification",
            ip_address="127.0.0.1",
            user_agent="unit-test",
        )

        audit = AuditLog.objects.get(
            action=AuditLog.Action.APPROVAL,
            table_name="sessions",
            record_id=session.id,
        )

        self.assertEqual(audit.new_value["status"], Session.Status.APPROVED)
        self.assertEqual(audit.new_value["approval_notes"], "Approved after verification")
        self.assertEqual(audit.notes, "Approved after verification")
        self.assertEqual(audit.ip_address, "127.0.0.1")
        self.assertEqual(audit.user_agent, "unit-test")

    def test_unlock_creates_audit_log(self):
        session = Session.objects.create(
            date=date.today(),
            session_type=Session.SessionType.REGULAR,
            status=Session.Status.LOCKED,
            unlock_count=0,
        )

        service = SessionService(session=session)
        service.unlock(
            user=None,
            reason="Needed correction after payment reconciliation.",
            ip_address="127.0.0.1",
            user_agent="unit-test",
        )

        audit = AuditLog.objects.get(
            action=AuditLog.Action.UNLOCK,
            table_name="sessions",
            record_id=session.id,
        )

        self.assertEqual(audit.new_value["status"], Session.Status.DISTRIBUTED)
        self.assertEqual(
            audit.new_value["last_unlock_reason"],
            "Needed correction after payment reconciliation.",
        )
        self.assertEqual(audit.notes, "Needed correction after payment reconciliation.")


class DistributionServiceAuditTests(TestCase):
    @patch("apps.fees.services.distribution.DistributionValidator.validate")
    @patch("apps.fees.services.distribution.PoolSummary.objects.update_or_create")
    @patch("apps.fees.services.distribution.Distribution.objects.create")
    def test_save_distribution_result_creates_audit_log(
        self,
        mock_distribution_create,
        mock_update_or_create,
        mock_validate,
    ):
        session = Session.objects.create(
            date=date.today(),
            session_type=Session.SessionType.REGULAR,
            status=Session.Status.APPROVED,
        )

        engine = FeeDistributionEngine(session=session)

        result = DistributionResult(
            pool_code="GEN_STUDIES",
            total_collected=Decimal("1000.00"),
            school_retention=Decimal("100.00"),
            administrative_fee=Decimal("0.00"),
            distributable_amount=Decimal("900.00"),
            staff_shares={
                1: Decimal("450.00"),
                2: Decimal("450.00"),
            },
            special_shares={},
            staff_metadata={
                1: {"attendance_status": "PRESENT", "attendance_weight": "1.0"},
                2: {"attendance_status": "PRESENT", "attendance_weight": "1.0"},
            },
        )

        mock_validate.return_value = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
        )

        fake_pool_summary = SimpleNamespace(
            id=999,
            session_id=session.id,
            pool_type="GEN_STUDIES",
            total_expected=Decimal("1000.00"),
            total_collected=Decimal("1000.00"),
            total_outstanding=Decimal("0.00"),
            school_retention=Decimal("100.00"),
            administrative_fee=Decimal("0.00"),
            total_distributed=Decimal("900.00"),
            recipient_count=2,
        )
        mock_update_or_create.return_value = (fake_pool_summary, True)

        engine.save_distribution_result(
            result,
            user=None,
            ip_address="127.0.0.1",
            user_agent="unit-test",
        )

        audit = AuditLog.objects.get(
            action=AuditLog.Action.DISTRIBUTION,
            table_name="pool_summaries",
            record_id=999,
        )

        self.assertEqual(audit.new_value["pool_code"], "GEN_STUDIES")
        self.assertEqual(audit.new_value["recipient_count"], 2)
        self.assertEqual(audit.new_value["total_distributed"], "900.00")
        self.assertEqual(audit.ip_address, "127.0.0.1")
        self.assertEqual(audit.user_agent, "unit-test")
        self.assertIn("Distribution saved for pool GEN_STUDIES", audit.notes)
        self.assertTrue(mock_distribution_create.called)