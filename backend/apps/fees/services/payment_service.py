# apps/fees/services/payment_service.py

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.audit.models import AuditLog
from ..models import FeeCollection, Session, StudentArrears


class PaymentServiceError(Exception):
    pass


class PaymentService:
    """
    Service layer for payment handling.

    Covers:
    - create/update fee collections
    - unpaid marking
    - fee waivers
    - exemptions
    - receipt generation
    - arrears payments
    - audit logging
    """

    def __init__(self, session: Optional[Session] = None):
        self.session = session

    def _require_session(self) -> Session:
        if not self.session:
            raise PaymentServiceError("Session is required for this operation.")
        return self.session

    def _to_decimal(self, value) -> Decimal:
        return Decimal(str(value or "0.00"))

    def _serialize_fee_collection(self, collection: FeeCollection) -> dict:
        return {
            "id": collection.id,
            "session_id": collection.session_id,
            "school_class_id": collection.school_class_id,
            "student_id": collection.student_id,
            "pool_type": collection.pool_type,
            "expected_amount": str(collection.expected_amount),
            "amount_paid": str(collection.amount_paid),
            "status": collection.status,
            "unpaid_reason": collection.unpaid_reason,
            "receipt_number": collection.receipt_number or "",
        }

    def _serialize_arrears(self, arrears: StudentArrears) -> dict:
        return {
            "id": arrears.id,
            "student_id": arrears.student_id,
            "session_id": arrears.session_id,
            "pool_type": arrears.pool_type,
            "amount_owed": str(arrears.amount_owed),
            "amount_paid": str(arrears.amount_paid),
            "balance": str(arrears.balance),
            "status": arrears.status,
        }

    def _audit(
        self,
        *,
        action: str,
        table_name: str,
        record_id: Optional[int],
        user=None,
        previous_value: Optional[dict] = None,
        new_value: Optional[dict] = None,
        notes: str = "",
        ip_address: Optional[str] = None,
        user_agent: str = "",
    ):
        AuditLog.log_action(
            action=action,
            table_name=table_name,
            record_id=record_id,
            user=user,
            previous_value=previous_value,
            new_value=new_value,
            notes=notes,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @transaction.atomic
    def record_collection(
        self,
        *,
        school_class,
        student,
        pool_type: str,
        expected_amount,
        amount_paid=Decimal("0.00"),
        recorded_by=None,
        unpaid_reason: str = "",
        unpaid_notes: str = "",
        session: Optional[Session] = None,
        ip_address: Optional[str] = None,
        user_agent: str = "",
    ) -> FeeCollection:
        """
        Create or update a fee collection record.

        Status is resolved automatically by the model.
        """
        session = session or self._require_session()

        collection = FeeCollection.objects.filter(
            session=session,
            student=student,
            pool_type=pool_type,
        ).first()

        previous_value = self._serialize_fee_collection(collection) if collection else None

        if collection is None:
            collection = FeeCollection(
                session=session,
                school_class=school_class,
                student=student,
                pool_type=pool_type,
            )

        collection.expected_amount = self._to_decimal(expected_amount)
        collection.amount_paid = self._to_decimal(amount_paid)
        collection.unpaid_reason = unpaid_reason
        collection.unpaid_notes = unpaid_notes
        collection.recorded_by = recorded_by

        collection.save()

        self._audit(
            action=AuditLog.Action.CREATE if previous_value is None else AuditLog.Action.UPDATE,
            table_name="fee_collections",
            record_id=collection.id,
            user=recorded_by,
            previous_value=previous_value,
            new_value=self._serialize_fee_collection(collection),
            notes="Fee collection recorded",
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return collection

    @transaction.atomic
    def mark_unpaid(
        self,
        *,
        collection: FeeCollection,
        reason: str,
        notes: str = "",
        user=None,
        ip_address: Optional[str] = None,
        user_agent: str = "",
    ) -> FeeCollection:
        previous_value = self._serialize_fee_collection(collection)

        collection.amount_paid = Decimal("0.00")
        collection.unpaid_reason = reason
        collection.unpaid_notes = notes
        collection.status = FeeCollection.PaymentStatus.UNPAID
        collection.recorded_by = user
        collection.save()

        self._audit(
            action=AuditLog.Action.UPDATE,
            table_name="fee_collections",
            record_id=collection.id,
            user=user,
            previous_value=previous_value,
            new_value=self._serialize_fee_collection(collection),
            notes=notes or f"Marked unpaid: {reason}",
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return collection

    @transaction.atomic
    def waive_fee(
        self,
        *,
        collection: FeeCollection,
        approved_by,
        reason: str,
        ip_address: Optional[str] = None,
        user_agent: str = "",
    ) -> FeeCollection:
        """
        Mark a fee collection as WAIVED.

        The model preserves WAIVED in resolve_status().
        """
        if not reason:
            raise ValidationError("Waiver reason is required.")

        previous_value = self._serialize_fee_collection(collection)

        collection.amount_paid = Decimal("0.00")
        collection.status = FeeCollection.PaymentStatus.WAIVED
        collection.waiver_approved_by = approved_by
        collection.waiver_reason = reason
        collection.unpaid_reason = ""
        collection.unpaid_notes = ""
        collection.recorded_by = approved_by
        collection.save()

        self._audit(
            action=AuditLog.Action.FEE_WAIVER,
            table_name="fee_collections",
            record_id=collection.id,
            user=approved_by,
            previous_value=previous_value,
            new_value=self._serialize_fee_collection(collection),
            notes=reason,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return collection

    @transaction.atomic
    def mark_exempt(
        self,
        *,
        collection: FeeCollection,
        user=None,
        notes: str = "",
        ip_address: Optional[str] = None,
        user_agent: str = "",
    ) -> FeeCollection:
        """
        Mark a student as EXEMPT for this session/pool.

        Assumes exemption eligibility has been checked elsewhere.
        """
        previous_value = self._serialize_fee_collection(collection)

        collection.amount_paid = Decimal("0.00")
        collection.status = FeeCollection.PaymentStatus.EXEMPT
        collection.unpaid_reason = ""
        collection.unpaid_notes = ""
        collection.recorded_by = user
        collection.save()

        self._audit(
            action=AuditLog.Action.UPDATE,
            table_name="fee_collections",
            record_id=collection.id,
            user=user,
            previous_value=previous_value,
            new_value=self._serialize_fee_collection(collection),
            notes=notes or "Fee marked exempt",
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return collection

    @transaction.atomic
    def generate_receipt(
        self,
        *,
        collection: FeeCollection,
        user=None,
        ip_address: Optional[str] = None,
        user_agent: str = "",
    ) -> str:
        """
        Generate a receipt number for a paid collection.
        """
        previous_value = self._serialize_fee_collection(collection)
        receipt_number = collection.generate_receipt()

        collection.refresh_from_db()

        self._audit(
            action=AuditLog.Action.CREATE,
            table_name="receipts",
            record_id=collection.id,
            user=user,
            previous_value=previous_value,
            new_value=self._serialize_fee_collection(collection),
            notes=f"Receipt generated: {receipt_number}",
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return receipt_number

    @transaction.atomic
    def record_arrears_payment(
        self,
        *,
        arrears: StudentArrears,
        amount,
        recorded_by=None,
        ip_address: Optional[str] = None,
        user_agent: str = "",
    ) -> StudentArrears:
        """
        Record a payment against arrears and audit it.
        """
        payment_amount = self._to_decimal(amount)

        if payment_amount <= Decimal("0.00"):
            raise ValidationError("Arrears payment amount must be greater than zero.")

        previous_value = self._serialize_arrears(arrears)

        arrears.record_payment(payment_amount, recorded_by=recorded_by)
        arrears.refresh_from_db()

        self._audit(
            action=AuditLog.Action.ARREARS_PAYMENT,
            table_name="student_arrears",
            record_id=arrears.id,
            user=recorded_by,
            previous_value=previous_value,
            new_value=self._serialize_arrears(arrears),
            notes=f"Arrears payment recorded: {payment_amount}",
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return arrears

    @transaction.atomic
    def get_or_create_collection(
        self,
        *,
        school_class,
        student,
        pool_type: str,
        expected_amount,
        recorded_by=None,
        session: Optional[Session] = None,
    ) -> FeeCollection:
        """
        Convenience method for creating an EXPECTED collection row if missing.
        """
        session = session or self._require_session()

        collection, created = FeeCollection.objects.get_or_create(
            session=session,
            student=student,
            pool_type=pool_type,
            defaults={
                "school_class": school_class,
                "expected_amount": self._to_decimal(expected_amount),
                "amount_paid": Decimal("0.00"),
                "recorded_by": recorded_by,
            },
        )

        if created:
            collection.save()

        return collection