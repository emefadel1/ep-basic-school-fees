# apps/fees/services/distribution.py

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional

from django.db import transaction
from django.db.models import Sum

from apps.audit.models import AuditLog
from core.exceptions import DistributionError, InsufficientDataError
from ..models import Distribution, FeeCollection, PoolSummary, Session
from .attendance_service import AttendanceService
from .pool_config import get_pool_by_code
from .validators import DistributionValidator

logger = logging.getLogger("distribution")


@dataclass
class DistributionResult:
    pool_code: str
    total_collected: Decimal
    school_retention: Decimal
    administrative_fee: Decimal
    distributable_amount: Decimal
    staff_shares: Dict[int, Decimal]
    special_shares: Dict[str, Dict[int, Decimal]] = field(default_factory=dict)
    staff_metadata: Dict[int, Dict[str, str]] = field(default_factory=dict)

    def to_dict(self):
        return {
            "pool_code": self.pool_code,
            "total_collected": str(self.total_collected),
            "school_retention": str(self.school_retention),
            "administrative_fee": str(self.administrative_fee),
            "distributable_amount": str(self.distributable_amount),
            "staff_shares": {k: str(v) for k, v in self.staff_shares.items()},
            "special_shares": {
                key: {k: str(v) for k, v in value.items()}
                for key, value in self.special_shares.items()
            },
            "staff_metadata": self.staff_metadata,
        }


