# apps/fees/tests/test_models_and_session.py

from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.fees.models import FeeCollection, Session


class SessionModelTests(TestCase):
    def test_session_cannot_be_in_future(self):
        session = Session(
            date=timezone.now().date() + timedelta(days=1),
            session_type=Session.SessionType.REGULAR,
        )

        with self.assertRaises(ValidationError):
            session.full_clean()

    def test_session_lifecycle(self):
        session = Session.objects.create(
            date=timezone.now().date(),
            session_type=Session.SessionType.REGULAR,
        )

        session.open_session(user=None)
        self.assertEqual(session.status, Session.Status.OPEN)

        session.submit_for_approval()
        self.assertEqual(session.status, Session.Status.PENDING_APPROVAL)

        session.approve(user=None, notes="ok")
        self.assertEqual(session.status, Session.Status.APPROVED)

        session.mark_distributed()
        self.assertEqual(session.status, Session.Status.DISTRIBUTED)

        session.lock(user=None)
        self.assertEqual(session.status, Session.Status.LOCKED)

        session.unlock(user=None, reason="Needed correction after payout reconciliation.")
        self.assertEqual(session.status, Session.Status.DISTRIBUTED)

    def test_rejected_session_can_reopen(self):
        session = Session.objects.create(
            date=timezone.now().date(),
            session_type=Session.SessionType.REGULAR,
        )

        session.open_session(user=None)
        session.submit_for_approval()
        session.reject(user=None, reason="Wrong totals")
        self.assertEqual(session.status, Session.Status.REJECTED)

        session.reopen(user=None)
        self.assertEqual(session.status, Session.Status.OPEN)


class FeeCollectionModelTests(TestCase):
    def test_resolve_status_paid_full(self):
        item = FeeCollection(
            expected_amount=Decimal("10.00"),
            amount_paid=Decimal("10.00"),
            status=FeeCollection.PaymentStatus.EXPECTED,
        )
        self.assertEqual(item.resolve_status(), FeeCollection.PaymentStatus.PAID_FULL)

    def test_resolve_status_paid_partial(self):
        item = FeeCollection(
            expected_amount=Decimal("10.00"),
            amount_paid=Decimal("4.00"),
            status=FeeCollection.PaymentStatus.EXPECTED,
        )
        self.assertEqual(item.resolve_status(), FeeCollection.PaymentStatus.PAID_PARTIAL)

    def test_resolve_status_unpaid(self):
        item = FeeCollection(
            expected_amount=Decimal("10.00"),
            amount_paid=Decimal("0.00"),
            unpaid_reason=FeeCollection.UnpaidReason.NO_MONEY,
            status=FeeCollection.PaymentStatus.EXPECTED,
        )
        self.assertEqual(item.resolve_status(), FeeCollection.PaymentStatus.UNPAID)

    def test_resolve_status_keeps_exempt(self):
        item = FeeCollection(
            expected_amount=Decimal("10.00"),
            amount_paid=Decimal("0.00"),
            status=FeeCollection.PaymentStatus.EXEMPT,
        )
        self.assertEqual(item.resolve_status(), FeeCollection.PaymentStatus.EXEMPT)

    def test_clean_requires_unpaid_reason(self):
        item = FeeCollection(
            expected_amount=Decimal("10.00"),
            amount_paid=Decimal("0.00"),
            status=FeeCollection.PaymentStatus.UNPAID,
        )

        with self.assertRaises(ValidationError):
            item.clean()

    def test_clean_rejects_amount_paid_above_expected(self):
        item = FeeCollection(
            expected_amount=Decimal("10.00"),
            amount_paid=Decimal("12.00"),
            status=FeeCollection.PaymentStatus.PAID_FULL,
        )

        with self.assertRaises(ValidationError):
            item.clean()