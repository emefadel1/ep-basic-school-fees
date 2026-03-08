# apps/fees/services/session_service.py

from __future__ import annotations

from datetime import date as date_type
from typing import Dict, Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from apps.audit.models import AuditLog
from ..models import FeeCollection, PoolSummary, Session


class SessionServiceError(Exception):
    pass


class SessionService:
    """
    Service layer for session lifecycle management.

    Centralizes:
    - session creation / retrieval
    - lifecycle transitions
    - readiness checks before approval
    - readiness checks before distribution / locking
    - audit logging
    """

    def __init__(self, session: Optional[Session] = None):
        self.session = session

    def _require_session(self) -> Session:
        if not self.session:
            raise SessionServiceError("Session is required for this operation.")
        return self.session

    def _audit(
        self,
        *,
        action: str,
        session: Session,
        user=None,
        previous_value: Optional[dict] = None,
        new_value: Optional[dict] = None,
        notes: str = "",
        ip_address: Optional[str] = None,
        user_agent: str = "",
    ):
        AuditLog.log_action(
            action=action,
            table_name="sessions",
            record_id=session.id,
            user=user,
            previous_value=previous_value,
            new_value=new_value,
            notes=notes,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def _get_active_class_count(self) -> int:
        """
        Returns number of active classes expected to submit for the session.
        Adjust this if your SchoolClass model uses a different active flag.
        """
        from apps.school.models import SchoolClass

        if hasattr(SchoolClass, "is_active"):
            return SchoolClass.objects.filter(is_active=True).count()

        return SchoolClass.objects.count()

    def _get_submitted_class_count(self, session: Session) -> int:
        return (
            FeeCollection.objects
            .filter(session=session)
            .values("school_class_id")
            .distinct()
            .count()
        )

    def get_submission_status(self, session: Optional[Session] = None) -> Dict:
        """
        Returns summary of class submission completeness for a session.
        """
        session = session or self._require_session()

        submitted_class_count = self._get_submitted_class_count(session)
        expected_class_count = self._get_active_class_count()

        return {
            "session_id": session.id,
            "session_date": session.date,
            "submitted_class_count": submitted_class_count,
            "expected_class_count": expected_class_count,
            "is_complete": submitted_class_count >= expected_class_count if expected_class_count > 0 else False,
        }

    def validate_ready_for_approval(self, session: Optional[Session] = None) -> Dict:
        """
        Checks whether a session can move from OPEN to PENDING_APPROVAL.
        """
        session = session or self._require_session()

        submission = self.get_submission_status(session)
        total_collections = FeeCollection.objects.filter(session=session).count()

        errors = []

        if session.status != Session.Status.OPEN:
            errors.append("Only OPEN sessions can be submitted for approval.")

        if total_collections == 0:
            errors.append("Session has no fee collection records.")

        if not submission["is_complete"]:
            errors.append(
                f"Not all classes have submitted. "
                f"{submission['submitted_class_count']}/{submission['expected_class_count']} complete."
            )

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "meta": {
                "total_collections": total_collections,
                **submission,
            },
        }

    def validate_ready_for_distribution(self, session: Optional[Session] = None) -> Dict:
        """
        Checks whether a session can move from APPROVED to DISTRIBUTED.
        """
        session = session or self._require_session()

        errors = []

        if session.status != Session.Status.APPROVED:
            errors.append("Only APPROVED sessions can be marked as distributed.")

        pool_summary_count = PoolSummary.objects.filter(session=session).count()
        if pool_summary_count == 0:
            errors.append("No pool summaries found for this session.")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "meta": {
                "pool_summary_count": pool_summary_count,
            },
        }

    def validate_ready_for_lock(self, session: Optional[Session] = None) -> Dict:
        """
        Checks whether a session can move from DISTRIBUTED to LOCKED.
        """
        session = session or self._require_session()

        errors = []

        if session.status != Session.Status.DISTRIBUTED:
            errors.append("Only DISTRIBUTED sessions can be locked.")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
        }

    @transaction.atomic
    def get_or_create_session(
        self,
        *,
        session_date: date_type,
        session_type: str = Session.SessionType.REGULAR,
    ) -> Session:
        """
        Fetch or create a session for a given date.
        """
        session, created = Session.objects.get_or_create(
            date=session_date,
            defaults={
                "session_type": session_type,
                "status": Session.Status.DRAFT,
            },
        )
        self.session = session

        if created:
            self._audit(
                action=AuditLog.Action.CREATE,
                session=session,
                previous_value=None,
                new_value={
                    "date": str(session.date),
                    "session_type": session.session_type,
                    "status": session.status,
                },
                notes="Session created",
            )

        return session

    @transaction.atomic
    def open_session(
        self,
        *,
        user,
        session: Optional[Session] = None,
        ip_address: Optional[str] = None,
        user_agent: str = "",
    ) -> Session:
        session = session or self._require_session()
        previous_status = session.status

        session.open_session(user=user)
        self.session = session

        self._audit(
            action=AuditLog.Action.SESSION_TRANSITION,
            session=session,
            user=user,
            previous_value={"status": previous_status},
            new_value={"status": session.status},
            notes="Session opened",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return session

    @transaction.atomic
    def submit_for_approval(
        self,
        *,
        session: Optional[Session] = None,
        user=None,
        ip_address: Optional[str] = None,
        user_agent: str = "",
    ) -> Session:
        session = session or self._require_session()
        previous_status = session.status

        validation = self.validate_ready_for_approval(session)
        if not validation["is_valid"]:
            raise ValidationError(validation["errors"])

        session.submit_for_approval()
        self.session = session

        self._audit(
            action=AuditLog.Action.SESSION_TRANSITION,
            session=session,
            user=user,
            previous_value={"status": previous_status},
            new_value={"status": session.status},
            notes="Session submitted for approval",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return session

    @transaction.atomic
    def approve(
        self,
        *,
        user,
        notes: str = "",
        session: Optional[Session] = None,
        ip_address: Optional[str] = None,
        user_agent: str = "",
    ) -> Session:
        session = session or self._require_session()
        previous_status = session.status

        session.approve(user=user, notes=notes)
        self.session = session

        self._audit(
            action=AuditLog.Action.APPROVAL,
            session=session,
            user=user,
            previous_value={"status": previous_status},
            new_value={"status": session.status, "approval_notes": notes},
            notes=notes or "Session approved",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return session

    @transaction.atomic
    def reject(
        self,
        *,
        user,
        reason: str,
        session: Optional[Session] = None,
        ip_address: Optional[str] = None,
        user_agent: str = "",
    ) -> Session:
        session = session or self._require_session()
        previous_status = session.status

        session.reject(user=user, reason=reason)
        self.session = session

        self._audit(
            action=AuditLog.Action.REJECTION,
            session=session,
            user=user,
            previous_value={"status": previous_status},
            new_value={"status": session.status, "rejection_reason": reason},
            notes=reason,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return session

    @transaction.atomic
    def reopen(
        self,
        *,
        user,
        session: Optional[Session] = None,
        ip_address: Optional[str] = None,
        user_agent: str = "",
    ) -> Session:
        session = session or self._require_session()
        previous_status = session.status

        session.reopen(user=user)
        self.session = session

        self._audit(
            action=AuditLog.Action.SESSION_TRANSITION,
            session=session,
            user=user,
            previous_value={"status": previous_status},
            new_value={"status": session.status},
            notes="Rejected session reopened for corrections",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return session

    @transaction.atomic
    def mark_distributed(
        self,
        *,
        user=None,
        session: Optional[Session] = None,
        ip_address: Optional[str] = None,
        user_agent: str = "",
    ) -> Session:
        session = session or self._require_session()
        previous_status = session.status

        validation = self.validate_ready_for_distribution(session)
        if not validation["is_valid"]:
            raise ValidationError(validation["errors"])

        session.mark_distributed()
        self.session = session

        self._audit(
            action=AuditLog.Action.SESSION_TRANSITION,
            session=session,
            user=user,
            previous_value={"status": previous_status},
            new_value={"status": session.status},
            notes="Session marked distributed",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return session

    @transaction.atomic
    def lock(
        self,
        *,
        user,
        session: Optional[Session] = None,
        ip_address: Optional[str] = None,
        user_agent: str = "",
    ) -> Session:
        session = session or self._require_session()
        previous_status = session.status

        validation = self.validate_ready_for_lock(session)
        if not validation["is_valid"]:
            raise ValidationError(validation["errors"])

        session.lock(user=user)
        self.session = session

        self._audit(
            action=AuditLog.Action.SESSION_TRANSITION,
            session=session,
            user=user,
            previous_value={"status": previous_status},
            new_value={"status": session.status},
            notes="Session locked",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return session

    @transaction.atomic
    def unlock(
        self,
        *,
        user,
        reason: str,
        session: Optional[Session] = None,
        ip_address: Optional[str] = None,
        user_agent: str = "",
    ) -> Session:
        session = session or self._require_session()
        previous_status = session.status

        session.unlock(user=user, reason=reason)
        self.session = session

        self._audit(
            action=AuditLog.Action.UNLOCK,
            session=session,
            user=user,
            previous_value={"status": previous_status},
            new_value={
                "status": session.status,
                "unlock_count": session.unlock_count,
                "last_unlock_reason": session.last_unlock_reason,
            },
            notes=reason,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return session

    def get_session_dashboard(self, session: Optional[Session] = None) -> Dict:
        """
        Returns a simple dashboard summary for a session.
        """
        session = session or self._require_session()

        collections = FeeCollection.objects.filter(session=session)

        by_status_rows = collections.values("status").order_by("status")
        by_status = {
            row["status"]: collections.filter(status=row["status"]).count()
            for row in by_status_rows
        }

        totals = collections.aggregate(
            total_expected=Sum("expected_amount"),
            total_collected=Sum("amount_paid"),
        )

        return {
            "session_id": session.id,
            "date": session.date,
            "session_type": session.session_type,
            "status": session.status,
            "submitted_classes": self._get_submitted_class_count(session),
            "expected_classes": self._get_active_class_count(),
            "collection_counts_by_status": by_status,
            "total_expected": totals["total_expected"] or 0,
            "total_collected": totals["total_collected"] or 0,
            "submitted_at": session.submitted_at,
            "approved_at": session.approved_at,
            "distributed_at": session.distributed_at,
            "locked_at": session.locked_at,
            "unlock_count": session.unlock_count,
        }