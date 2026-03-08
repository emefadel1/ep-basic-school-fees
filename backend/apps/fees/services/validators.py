# apps/fees/services/validators.py

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

from .pool_config import get_pool_by_code


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]


class DistributionValidator:
    """
    Validates distribution results before they are saved.
    """

    MONEY_TOLERANCE = Decimal("0.01")

    def round_currency(self, amount: Decimal) -> Decimal:
        return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _rate(self, value) -> Decimal:
        """
        Accepts:
        - Decimal('0.10')
        - '10%'
        - '0.10'
        - None
        """
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

    def _get_pool_rates(self, pool_code: str):
        pool = get_pool_by_code(pool_code)

        school_retention = (
            pool.get("deductions", {})
            .get("school_retention", {})
        )
        administrative_fee = (
            pool.get("deductions", {})
            .get("administrative_fee", {})
        )

        school_rate = self._rate(
            school_retention.get("rate", school_retention.get("percentage", "0%"))
        )
        admin_rate = self._rate(
            administrative_fee.get("rate", administrative_fee.get("percentage", "0%"))
        )

        return pool, school_rate, admin_rate

    def validate(
        self,
        result: "DistributionResult",
        expected_total: Optional[Decimal] = None,
    ) -> ValidationResult:
        errors: List[str] = []
        warnings: List[str] = []

        try:
            pool, school_rate, admin_rate = self._get_pool_rates(result.pool_code)
        except Exception as exc:
            return ValidationResult(
                is_valid=False,
                errors=[f"Pool config lookup failed for {result.pool_code}: {exc}"],
                warnings=[],
            )

        # 1. Optional external total check
        if expected_total is not None and result.total_collected != expected_total:
            errors.append(
                f"Total collected mismatch: expected {expected_total}, got {result.total_collected}"
            )

        # 2. Retention check
        expected_retention = self.round_currency(result.total_collected * school_rate)
        retention_diff = abs(result.school_retention - expected_retention)
        if retention_diff > self.MONEY_TOLERANCE:
            errors.append(
                f"School retention incorrect: expected {expected_retention}, "
                f"got {result.school_retention}"
            )

        # 3. Admin fee check
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

        # 5. Staff share total check
        total_staff_shares = sum(result.staff_shares.values(), Decimal("0.00"))
        staff_diff = abs(result.distributable_amount - total_staff_shares)

        if staff_diff > self.MONEY_TOLERANCE:
            errors.append(
                f"Staff shares do not reconcile: distributable {result.distributable_amount}, "
                f"staff total {total_staff_shares}, difference {staff_diff}"
            )
        elif staff_diff > Decimal("0.00"):
            warnings.append(f"Minor staff-share rounding difference: {staff_diff}")

        # 6. Grand total reconciliation
        calculated_total = (
            result.school_retention
            + result.administrative_fee
            + total_staff_shares
        )
        total_diff = abs(result.total_collected - calculated_total)

        if total_diff > self.MONEY_TOLERANCE:
            errors.append(
                f"Grand total mismatch: collected {result.total_collected}, "
                f"reconciled {calculated_total}, difference {total_diff}"
            )
        elif total_diff > Decimal("0.00"):
            warnings.append(f"Minor grand-total rounding difference: {total_diff}")

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

        # 8. Empty recipient sanity check
        positive_share_count = len([v for v in result.staff_shares.values() if v > 0])
        if result.distributable_amount > Decimal("0.00") and positive_share_count == 0:
            errors.append(
                "Distributable amount is greater than zero but no recipient has a positive share."
            )

        # 9. Special shares must not exceed total share
        for special_name, share_map in (result.special_shares or {}).items():
            for staff_id, special_amount in share_map.items():
                total_amount = result.staff_shares.get(staff_id, Decimal("0.00"))

                if special_amount < 0:
                    errors.append(
                        f"Negative special share for '{special_name}' staff {staff_id}: {special_amount}"
                    )

                if special_amount > total_amount:
                    errors.append(
                        f"Special share '{special_name}' for staff {staff_id} "
                        f"({special_amount}) exceeds total staff share ({total_amount})"
                    )

        # 10. Pool-specific validation for JHS_EXTRA class teacher bonus
        if result.pool_code == "JHS_EXTRA":
            ct_bonus_shares = result.special_shares.get("class_teacher_bonus", {})
            declared_ct_bonus_total = sum(ct_bonus_shares.values(), Decimal("0.00"))

            split_defs = pool.get("distribution", {}).get("splits", [])
            ct_split = next(
                (s for s in split_defs if s.get("name") == "Class Teacher Bonus"),
                None,
            )

            if ct_split:
                ct_bonus_rate = self._rate(
                    ct_split.get("rate", ct_split.get("percentage", "0%"))
                )
                expected_ct_bonus_total = self.round_currency(
                    result.total_collected * ct_bonus_rate
                )
                ct_bonus_diff = abs(declared_ct_bonus_total - expected_ct_bonus_total)

                if ct_bonus_diff > self.MONEY_TOLERANCE:
                    errors.append(
                        f"Class teacher bonus total incorrect: expected {expected_ct_bonus_total}, "
                        f"got {declared_ct_bonus_total}"
                    )
                elif ct_bonus_diff > Decimal("0.00"):
                    warnings.append(
                        f"Minor class teacher bonus rounding difference: {ct_bonus_diff}"
                    )

        # 11. Metadata consistency checks
        for staff_id, metadata in (result.staff_metadata or {}).items():
            if staff_id not in result.staff_shares:
                warnings.append(
                    f"staff_metadata contains staff {staff_id} not present in staff_shares"
                )

            weight = metadata.get("attendance_weight")
            if weight is not None:
                try:
                    parsed_weight = Decimal(str(weight))
                    if parsed_weight < 0:
                        errors.append(
                            f"Negative attendance_weight in staff_metadata for staff {staff_id}: {parsed_weight}"
                        )
                except Exception:
                    errors.append(
                        f"Invalid attendance_weight in staff_metadata for staff {staff_id}: {weight}"
                    )

        # 12. Very small share warning
        for staff_id, amount in result.staff_shares.items():
            if Decimal("0.00") < amount < Decimal("0.01"):
                warnings.append(f"Very small share for staff {staff_id}: {amount}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )