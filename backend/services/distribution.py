# services/distribution.py

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List
from dataclasses import dataclass
from django.db import transaction
import logging

from .pool_config import get_pool_by_code

logger = logging.getLogger("distribution")


@dataclass
class DistributionResult:
    pool_code: str
    total_collected: Decimal
    school_retention: Decimal
    administrative_fee: Decimal
    distributable_amount: Decimal
    staff_shares: Dict[int, Decimal]  # staff_id -> amount
    special_shares: Dict[str, Dict[int, Decimal]]  # e.g. {"class_teacher_bonus": {...}}

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
        }


class FeeDistributionEngine:
    """
    Core distribution engine for all fee pools.
    Handles calculation logic with full audit trail.
    Pool percentages and split rules are loaded from fee_pools.yaml.
    """

    ATTENDANCE_WEIGHTS = {
        "PRESENT": Decimal("1.0"),
        "LATE": Decimal("0.5"),
        "SICK": Decimal("0.5"),
        "PERMISSION": Decimal("0.5"),
        "OFFICIAL_DUTY": Decimal("1.0"),
        "ABSENT": Decimal("0.0"),
    }

    def __init__(self, session):
        self.session = session
        self.calculation_log = []

    def log(self, message: str, data: dict = None):
        """Log calculation step for audit"""
        entry = {
            "step": len(self.calculation_log) + 1,
            "message": message,
            "data": data or {},
        }
        self.calculation_log.append(entry)
        logger.info(f"Distribution: {message}", extra=data or {})

    def round_currency(self, amount: Decimal) -> Decimal:
        """Round to 2 decimal places"""
        return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def get_pool(self, pool_code: str) -> dict:
        return get_pool_by_code(pool_code)

    def parse_percentage(self, value) -> Decimal:
        """
        Accepts:
        - '10%' -> Decimal('0.10')
        - '0.10' -> Decimal('0.10')
        - 10 -> Decimal('10')
        """
        if value is None:
            return Decimal("0.00")

        if isinstance(value, str):
            value = value.strip()
            if value.endswith("%"):
                return Decimal(value[:-1]) / Decimal("100")
            return Decimal(value)

        return Decimal(str(value))

    def get_deduction_rate(self, pool_code: str, deduction_name: str) -> Decimal:
        pool = self.get_pool(pool_code)
        percentage = (
            pool.get("deductions", {})
            .get(deduction_name, {})
            .get("percentage", "0%")
        )
        return self.parse_percentage(percentage)

    def get_split_rate(self, pool_code: str, split_name: str) -> Decimal:
        pool = self.get_pool(pool_code)
        splits = pool.get("distribution", {}).get("splits", [])

        for split in splits:
            if split.get("name") == split_name:
                return self.parse_percentage(split.get("percentage", "0%"))

        raise ValueError(f"Split '{split_name}' not found for pool '{pool_code}'")

    def unique_ids(self, staff_ids: List[int]) -> List[int]:
        """Remove duplicates while keeping order"""
        return list(dict.fromkeys(staff_ids))

    def allocate_proportionally(
        self,
        total_amount: Decimal,
        weights: Dict[int, Decimal]
    ) -> Dict[int, Decimal]:
        """
        Distribute total_amount proportionally using progressive rounding so that:
        sum(result.values()) == total_amount exactly.
        """
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
        recipient_ids: List[int]
    ) -> Dict[int, Decimal]:
        recipients = self.unique_ids(recipient_ids)
        if not recipients:
            return {}

        equal_weights = {staff_id: Decimal("1.0") for staff_id in recipients}
        return self.allocate_proportionally(total_amount, equal_weights)

    @transaction.atomic
    def distribute_general_studies(
        self,
        total_collected: Decimal,
        staff_attendance: Dict[int, str],
        headteacher_id: int
    ) -> DistributionResult:
        """
        Distribute General Studies pool with attendance rules.
        """
        self.log("Starting General Studies distribution", {
            "total_collected": str(total_collected),
            "staff_count": len(staff_attendance),
        })

        school_rate = self.get_deduction_rate("GEN_STUDIES", "school_retention")
        admin_rate = self.get_deduction_rate("GEN_STUDIES", "administrative_fee")

        # Step 1: School retention
        school_retention = self.round_currency(total_collected * school_rate)
        remaining = total_collected - school_retention

        self.log("School retention calculated", {
            "school_retention": str(school_retention),
            "remaining": str(remaining),
        })

        # Step 2: Administrative fee
        admin_fee = self.round_currency(total_collected * admin_rate)
        distributable = remaining - admin_fee

        self.log("Administrative fee calculated", {
            "administrative_fee": str(admin_fee),
            "distributable": str(distributable),
        })

        # Step 3: Calculate attendance weights
        # Use a copy so we do not mutate caller input
        attendance_map = dict(staff_attendance)
        attendance_map[headteacher_id] = "PRESENT"  # headteacher always gets full share

        total_weight = Decimal("0")
        staff_weights = {}

        for staff_id, status in attendance_map.items():
            weight = self.ATTENDANCE_WEIGHTS.get(status, Decimal("0"))
            staff_weights[staff_id] = weight
            total_weight += weight

            self.log("Staff weight calculated", {
                "staff_id": staff_id,
                "status": status,
                "weight": str(weight),
            })

        # Step 4: Distribute based on weights
        staff_shares = self.allocate_proportionally(distributable, staff_weights)

        self.log("Distribution complete", {
            "total_distributed": str(sum(staff_shares.values(), Decimal("0.00"))),
            "recipient_count": len([s for s in staff_shares.values() if s > 0]),
            "total_weight": str(total_weight),
        })

        return DistributionResult(
            pool_code="GEN_STUDIES",
            total_collected=total_collected,
            school_retention=school_retention,
            administrative_fee=admin_fee,
            distributable_amount=distributable,
            staff_shares=staff_shares,
            special_shares={}
        )

    @transaction.atomic
    def distribute_jhs_extra(
        self,
        total_collected: Decimal,
        jhs_class_teachers: List[int],
        all_jhs_staff: List[int],
        headteacher_id: int
    ) -> DistributionResult:
        """
        Distribute JHS Extra pool.

        Distribution:
        - school retention from YAML
        - administrative fee from YAML
        - class teacher bonus from YAML split
        - remaining to all JHS staff including headteacher

        Note: Class teachers receive BOTH the CT bonus AND staff share.
        """
        self.log("Starting JHS Extra distribution", {
            "total_collected": str(total_collected),
            "class_teachers": jhs_class_teachers,
            "jhs_staff_count": len(all_jhs_staff),
        })

        school_rate = self.get_deduction_rate("JHS_EXTRA", "school_retention")
        admin_rate = self.get_deduction_rate("JHS_EXTRA", "administrative_fee")
        ct_bonus_rate = self.get_split_rate("JHS_EXTRA", "Class Teacher Bonus")

        # Step 1: Deductions
        school_retention = self.round_currency(total_collected * school_rate)
        admin_fee = self.round_currency(total_collected * admin_rate)

        total_after_deductions = total_collected - school_retention - admin_fee

        self.log("Deductions calculated", {
            "school_retention": str(school_retention),
            "admin_fee": str(admin_fee),
            "after_deductions": str(total_after_deductions),
        })

        # Step 2: Class teacher bonus
        ct_bonus_pool = self.round_currency(total_collected * ct_bonus_rate)
        staff_pool = total_after_deductions - ct_bonus_pool

        class_teacher_ids = self.unique_ids(jhs_class_teachers)
        all_recipients = self.unique_ids(all_jhs_staff + [headteacher_id])

        ct_bonus_shares = self.allocate_equally(ct_bonus_pool, class_teacher_ids)
        staff_pool_shares = self.allocate_equally(staff_pool, all_recipients)

        self.log("Class teacher bonus calculated", {
            "ct_bonus_pool": str(ct_bonus_pool),
            "ct_bonus_recipients": len(class_teacher_ids),
        })

        # Step 3: Merge shares
        staff_shares = {
            staff_id: Decimal("0.00")
            for staff_id in self.unique_ids(all_recipients + class_teacher_ids)
        }
        special_shares = {"class_teacher_bonus": {}}

        for staff_id, amount in staff_pool_shares.items():
            staff_shares[staff_id] += amount

        for staff_id, amount in ct_bonus_shares.items():
            staff_shares[staff_id] += amount
            special_shares["class_teacher_bonus"][staff_id] = amount

        distributable = total_after_deductions

        self.log("Distribution complete", {
            "total_distributed": str(sum(staff_shares.values(), Decimal("0.00"))),
            "staff_pool_total": str(sum(staff_pool_shares.values(), Decimal("0.00"))),
            "ct_bonus_total": str(sum(ct_bonus_shares.values(), Decimal("0.00"))),
            "recipient_count": len([s for s in staff_shares.values() if s > 0]),
        })

        return DistributionResult(
            pool_code="JHS_EXTRA",
            total_collected=total_collected,
            school_retention=school_retention,
            administrative_fee=admin_fee,
            distributable_amount=distributable,
            staff_shares=staff_shares,
            special_shares=special_shares
        )

    @transaction.atomic
    def distribute_jhs3_extra(
        self,
        total_collected: Decimal,
        all_jhs_staff: List[int],
        headteacher_id: int
    ) -> DistributionResult:
        """
        Distribute JHS 3 Extra pool.
        """
        self.log("Starting JHS 3 Extra distribution", {
            "total_collected": str(total_collected),
            "jhs_staff_count": len(all_jhs_staff),
        })

        school_rate = self.get_deduction_rate("JHS3_EXTRA", "school_retention")
        admin_rate = self.get_deduction_rate("JHS3_EXTRA", "administrative_fee")

        # Step 1: Deductions
        school_retention = self.round_currency(total_collected * school_rate)
        remaining = total_collected - school_retention

        admin_fee = self.round_currency(total_collected * admin_rate)
        distributable = remaining - admin_fee

        # Step 2: Distribute equally
        all_recipients = self.unique_ids(all_jhs_staff + [headteacher_id])
        staff_shares = self.allocate_equally(distributable, all_recipients)

        self.log("Distribution complete", {
            "total_distributed": str(sum(staff_shares.values(), Decimal("0.00"))),
            "recipient_count": len([s for s in staff_shares.values() if s > 0]),
        })

        return DistributionResult(
            pool_code="JHS3_EXTRA",
            total_collected=total_collected,
            school_retention=school_retention,
            administrative_fee=admin_fee,
            distributable_amount=distributable,
            staff_shares=staff_shares,
            special_shares={}
        )

    @transaction.atomic
    def distribute_saturday(
        self,
        total_collected: Decimal,
        saturday_attendees: List[int],
        headteacher_id: int
    ) -> DistributionResult:
        """
        Distribute Saturday Classes pool.
        """
        self.log("Starting Saturday distribution", {
            "total_collected": str(total_collected),
            "attendees_count": len(saturday_attendees),
        })

        school_rate = self.get_deduction_rate("SATURDAY", "school_retention")
        admin_rate = self.get_deduction_rate("SATURDAY", "administrative_fee")

        # Ensure headteacher is included
        all_recipients = self.unique_ids(saturday_attendees + [headteacher_id])

        # Step 1: Deductions
        school_retention = self.round_currency(total_collected * school_rate)
        remaining = total_collected - school_retention

        admin_fee = self.round_currency(total_collected * admin_rate)
        distributable = remaining - admin_fee

        # Step 2: Distribute equally
        staff_shares = self.allocate_equally(distributable, all_recipients)

        self.log("Distribution complete", {
            "total_distributed": str(sum(staff_shares.values(), Decimal("0.00"))),
            "recipient_count": len([s for s in staff_shares.values() if s > 0]),
        })

        return DistributionResult(
            pool_code="SATURDAY",
            total_collected=total_collected,
            school_retention=school_retention,
            administrative_fee=admin_fee,
            distributable_amount=distributable,
            staff_shares=staff_shares,
            special_shares={}
        )

    def get_calculation_log(self) -> List[dict]:
        """Return full calculation log for audit"""
        return self.calculation_log