class FeeDistributionEngine:
    """
    Calculates and saves fee distributions for configured pools.
    """

    ATTENDANCE_WEIGHTS = {
        "PRESENT": Decimal("1.0"),
        "LATE": Decimal("0.5"),
        "SICK": Decimal("0.5"),
        "PERMISSION": Decimal("0.5"),
        "OFFICIAL_DUTY": Decimal("1.0"),
        "ABSENT": Decimal("0.0"),
    }

    def __init__(self, session: Session):
        self.session = session
        self.calculation_log: List[dict] = []

    def log(self, message: str, data: Optional[dict] = None):
        entry = {
            "step": len(self.calculation_log) + 1,
            "message": message,
            "data": data or {},
        }
        self.calculation_log.append(entry)
        logger.info("Distribution: %s", message, extra=data or {})

    def round_currency(self, amount: Decimal) -> Decimal:
        return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def get_pool(self, pool_code: str) -> dict:
        return get_pool_by_code(pool_code)

    def _rate(self, value) -> Decimal:
        if isinstance(value, Decimal):
            return value

        if value is None:
            return Decimal("0.00")

        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned.endswith("%"):
                return Decimal(cleaned[:-1]) / Decimal("100")
            return Decimal(cleaned)

        return Decimal(str(value))

    def _serialize_pool_summary(self, summary: PoolSummary) -> dict:
        return {
            "session_id": summary.session_id,
            "pool_type": summary.pool_type,
            "total_expected": str(summary.total_expected),
            "total_collected": str(summary.total_collected),
            "total_outstanding": str(summary.total_outstanding),
            "school_retention": str(summary.school_retention),
            "administrative_fee": str(summary.administrative_fee),
            "total_distributed": str(summary.total_distributed),
            "recipient_count": summary.recipient_count,
        }

    def _audit_distribution(
        self,
        *,
        result: DistributionResult,
        pool_summary: PoolSummary,
        user=None,
        previous_value: Optional[dict] = None,
        notes: str = "",
        ip_address: Optional[str] = None,
        user_agent: str = "",
    ):
        AuditLog.log_action(
            action=AuditLog.Action.DISTRIBUTION,
            table_name="pool_summaries",
            record_id=pool_summary.id,
            user=user,
            previous_value=previous_value,
            new_value={
                "session_id": self.session.id,
                "session_date": str(self.session.date),
                "pool_code": result.pool_code,
                "total_collected": str(result.total_collected),
                "school_retention": str(result.school_retention),
                "administrative_fee": str(result.administrative_fee),
                "distributable_amount": str(result.distributable_amount),
                "recipient_count": len([v for v in result.staff_shares.values() if v > 0]),
                "total_distributed": str(sum(result.staff_shares.values(), Decimal("0.00"))),
            },
            notes=notes,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def get_deduction_rate(self, pool_code: str, deduction_name: str) -> Decimal:
        pool = self.get_pool(pool_code)
        deduction = pool.get("deductions", {}).get(deduction_name, {})
        return self._rate(deduction.get("rate", deduction.get("percentage", "0%")))

    def get_split_rate(self, pool_code: str, split_name: str) -> Decimal:
        pool = self.get_pool(pool_code)
        splits = pool.get("distribution", {}).get("splits", [])

        for split in splits:
            if split.get("name") == split_name:
                return self._rate(split.get("rate", split.get("percentage", "0%")))

        raise DistributionError(
            message=f"Split '{split_name}' was not found for pool '{pool_code}'.",
            code="distribution_split_not_found",
            extra={"pool_code": pool_code, "split_name": split_name},
        )

    def unique_ids(self, staff_ids: List[int]) -> List[int]:
        return list(dict.fromkeys(staff_ids))

    def allocate_proportionally(
        self,
        total_amount: Decimal,
        weights: Dict[int, Decimal],
    ) -> Dict[int, Decimal]:
        allocations = {staff_id: Decimal("0.00") for staff_id in weights.keys()}
        positive_items = [(staff_id, weight) for staff_id, weight in weights.items() if weight > 0]

        if not positive_items:
            return allocations

        remaining_amount = self.round_currency(total_amount)
        remaining_weight = sum(weight for _, weight in positive_items)

        for index, (staff_id, weight) in enumerate(positive_items):
            is_last = index == len(positive_items) - 1

            if is_last:
                share = self.round_currency(remaining_amount)
            else:
                raw_share = remaining_amount * weight / remaining_weight
                share = self.round_currency(raw_share)

                if share > remaining_amount:
                    share = remaining_amount

            allocations[staff_id] = share
            remaining_amount -= share
            remaining_weight -= weight

        return allocations

    def allocate_equally(
        self,
        total_amount: Decimal,
        recipient_ids: List[int],
    ) -> Dict[int, Decimal]:
        recipients = self.unique_ids(recipient_ids)
        if not recipients:
            return {}

        return self.allocate_proportionally(
            total_amount=total_amount,
            weights={staff_id: Decimal("1.0") for staff_id in recipients},
        )

    def get_pool_total_collected(self, pool_code: str) -> Decimal:
        total = (
            FeeCollection.objects
            .filter(session=self.session, pool_type=pool_code)
            .aggregate(total=Sum("amount_paid"))
            .get("total")
        )
        return total or Decimal("0.00")

    def get_calculation_log(self) -> List[dict]:
        return self.calculation_log

    def calculate(
        self,
        pool_code: str,
        *,
        headteacher_id: int,
        total_collected: Optional[Decimal] = None,
        staff_attendance: Optional[Dict[int, str]] = None,
        jhs_class_teachers: Optional[List[int]] = None,
        all_jhs_staff: Optional[List[int]] = None,
        saturday_attendees: Optional[List[int]] = None,
    ) -> DistributionResult:
        if total_collected is None:
            total_collected = self.get_pool_total_collected(pool_code)

        if pool_code == "GEN_STUDIES":
            if staff_attendance is None:
                attendance_service = AttendanceService(session=self.session)
                staff_attendance = attendance_service.get_distribution_attendance_map(
                    date=self.session.date
                )
            return self.distribute_general_studies(
                total_collected=total_collected,
                staff_attendance=staff_attendance,
                headteacher_id=headteacher_id,
            )

        if pool_code == "JHS_EXTRA":
            if jhs_class_teachers is None or all_jhs_staff is None:
                raise InsufficientDataError(
                    message="JHS_EXTRA distribution requires class teacher and staff data.",
                    extra={"required": ["jhs_class_teachers", "all_jhs_staff"]},
                )
            return self.distribute_jhs_extra(
                total_collected=total_collected,
                jhs_class_teachers=jhs_class_teachers,
                all_jhs_staff=all_jhs_staff,
                headteacher_id=headteacher_id,
            )

        if pool_code == "JHS3_EXTRA":
            if all_jhs_staff is None:
                raise InsufficientDataError(
                    message="JHS3_EXTRA distribution requires the full JHS staff list.",
                    extra={"required": ["all_jhs_staff"]},
                )
            return self.distribute_jhs3_extra(
                total_collected=total_collected,
                all_jhs_staff=all_jhs_staff,
                headteacher_id=headteacher_id,
            )

        if pool_code == "SATURDAY":
            if saturday_attendees is None:
                attendance_service = AttendanceService(session=self.session)
                saturday_attendees = attendance_service.get_saturday_attendees(
                    date=self.session.date
                )
            return self.distribute_saturday(
                total_collected=total_collected,
                saturday_attendees=saturday_attendees,
                headteacher_id=headteacher_id,
            )

        raise DistributionError(
            message=f"Pool '{pool_code}' is not supported for distribution.",
            code="unsupported_pool_code",
            extra={"pool_code": pool_code},
        )
    @transaction.atomic
    def calculate_and_save(
        self,
        pool_code: str,
        *,
        headteacher_id: int,
        total_collected: Optional[Decimal] = None,
        staff_attendance: Optional[Dict[int, str]] = None,
        jhs_class_teachers: Optional[List[int]] = None,
        all_jhs_staff: Optional[List[int]] = None,
        saturday_attendees: Optional[List[int]] = None,
        overwrite_existing: bool = True,
        user=None,
        ip_address: Optional[str] = None,
        user_agent: str = "",
    ) -> DistributionResult:
        if self.session.status != Session.Status.APPROVED:
            raise DistributionError(
                message="Session must be approved before distribution can run.",
                code="distribution_invalid_state",
                extra={"session_id": self.session.id, "status": self.session.status},
            )
        result = self.calculate(
            pool_code=pool_code,
            headteacher_id=headteacher_id,
            total_collected=total_collected,
            staff_attendance=staff_attendance,
            jhs_class_teachers=jhs_class_teachers,
            all_jhs_staff=all_jhs_staff,
            saturday_attendees=saturday_attendees,
        )
        self.save_distribution_result(
            result,
            overwrite_existing=overwrite_existing,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return result

    @transaction.atomic
    def save_distribution_result(
        self,
        result: DistributionResult,
        *,
        overwrite_existing: bool = True,
        user=None,
        ip_address: Optional[str] = None,
        user_agent: str = "",
    ):
        validator = DistributionValidator()
        validation = validator.validate(result, expected_total=result.total_collected)

        if not validation.is_valid:
            raise DistributionError(
                message="Distribution result did not pass validation.",
                code="distribution_validation_failed",
                extra={"errors": validation.errors, "warnings": validation.warnings},
            )

        existing_summary = PoolSummary.objects.filter(
            session=self.session,
            pool_type=result.pool_code,
        ).first()
        previous_summary_data = self._serialize_pool_summary(existing_summary) if existing_summary else None

        deleted_count = 0
        if overwrite_existing:
            existing_qs = Distribution.objects.filter(
                session=self.session,
                pool_type=result.pool_code,
            )
            deleted_count = existing_qs.count()
            existing_qs.delete()

        for staff_id, final_amount in result.staff_shares.items():
            special_amount = Decimal("0.00")
            special_types: List[str] = []

            for special_name, share_map in (result.special_shares or {}).items():
                if staff_id in share_map:
                    special_amount += share_map[staff_id]
                    special_types.append(special_name)

            adjusted_share = final_amount - special_amount
            metadata = result.staff_metadata.get(staff_id, {})

            Distribution.objects.create(
                session=self.session,
                pool_type=result.pool_code,
                staff_id=staff_id,
                base_share=adjusted_share,
                adjusted_share=adjusted_share,
                attendance_status=metadata.get("attendance_status", ""),
                attendance_weight=Decimal(metadata.get("attendance_weight", "1.00")),
                special_share_type=",".join(special_types),
                special_share_amount=special_amount,
                calculation_log={
                    "pool_code": result.pool_code,
                    "staff_id": staff_id,
                    "final_amount": str(final_amount),
                    "adjusted_share": str(adjusted_share),
                    "special_amount": str(special_amount),
                    "special_types": special_types,
                    "staff_metadata": metadata,
                    "engine_log": self.get_calculation_log(),
                },
            )

        pool_summary, _created = PoolSummary.objects.update_or_create(
            session=self.session,
            pool_type=result.pool_code,
            defaults={
                "total_expected": result.total_collected,
                "total_collected": result.total_collected,
                "total_outstanding": Decimal("0.00"),
                "school_retention": result.school_retention,
                "administrative_fee": result.administrative_fee,
                "total_distributed": sum(result.staff_shares.values(), Decimal("0.00")),
                "recipient_count": len([v for v in result.staff_shares.values() if v > 0]),
                "calculation_log": {
                    "result": result.to_dict(),
                    "validation_errors": validation.errors,
                    "validation_warnings": validation.warnings,
                    "engine_log": self.get_calculation_log(),
                },
            },
        )

        notes = (
            f"Distribution saved for pool {result.pool_code}. "
            f"Recipients: {len([v for v in result.staff_shares.values() if v > 0])}. "
            f"Overwritten existing rows: {deleted_count}."
        )

        self._audit_distribution(
            result=result,
            pool_summary=pool_summary,
            user=user,
            previous_value=previous_summary_data,
            notes=notes,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @transaction.atomic
    def distribute_general_studies(
        self,
        *,
        total_collected: Decimal,
        staff_attendance: Dict[int, str],
        headteacher_id: int,
    ) -> DistributionResult:
        self.log("Starting General Studies distribution", {
            "pool_code": "GEN_STUDIES",
            "total_collected": str(total_collected),
            "staff_count": len(staff_attendance),
        })

        school_rate = self.get_deduction_rate("GEN_STUDIES", "school_retention")
        admin_rate = self.get_deduction_rate("GEN_STUDIES", "administrative_fee")

        school_retention = self.round_currency(total_collected * school_rate)
        admin_fee = self.round_currency(total_collected * admin_rate)
        distributable = total_collected - school_retention - admin_fee

        attendance_map = dict(staff_attendance)
        attendance_map[headteacher_id] = "PRESENT"

        staff_weights: Dict[int, Decimal] = {}
        staff_metadata: Dict[int, Dict[str, str]] = {}

        for staff_id, status in attendance_map.items():
            weight = self.ATTENDANCE_WEIGHTS.get(status, Decimal("0.0"))
            staff_weights[staff_id] = weight
            staff_metadata[staff_id] = {
                "attendance_status": status,
                "attendance_weight": str(weight),
            }

            self.log("Staff weight calculated", {
                "staff_id": staff_id,
                "status": status,
                "weight": str(weight),
            })

        staff_shares = self.allocate_proportionally(distributable, staff_weights)

        self.log("General Studies distribution complete", {
            "school_retention": str(school_retention),
            "administrative_fee": str(admin_fee),
            "distributable": str(distributable),
            "total_distributed": str(sum(staff_shares.values(), Decimal("0.00"))),
        })

        return DistributionResult(
            pool_code="GEN_STUDIES",
            total_collected=total_collected,
            school_retention=school_retention,
            administrative_fee=admin_fee,
            distributable_amount=distributable,
            staff_shares=staff_shares,
            special_shares={},
            staff_metadata=staff_metadata,
        )

    @transaction.atomic
    def distribute_jhs_extra(
        self,
        *,
        total_collected: Decimal,
        jhs_class_teachers: List[int],
        all_jhs_staff: List[int],
        headteacher_id: int,
    ) -> DistributionResult:
        self.log("Starting JHS Extra distribution", {
            "pool_code": "JHS_EXTRA",
            "total_collected": str(total_collected),
            "class_teacher_count": len(jhs_class_teachers),
            "jhs_staff_count": len(all_jhs_staff),
        })

        school_rate = self.get_deduction_rate("JHS_EXTRA", "school_retention")
        admin_rate = self.get_deduction_rate("JHS_EXTRA", "administrative_fee")
        ct_bonus_rate = self.get_split_rate("JHS_EXTRA", "Class Teacher Bonus")

        school_retention = self.round_currency(total_collected * school_rate)
        admin_fee = self.round_currency(total_collected * admin_rate)
        total_after_deductions = total_collected - school_retention - admin_fee

        ct_bonus_pool = self.round_currency(total_collected * ct_bonus_rate)
        staff_pool = total_after_deductions - ct_bonus_pool

        class_teacher_ids = self.unique_ids(jhs_class_teachers)
        all_recipients = self.unique_ids(all_jhs_staff + [headteacher_id])

        ct_bonus_shares = self.allocate_equally(ct_bonus_pool, class_teacher_ids)
        staff_pool_shares = self.allocate_equally(staff_pool, all_recipients)

        staff_shares = {
            staff_id: Decimal("0.00")
            for staff_id in self.unique_ids(all_recipients + class_teacher_ids)
        }
        special_shares = {"class_teacher_bonus": {}}
        staff_metadata = {}

        for staff_id in staff_shares.keys():
            base_share = staff_pool_shares.get(staff_id, Decimal("0.00"))
            bonus_share = ct_bonus_shares.get(staff_id, Decimal("0.00"))
            staff_shares[staff_id] = base_share + bonus_share

            staff_metadata[staff_id] = {
                "attendance_status": "",
                "attendance_weight": "1.00",
            }

            if bonus_share > 0:
                special_shares["class_teacher_bonus"][staff_id] = bonus_share

        distributable = total_after_deductions

        self.log("JHS Extra distribution complete", {
            "school_retention": str(school_retention),
            "administrative_fee": str(admin_fee),
            "ct_bonus_pool": str(ct_bonus_pool),
            "staff_pool": str(staff_pool),
            "total_distributed": str(sum(staff_shares.values(), Decimal("0.00"))),
        })

        return DistributionResult(
            pool_code="JHS_EXTRA",
            total_collected=total_collected,
            school_retention=school_retention,
            administrative_fee=admin_fee,
            distributable_amount=distributable,
            staff_shares=staff_shares,
            special_shares=special_shares,
            staff_metadata=staff_metadata,
        )

    @transaction.atomic
    def distribute_jhs3_extra(
        self,
        *,
        total_collected: Decimal,
        all_jhs_staff: List[int],
        headteacher_id: int,
    ) -> DistributionResult:
        self.log("Starting JHS3 Extra distribution", {
            "pool_code": "JHS3_EXTRA",
            "total_collected": str(total_collected),
            "jhs_staff_count": len(all_jhs_staff),
        })

        school_rate = self.get_deduction_rate("JHS3_EXTRA", "school_retention")
        admin_rate = self.get_deduction_rate("JHS3_EXTRA", "administrative_fee")

        school_retention = self.round_currency(total_collected * school_rate)
        admin_fee = self.round_currency(total_collected * admin_rate)
        distributable = total_collected - school_retention - admin_fee

        all_recipients = self.unique_ids(all_jhs_staff + [headteacher_id])
        staff_shares = self.allocate_equally(distributable, all_recipients)
        staff_metadata = {
            staff_id: {"attendance_status": "", "attendance_weight": "1.00"}
            for staff_id in staff_shares.keys()
        }

        self.log("JHS3 Extra distribution complete", {
            "school_retention": str(school_retention),
            "administrative_fee": str(admin_fee),
            "distributable": str(distributable),
            "total_distributed": str(sum(staff_shares.values(), Decimal("0.00"))),
        })

        return DistributionResult(
            pool_code="JHS3_EXTRA",
            total_collected=total_collected,
            school_retention=school_retention,
            administrative_fee=admin_fee,
            distributable_amount=distributable,
            staff_shares=staff_shares,
            special_shares={},
            staff_metadata=staff_metadata,
        )

    @transaction.atomic
    def distribute_saturday(
        self,
        *,
        total_collected: Decimal,
        saturday_attendees: List[int],
        headteacher_id: int,
    ) -> DistributionResult:
        self.log("Starting Saturday distribution", {
            "pool_code": "SATURDAY",
            "total_collected": str(total_collected),
            "attendee_count": len(saturday_attendees),
        })

        school_rate = self.get_deduction_rate("SATURDAY", "school_retention")
        admin_rate = self.get_deduction_rate("SATURDAY", "administrative_fee")

        school_retention = self.round_currency(total_collected * school_rate)
        admin_fee = self.round_currency(total_collected * admin_rate)
        distributable = total_collected - school_retention - admin_fee

        all_recipients = self.unique_ids(saturday_attendees + [headteacher_id])
        staff_shares = self.allocate_equally(distributable, all_recipients)
        staff_metadata = {
            staff_id: {"attendance_status": "", "attendance_weight": "1.00"}
            for staff_id in staff_shares.keys()
        }

        self.log("Saturday distribution complete", {
            "school_retention": str(school_retention),
            "administrative_fee": str(admin_fee),
            "distributable": str(distributable),
            "total_distributed": str(sum(staff_shares.values(), Decimal("0.00"))),
        })

        return DistributionResult(
            pool_code="SATURDAY",
            total_collected=total_collected,
            school_retention=school_retention,
            administrative_fee=admin_fee,
            distributable_amount=distributable,
            staff_shares=staff_shares,
            special_shares={},
            staff_metadata=staff_metadata,
        )