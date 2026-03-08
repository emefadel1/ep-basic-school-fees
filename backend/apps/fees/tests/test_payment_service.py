# apps/fees/tests/test_payment_service.py

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.audit.models import AuditLog
from apps.fees.models import FeeCollection, Session, StudentArrears
from apps.fees.services.payment_service import PaymentService


class DummyCollection:
    def __init__(self):
        self.id = 101
        self.session_id = 1
        self.school_class_id = 11
        self.student_id = 21
        self.pool_type = "GEN_STUDIES"
        self.expected_amount = Decimal("5.00")
        self.amount_paid = Decimal("2.00")
        self.status = FeeCollection.PaymentStatus.PAID_PARTIAL
        self.unpaid_reason = ""
        self.unpaid_notes = ""
        self.receipt_number = ""
        self.waiver_approved_by = None
        self.waiver_reason = ""
        self.recorded_by = None
        self.save_called = False

    def save(self, *args, **kwargs):
        self.save_called = True

    def generate_receipt(self):
        self.receipt_number = "EP-20260308-0001"
        return self.receipt_number

    def refresh_from_db(self):
        return None


class DummyArrears:
    def __init__(self):
        self.id = 501
        self.student_id = 21
        self.session_id = 1
        self.pool_type = "GEN_STUDIES"
        self.amount_owed = Decimal("10.00")
        self.amount_paid = Decimal("3.00")
        self.status = StudentArrears.Status.PENDING

    @property
    def balance(self):
        return self.amount_owed - self.amount_paid

    def record_payment(self, amount, recorded_by=None):
        self.amount_paid += Decimal(str(amount))
        if self.amount_paid >= self.amount_owed:
            self.amount_paid = self.amount_owed
            self.status = StudentArrears.Status.PAID
        else:
            self.status = StudentArrears.Status.PARTIAL

    def refresh_from_db(self):
        return None


