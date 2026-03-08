# apps/fees/services/attendance_service.py

from __future__ import annotations

from datetime import time
from typing import Dict, List, Optional

from django.db import transaction

from ..models import Session, StaffAttendance, SaturdayAttendance
from .attendance_rules import get_attendance_rule


class AttendanceServiceError(Exception):
    pass


class AttendanceService:
    """
    Service layer for staff attendance recording, verification,
    finalization, and payout-ready attendance extraction.
    """

    DEFAULT_LATE_CUTOFF = time(hour=8, minute=0)

    def __init__(self, session: Session):
        self.session = session

    def _get_late_cutoff(self) -> time:
        """
        Read late threshold from attendance rules.
        Falls back to 8:00 AM if not configured.
        """
        try:
            late_rule = get_attendance_rule(StaffAttendance.Status.LATE)
            threshold_minutes = late_rule.get("late_threshold_minutes", 0)

            if threshold_minutes == 30:
                return time(hour=8, minute=0)

            return self.DEFAULT_LATE_CUTOFF
        except Exception:
            return self.DEFAULT_LATE_CUTOFF

    def _status_requires_documentation(self, status: str) -> bool:
        rule = get_attendance_rule(status)
        return bool(rule.get("requires_documentation", False))

    def _status_requires_approval(self, status: str) -> bool:
        rule = get_attendance_rule(status)
        return bool(rule.get("requires_approval", False))

    def _auto_resolve_status(
        self,
        requested_status: str,
        check_in_time=None,
    ) -> str:
        """
        Auto-convert PRESENT -> LATE if check-in is after cutoff.
        """
        if requested_status == StaffAttendance.Status.PRESENT and check_in_time:
            if check_in_time > self._get_late_cutoff():
                return StaffAttendance.Status.LATE
        return requested_status

    @transaction.atomic
    def record_staff_attendance(
        self,
        *,
        staff,
        date,
        recorded_by,
        status: str = StaffAttendance.Status.PRESENT,
        check_in_time=None,
        check_out_time=None,
        documentation=None,
        notes: str = "",
    ) -> StaffAttendance:
        """
        Create or update staff attendance for a session/date.
        Unique key is staff + date, matching your model constraint.
        """
        final_status = self._auto_resolve_status(
            requested_status=status,
            check_in_time=check_in_time,
        )

        record, _created = StaffAttendance.objects.get_or_create(
            staff=staff,
            date=date,
            defaults={
                "session": self.session,
            },
        )

        record.session = self.session
        record.date = date
        record.status = final_status
        record.check_in_time = check_in_time
        record.check_out_time = check_out_time
        record.documentation = documentation
        record.notes = notes
        record.recorded_by = recorded_by

        if self._status_requires_documentation(final_status):
            record.documentation_verified = False
            record.documentation_verified_by = None
        else:
            record.documentation_verified = True
            record.documentation_verified_by = recorded_by

        record.full_clean()
        record.save()

        return record

    @transaction.atomic
    def verify_documentation(
        self,
        *,
        attendance_id: int,
        verified_by,
    ) -> StaffAttendance:
        """
        Mark documentation as verified for attendance statuses
        that require supporting documents.
        """
        record = StaffAttendance.objects.select_for_update().get(id=attendance_id)

        if not record.documentation:
            raise AttendanceServiceError(
                "Cannot verify documentation because no file is attached."
            )

        if not self._status_requires_documentation(record.status):
            raise AttendanceServiceError(
                f"Status {record.status} does not require documentation verification."
            )

        record.documentation_verified = True
        record.documentation_verified_by = verified_by
        record.full_clean()
        record.save(update_fields=[
            "documentation_verified",
            "documentation_verified_by",
            "updated_at",
        ])

        return record

    @transaction.atomic
    def finalize_attendance_status(
        self,
        *,
        attendance_id: int,
        approver,
        approved: bool,
        rejection_status: str = StaffAttendance.Status.ABSENT,
        notes: Optional[str] = None,
    ) -> StaffAttendance:
        """
        Finalize attendance for payout purposes.

        Because your model does not yet have a dedicated approval_status field,
        finalization is reflected through:
        - documentation_verified / documentation_verified_by
        - optional downgrade to rejection_status
        """
        record = StaffAttendance.objects.select_for_update().get(id=attendance_id)

        if approved:
            if self._status_requires_documentation(record.status):
                if not record.documentation:
                    raise AttendanceServiceError(
                        f"Cannot approve {record.status} without documentation."
                    )
                record.documentation_verified = True
                record.documentation_verified_by = approver
            else:
                record.documentation_verified = True
                record.documentation_verified_by = approver
        else:
            record.status = rejection_status
            record.documentation_verified = False
            record.documentation_verified_by = approver

        if notes:
            record.notes = f"{record.notes}\n{notes}".strip()

        record.full_clean()
        record.save()

        return record

    def resolve_distribution_status(self, record: StaffAttendance) -> str:
        """
        Convert a raw attendance record into the status that should be used
        by the distribution engine.
        """
        if self._status_requires_documentation(record.status):
            if not record.documentation or not record.documentation_verified:
                return StaffAttendance.Status.ABSENT

        if self._status_requires_approval(record.status):
            if not record.documentation_verified:
                return StaffAttendance.Status.ABSENT

        return record.status

    def get_distribution_attendance_map(self, *, date) -> Dict[int, str]:
        """
        Return {staff_id: final_status} for General Studies distribution.
        """
        records = (
            StaffAttendance.objects
            .filter(session=self.session, date=date)
            .select_related("staff")
        )

        result: Dict[int, str] = {}
        for record in records:
            result[record.staff_id] = self.resolve_distribution_status(record)

        return result

    @transaction.atomic
    def record_saturday_attendance(
        self,
        *,
        staff,
        date,
        recorded_by,
        is_present: bool,
        check_in_time=None,
        check_out_time=None,
    ) -> SaturdayAttendance:
        """
        Create or update Saturday attendance for a session/date.
        """
        record, _created = SaturdayAttendance.objects.get_or_create(
            staff=staff,
            date=date,
            defaults={
                "session": self.session,
            },
        )

        record.session = self.session
        record.date = date
        record.is_present = is_present
        record.check_in_time = check_in_time
        record.check_out_time = check_out_time
        record.recorded_by = recorded_by

        record.full_clean()
        record.save()

        return record

    def get_saturday_attendees(self, *, date) -> List[int]:
        """
        Return list of staff IDs eligible for Saturday distribution.
        """
        return list(
            SaturdayAttendance.objects
            .filter(session=self.session, date=date, is_present=True)
            .values_list("staff_id", flat=True)
        )