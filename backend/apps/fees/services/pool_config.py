# apps/fees/services/pool_config.py

from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

import yaml
from django.conf import settings


POOL_CONFIG_PATH = Path(settings.BASE_DIR) / "config" / "fee_pools.yaml"


class PoolConfigError(Exception):
    """Raised when fee pool configuration is invalid."""


def parse_percentage(value: Any) -> Decimal:
    """
    Convert percentage-like values into Decimal ratios.

    Examples:
        "10%"  -> Decimal("0.10")
        "3%"   -> Decimal("0.03")
        "0.10" -> Decimal("0.10")
        0.10   -> Decimal("0.10")
        None   -> Decimal("0.00")
    """
    if value is None:
        return Decimal("0.00")

    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned.endswith("%"):
            return Decimal(cleaned[:-1]) / Decimal("100")
        return Decimal(cleaned)

    return Decimal(str(value))


def _require_mapping(value: Any, path: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise PoolConfigError(f"{path} must be a mapping/object")
    return value


def _require_list(value: Any, path: str) -> List[Any]:
    if not isinstance(value, list):
        raise PoolConfigError(f"{path} must be a list")
    return value


def _require_str(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PoolConfigError(f"{path} must be a non-empty string")
    return value.strip()


def _validate_non_negative_rate(rate: Decimal, path: str) -> None:
    if rate < Decimal("0.00"):
        raise PoolConfigError(f"{path} cannot be negative")


def _validate_pool_top_level(pool_key: str, pool: Dict[str, Any]) -> None:
    required_fields = [
        "name",
        "code",
        "description",
        "source_classes",
        "fee_field",
        "deductions",
        "distribution",
    ]

    for field in required_fields:
        if field not in pool:
            raise PoolConfigError(f"{pool_key}: missing required field '{field}'")

    _require_str(pool["name"], f"{pool_key}.name")
    _require_str(pool["code"], f"{pool_key}.code")
    _require_str(pool["description"], f"{pool_key}.description")
    _require_str(pool["fee_field"], f"{pool_key}.fee_field")

    source_classes = pool["source_classes"]
    if source_classes != "ALL" and not isinstance(source_classes, list):
        raise PoolConfigError(
            f"{pool_key}.source_classes must be 'ALL' or a list of class codes"
        )

    if isinstance(source_classes, list):
        for index, class_code in enumerate(source_classes):
            _require_str(class_code, f"{pool_key}.source_classes[{index}]")

    deductions = _require_mapping(pool["deductions"], f"{pool_key}.deductions")
    distribution = _require_mapping(pool["distribution"], f"{pool_key}.distribution")

    if "school_retention" not in deductions:
        raise PoolConfigError(f"{pool_key}.deductions.school_retention is required")

    if "administrative_fee" not in deductions:
        raise PoolConfigError(f"{pool_key}.deductions.administrative_fee is required")

    if "method" not in distribution:
        raise PoolConfigError(f"{pool_key}.distribution.method is required")


def _validate_deductions(pool_key: str, pool: Dict[str, Any]) -> Dict[str, Decimal]:
    deductions = pool["deductions"]

    school_retention = _require_mapping(
        deductions["school_retention"],
        f"{pool_key}.deductions.school_retention",
    )
    administrative_fee = _require_mapping(
        deductions["administrative_fee"],
        f"{pool_key}.deductions.administrative_fee",
    )

    school_rate = parse_percentage(school_retention.get("percentage"))
    admin_rate = parse_percentage(administrative_fee.get("percentage"))

    _validate_non_negative_rate(
        school_rate,
        f"{pool_key}.deductions.school_retention.percentage",
    )
    _validate_non_negative_rate(
        admin_rate,
        f"{pool_key}.deductions.administrative_fee.percentage",
    )

    if school_rate > Decimal("1.00"):
        raise PoolConfigError(
            f"{pool_key}.deductions.school_retention.percentage cannot exceed 100%"
        )

    if admin_rate > Decimal("1.00"):
        raise PoolConfigError(
            f"{pool_key}.deductions.administrative_fee.percentage cannot exceed 100%"
        )

    return {
        "school_retention_rate": school_rate,
        "administrative_fee_rate": admin_rate,
    }


def _validate_distribution(pool_key: str, pool: Dict[str, Any]) -> Dict[str, Any]:
    distribution = pool["distribution"]
    method = _require_str(distribution["method"], f"{pool_key}.distribution.method")

    allowed_methods = {"attendance_weighted", "fixed_split", "equal"}
    if method not in allowed_methods:
        raise PoolConfigError(
            f"{pool_key}.distribution.method must be one of {sorted(allowed_methods)}"
        )

    result = {"method": method}

    if method in {"attendance_weighted", "equal"}:
        eligible_staff = distribution.get("eligible_staff")
        if eligible_staff is None:
            raise PoolConfigError(
                f"{pool_key}.distribution.eligible_staff is required for {method}"
            )
        _require_str(eligible_staff, f"{pool_key}.distribution.eligible_staff")

    elif method == "fixed_split":
        splits = _require_list(distribution.get("splits"), f"{pool_key}.distribution.splits")
        if not splits:
            raise PoolConfigError(f"{pool_key}.distribution.splits cannot be empty")

        split_names = set()
        total_split_rate = Decimal("0.00")

        for index, split in enumerate(splits):
            split = _require_mapping(split, f"{pool_key}.distribution.splits[{index}]")

            name = _require_str(split.get("name"), f"{pool_key}.distribution.splits[{index}].name")
            recipients = _require_str(
                split.get("recipients"),
                f"{pool_key}.distribution.splits[{index}].recipients",
            )
            split_method = _require_str(
                split.get("split_method"),
                f"{pool_key}.distribution.splits[{index}].split_method",
            )

            if name in split_names:
                raise PoolConfigError(
                    f"{pool_key}.distribution.splits has duplicate split name '{name}'"
                )
            split_names.add(name)

            if split_method not in {"equal"}:
                raise PoolConfigError(
                    f"{pool_key}.distribution.splits[{index}].split_method must currently be 'equal'"
                )

            split_rate = parse_percentage(split.get("percentage"))
            _validate_non_negative_rate(
                split_rate,
                f"{pool_key}.distribution.splits[{index}].percentage",
            )

            if split_rate > Decimal("1.00"):
                raise PoolConfigError(
                    f"{pool_key}.distribution.splits[{index}].percentage cannot exceed 100%"
                )

            total_split_rate += split_rate

            # keep variables referenced so validation isn't "unused" conceptually
            _ = recipients

        deductions_info = _validate_deductions(pool_key, pool)
        total_configured = (
            deductions_info["school_retention_rate"]
            + deductions_info["administrative_fee_rate"]
            + total_split_rate
        )

        if total_configured > Decimal("1.00"):
            raise PoolConfigError(
                f"{pool_key}: deductions + splits exceed 100% "
                f"({(total_configured * Decimal('100'))}%)"
            )

        result["total_split_rate"] = total_split_rate

    return result


def _validate_special_rules(pool_key: str, pool: Dict[str, Any]) -> None:
    special_rules = pool.get("special_rules", [])
    if special_rules is None:
        return

    if not isinstance(special_rules, list):
        raise PoolConfigError(f"{pool_key}.special_rules must be a list")

    for index, rule in enumerate(special_rules):
        _require_str(rule, f"{pool_key}.special_rules[{index}]")


def _validate_cross_pool_rules(pools: Dict[str, Dict[str, Any]]) -> None:
    seen_codes = set()

    for pool_key, pool in pools.items():
        code = pool["code"]
        if code in seen_codes:
            raise PoolConfigError(f"Duplicate pool code found: {code}")
        seen_codes.add(code)

    # Known business checks for your current pool set
    required_codes = {"GEN_STUDIES", "JHS_EXTRA", "JHS3_EXTRA", "SATURDAY"}
    missing = required_codes - seen_codes
    if missing:
        raise PoolConfigError(f"Missing required pool codes: {sorted(missing)}")

    general = next(pool for pool in pools.values() if pool["code"] == "GEN_STUDIES")
    if general["distribution"]["method"] != "attendance_weighted":
        raise PoolConfigError("GEN_STUDIES must use distribution.method='attendance_weighted'")

    jhs_extra = next(pool for pool in pools.values() if pool["code"] == "JHS_EXTRA")
    if jhs_extra["distribution"]["method"] != "fixed_split":
        raise PoolConfigError("JHS_EXTRA must use distribution.method='fixed_split'")

    jhs3 = next(pool for pool in pools.values() if pool["code"] == "JHS3_EXTRA")
    if jhs3["distribution"]["method"] != "equal":
        raise PoolConfigError("JHS3_EXTRA must use distribution.method='equal'")

    saturday = next(pool for pool in pools.values() if pool["code"] == "SATURDAY")
    if saturday["distribution"]["method"] != "equal":
        raise PoolConfigError("SATURDAY must use distribution.method='equal'")


def validate_pool_definitions(data: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    if not isinstance(data, dict):
        raise PoolConfigError("fee_pools.yaml must contain a top-level mapping")

    if not data:
        raise PoolConfigError("fee_pools.yaml cannot be empty")

    normalized: Dict[str, Dict[str, Any]] = {}

    for pool_key, raw_pool in data.items():
        pool = _require_mapping(raw_pool, pool_key)

        _validate_pool_top_level(pool_key, pool)
        deductions_info = _validate_deductions(pool_key, pool)
        _validate_distribution(pool_key, pool)
        _validate_special_rules(pool_key, pool)

        normalized_pool = dict(pool)

        normalized_pool["deductions"] = dict(pool["deductions"])
        normalized_pool["deductions"]["school_retention"] = dict(
            pool["deductions"]["school_retention"]
        )
        normalized_pool["deductions"]["administrative_fee"] = dict(
            pool["deductions"]["administrative_fee"]
        )

        normalized_pool["deductions"]["school_retention"]["rate"] = deductions_info[
            "school_retention_rate"
        ]
        normalized_pool["deductions"]["administrative_fee"]["rate"] = deductions_info[
            "administrative_fee_rate"
        ]

        distribution = dict(pool["distribution"])
        splits = distribution.get("splits", [])
        normalized_splits = []

        for split in splits:
            split_copy = dict(split)
            split_copy["rate"] = parse_percentage(split_copy.get("percentage"))
            normalized_splits.append(split_copy)

        distribution["splits"] = normalized_splits
        normalized_pool["distribution"] = distribution

        normalized[pool_key] = normalized_pool

    _validate_cross_pool_rules(normalized)
    return normalized


@lru_cache(maxsize=1)
def load_pool_definitions() -> Dict[str, Dict[str, Any]]:
    if not POOL_CONFIG_PATH.exists():
        raise PoolConfigError(f"Pool config file not found: {POOL_CONFIG_PATH}")

    with POOL_CONFIG_PATH.open("r", encoding="utf-8") as file_obj:
        raw_data = yaml.safe_load(file_obj) or {}

    return validate_pool_definitions(raw_data)


def get_pool_by_code(pool_code: str) -> Dict[str, Any]:
    pools = load_pool_definitions()

    for _, pool in pools.items():
        if pool.get("code") == pool_code:
            return pool

    raise PoolConfigError(f"No pool found with code '{pool_code}'")


def get_all_pools() -> Dict[str, Dict[str, Any]]:
    return load_pool_definitions()


def clear_pool_cache() -> None:
    load_pool_definitions.cache_clear()