class PaymentServiceTests(TestCase):
    def setUp(self):
        self.session = Session.objects.create(
            date="2026-03-08",
            session_type=Session.SessionType.REGULAR,
            status=Session.Status.OPEN,
        )
        self.service = PaymentService(session=self.session)

    def test_mark_unpaid_updates_collection_and_creates_audit_log(self):
        collection = DummyCollection()

        self.service.mark_unpaid(
            collection=collection,
            reason=FeeCollection.UnpaidReason.NO_MONEY,
            notes="Student did not bring money",
            user=None,
            ip_address="127.0.0.1",
            user_agent="unit-test",
        )

        self.assertEqual(collection.amount_paid, Decimal("0.00"))
        self.assertEqual(collection.status, FeeCollection.PaymentStatus.UNPAID)
        self.assertEqual(collection.unpaid_reason, FeeCollection.UnpaidReason.NO_MONEY)
        self.assertTrue(collection.save_called)

        audit = AuditLog.objects.get(
            action=AuditLog.Action.UPDATE,
            table_name="fee_collections",
            record_id=collection.id,
        )
        self.assertEqual(audit.new_value["status"], FeeCollection.PaymentStatus.UNPAID)
        self.assertEqual(audit.new_value["unpaid_reason"], FeeCollection.UnpaidReason.NO_MONEY)
        self.assertEqual(audit.notes, "Student did not bring money")

    def test_waive_fee_updates_collection_and_creates_audit_log(self):
        collection = DummyCollection()

        self.service.waive_fee(
            collection=collection,
            approved_by=None,
            reason="Approved hardship waiver",
            ip_address="127.0.0.1",
            user_agent="unit-test",
        )

        self.assertEqual(collection.amount_paid, Decimal("0.00"))
        self.assertEqual(collection.status, FeeCollection.PaymentStatus.WAIVED)
        self.assertEqual(collection.waiver_reason, "Approved hardship waiver")
        self.assertTrue(collection.save_called)

        audit = AuditLog.objects.get(
            action=AuditLog.Action.FEE_WAIVER,
            table_name="fee_collections",
            record_id=collection.id,
        )
        self.assertEqual(audit.new_value["status"], FeeCollection.PaymentStatus.WAIVED)
        self.assertEqual(audit.notes, "Approved hardship waiver")

    def test_waive_fee_requires_reason(self):
        collection = DummyCollection()

        with self.assertRaises(ValidationError):
            self.service.waive_fee(
                collection=collection,
                approved_by=None,
                reason="",
            )

    def test_mark_exempt_updates_collection_and_creates_audit_log(self):
        collection = DummyCollection()

        self.service.mark_exempt(
            collection=collection,
            user=None,
            notes="Student has active exemption",
            ip_address="127.0.0.1",
            user_agent="unit-test",
        )

        self.assertEqual(collection.amount_paid, Decimal("0.00"))
        self.assertEqual(collection.status, FeeCollection.PaymentStatus.EXEMPT)
        self.assertTrue(collection.save_called)

        audit = AuditLog.objects.get(
            action=AuditLog.Action.UPDATE,
            table_name="fee_collections",
            record_id=collection.id,
        )
        self.assertEqual(audit.new_value["status"], FeeCollection.PaymentStatus.EXEMPT)
        self.assertEqual(audit.notes, "Student has active exemption")

    def test_generate_receipt_creates_audit_log(self):
        collection = DummyCollection()

        receipt_number = self.service.generate_receipt(
            collection=collection,
            user=None,
            ip_address="127.0.0.1",
            user_agent="unit-test",
        )

        self.assertEqual(receipt_number, "EP-20260308-0001")

        audit = AuditLog.objects.get(
            action=AuditLog.Action.CREATE,
            table_name="receipts",
            record_id=collection.id,
        )
        self.assertEqual(audit.notes, "Receipt generated: EP-20260308-0001")
        self.assertEqual(audit.new_value["receipt_number"], "EP-20260308-0001")

    def test_record_arrears_payment_updates_arrears_and_creates_audit_log(self):
        arrears = DummyArrears()

        self.service.record_arrears_payment(
            arrears=arrears,
            amount="7.00",
            recorded_by=None,
            ip_address="127.0.0.1",
            user_agent="unit-test",
        )

        self.assertEqual(arrears.amount_paid, Decimal("10.00"))
        self.assertEqual(arrears.status, StudentArrears.Status.PAID)

        audit = AuditLog.objects.get(
            action=AuditLog.Action.ARREARS_PAYMENT,
            table_name="student_arrears",
            record_id=arrears.id,
        )
        self.assertEqual(audit.new_value["status"], StudentArrears.Status.PAID)
        self.assertEqual(audit.new_value["amount_paid"], "10.00")
        self.assertIn("Arrears payment recorded: 7.00", audit.notes)

    def test_record_arrears_payment_rejects_zero_or_negative_amount(self):
        arrears = DummyArrears()

        with self.assertRaises(ValidationError):
            self.service.record_arrears_payment(
                arrears=arrears,
                amount="0.00",
                recorded_by=None,
            )

    @patch("apps.fees.services.payment_service.FeeCollection.objects.get_or_create")
    def test_get_or_create_collection_saves_when_created(self, mock_get_or_create):
        dummy_collection = DummyCollection()
        dummy_collection.save = MagicMock()

        mock_get_or_create.return_value = (dummy_collection, True)

        result = self.service.get_or_create_collection(
            school_class=object(),
            student=object(),
            pool_type="GEN_STUDIES",
            expected_amount="5.00",
            recorded_by=None,
            session=self.session,
        )

        self.assertIs(result, dummy_collection)
        dummy_collection.save.assert_called_once()

    @patch("apps.fees.services.payment_service.FeeCollection.objects.filter")
    @patch("apps.fees.services.payment_service.FeeCollection")
    def test_record_collection_creates_and_audits_new_collection(
        self,
        mock_fee_collection_class,
        mock_filter,
    ):
        mock_filter.return_value.first.return_value = None

        dummy_collection = DummyCollection()
        mock_fee_collection_class.return_value = dummy_collection

        result = self.service.record_collection(
            school_class=object(),
            student=object(),
            pool_type="GEN_STUDIES",
            expected_amount="5.00",
            amount_paid="5.00",
            recorded_by=None,
            session=self.session,
            ip_address="127.0.0.1",
            user_agent="unit-test",
        )

        self.assertIs(result, dummy_collection)
        self.assertEqual(dummy_collection.expected_amount, Decimal("5.00"))
        self.assertEqual(dummy_collection.amount_paid, Decimal("5.00"))
        self.assertTrue(dummy_collection.save_called)

        audit = AuditLog.objects.get(
            action=AuditLog.Action.CREATE,
            table_name="fee_collections",
            record_id=dummy_collection.id,
        )
        self.assertEqual(audit.new_value["amount_paid"], "5.00")