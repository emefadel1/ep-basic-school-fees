# services/validators.py

from decimal import Decimal
from typing import List
from dataclasses import dataclass

from .pool_config import get_pool_by_code


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]


class DistributionValidator:
    """Validates distribution results before saving"""

    MONEY_TOLERANCE = Decimal("0.01")

    def parse_percentage(self, value) -> Decimal:
        if value is None:
            return Decimal("0.00")

        if isinstance(value, str):
            value = value.strip()
            if value.endswith("%"):
                return Decimal(value[:-1]) / Decimal("100")
            return Decimal(value)

        return Decimal(str(value))

    def round_currency(self, amount: Decimal) -> Decimal:
        return amount.quantize(Decimal("0.01"))

    def validate(
        self,
        result: "DistributionResult",
        expected_total: Decimal | None = None
    ) -> ValidationResult:
        errors = []
        warnings = []

        try:
            pool = get_pool_by_code(result.pool_code)
        except Exception as exc:
            return ValidationResult(
                is_valid=False,
                errors=[f"Pool config lookup failed for {result.pool_code}: {exc}"],
                warnings=[]
            )

        school_rate = self.parse_percentage(
            pool.get("deductions", {})
            .get("school_retention", {})
            .get("percentage", "0%")
        )

        admin_rate = self.parse_percentage(
            pool.get("deductions", {})
            .get("administrative_fee", {})
            .get("percentage", "0%")
        )

        # 1. Total-collected consistency
        if expected_total is not None and result.total_collected != expected_total:
            errors.append(
                f"Total collected mismatch: expected {expected_total}, "
                f"got {result.total_collected}"
            )

        # 2. School retention check from YAML
        expected_retention = self.round_currency(result.total_collected * school_rate)
        retention_diff = abs(result.school_retention - expected_retention)
        if retention_diff > self.MONEY_TOLERANCE:
            errors.append(
                f"School retention incorrect: expected {expected_retention}, "
                f"got {result.school_retention}"
            )

        # 3. Administrative fee check from YAML
        expected_admin_fee = self.round_currency(result.total_collected * admin_rate)
        admin_diff = abs(result.administrative_fee - expected_admin_fee)
        if admin_diff > self.MONEY_TOLERANCE:
            errors.append(
                f"Administrative fee incorrect: expected {expected_admin_fee}, "
                f"got {result.administrative_fee}"
            )

        # 4. Distributable amount check
        expected_distributable = (
            result.total_collected
            - result.school_retention
            - result.administrative_fee
        )
        distributable_diff = abs(result.distributable_amount - expected_distributable)
        if distributable_diff > self.MONEY_TOLERANCE:
            errors.append(
                f"Distributable amount incorrect: expected {expected_distributable}, "
                f"got {result.distributable_amount}"
            )

        # 5. Staff share reconciliation
        total_staff_shares = sum(result.staff_shares.values(), Decimal("0.00"))
        share_diff = abs(result.distributable_amount - total_staff_shares)

        if share_diff > self.MONEY_TOLERANCE:
            errors.append(
                f"Staff shares do not reconcile: distributable {result.distributable_amount}, "
                f"staff total {total_staff_shares}, difference {share_diff}"
            )
        elif share_diff > Decimal("0.00"):
            warnings.append(
                f"Minor rounding difference in staff shares: {share_diff}"
            )

        # 6. Full reconciliation
        calculated_total = (
            result.school_retention +
            result.administrative_fee +
            total_staff_shares
        )
        total_diff = abs(result.total_collected - calculated_total)

        if total_diff > self.MONEY_TOLERANCE:
            errors.append(
                f"Grand total mismatch: collected {result.total_collected}, "
                f"reconciled {calculated_total}, difference {total_diff}"
            )
        elif total_diff > Decimal("0.00"):
            warnings.append(
                f"Minor grand-total rounding difference: {total_diff}"
            )

        # 7. Negative amount checks
        if result.total_collected < 0:
            errors.append(f"Negative total_collected: {result.total_collected}")

        if result.school_retention < 0:
            errors.append(f"Negative school_retention: {result.school_retention}")

        if result.administrative_fee < 0:
            errors.append(f"Negative administrative_fee: {result.administrative_fee}")

        if result.distributable_amount < 0:
            errors.append(f"Negative distributable_amount: {result.distributable_amount}")

        for staff_id, amount in result.staff_shares.items():
            if amount < 0:
                errors.append(f"Negative share for staff {staff_id}: {amount}")

        # 8. Empty-recipient sanity check
        if result.distributable_amount > Decimal("0.00") and not result.staff_shares:
            errors.append(
                "Distributable amount is greater than zero but there are no staff shares"
            )

        # 9. Tiny-share warning
        for staff_id, amount in result.staff_shares.items():
            if Decimal("0.00") < amount < Decimal("0.01"):
                warnings.append(f"Very small share for staff {staff_id}: {amount}")

        # 10. Special share consistency checks
        if result.pool_code == "JHS_EXTRA":
            ct_bonus_shares = result.special_shares.get("class_teacher_bonus", {})
            declared_ct_bonus_total = sum(ct_bonus_shares.values(), Decimal("0.00"))

            split_defs = pool.get("distribution", {}).get("splits", [])
            ct_split = next(
                (s for s in split_defs if s.get("name") == "Class Teacher Bonus"),
                None
            )

            if ct_split:
                ct_bonus_rate = self.parse_percentage(ct_split.get("percentage", "0%"))
                expected_ct_bonus_total = self.round_currency(
                    result.total_collected * ct_bonus_rate
                )

                ct_bonus_diff = abs(declared_ct_bonus_total - expected_ct_bonus_total)
                if ct_bonus_diff > self.MONEY_TOLERANCE:
                    errors.append(
                        f"Class teacher bonus total incorrect: expected {expected_ct_bonus_total}, "
                        f"got {declared_ct_bonus_total}"
                    )

            for staff_id, bonus in ct_bonus_shares.items():
                total_share = result.staff_shares.get(staff_id, Decimal("0.00"))
                if bonus > total_share:
                    errors.append(
                        f"Special share inconsistency for staff {staff_id}: "
                        f"bonus {bonus} exceeds total share {total_share}"
                    )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )