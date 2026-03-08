# apps/fees/services/attendance_rules.py

from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml
from django.conf import settings


ATTENDANCE_RULES_PATH = Path(settings.BASE_DIR) / "config" / "attendance_rules.yaml"


class AttendanceRuleError(Exception):
    """Raised when attendance rule configuration is invalid."""


def parse_percentage(value: Any) -> Decimal:
    """
    Convert values like '50%' or '1.0' into Decimal ratios.

    Examples:
        '100%' -> Decimal('1.0')
        '50%'  -> Decimal('0.5')
        '0.5'  -> Decimal('0.5')
        None   -> Decimal('0.0')
    """
    if value is None:
        return Decimal("0.0")

    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned.endswith("%"):
            return Decimal(cleaned[:-1]) / Decimal("100")
        return Decimal(cleaned)

    return Decimal(str(value))


def _require_mapping(value: Any, path: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise AttendanceRuleError(f"{path} must be a mapping/object")
    return value


def _require_str(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AttendanceRuleError(f"{path} must be a non-empty string")
    return value.strip()


def validate_attendance_rules(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize attendance rules loaded from YAML.
    """
    if not isinstance(data, dict):
        raise AttendanceRuleError("attendance_rules.yaml must contain a top-level mapping")

    statuses = data.get("Attendance_Statuses")
    if not isinstance(statuses, dict) or not statuses:
        raise AttendanceRuleError("Attendance_Statuses must be a non-empty mapping")

    normalized_statuses: Dict[str, Dict[str, Any]] = {}

    for key, raw_rule in statuses.items():
        rule = _require_mapping(raw_rule, f"Attendance_Statuses.{key}")

        code = _require_str(rule.get("code"), f"Attendance_Statuses.{key}.code")
        description = _require_str(
            rule.get("description"),
            f"Attendance_Statuses.{key}.description",
        )

        if code != key:
            raise AttendanceRuleError(
                f"Attendance_Statuses.{key}.code must match key '{key}'"
            )

        share_rate = parse_percentage(rule.get("share_percentage"))
        if share_rate < Decimal("0.0") or share_rate > Decimal("1.0"):
            raise AttendanceRuleError(
                f"Attendance_Statuses.{key}.share_percentage must be between 0% and 100%"
            )

        requires_documentation = bool(rule.get("requires_documentation", False))
        requires_approval = bool(rule.get("requires_approval", False))

        if requires_documentation and not rule.get("documentation_type"):
            raise AttendanceRuleError(
                f"Attendance_Statuses.{key}.documentation_type is required when "
                f"requires_documentation=true"
            )

        late_threshold_minutes = rule.get("late_threshold_minutes")
        if late_threshold_minutes is not None:
            try:
                late_threshold_minutes = int(late_threshold_minutes)
            except (TypeError, ValueError):
                raise AttendanceRuleError(
                    f"Attendance_Statuses.{key}.late_threshold_minutes must be an integer"
                )

            if late_threshold_minutes < 0:
                raise AttendanceRuleError(
                    f"Attendance_Statuses.{key}.late_threshold_minutes cannot be negative"
                )

        grace_period_days = rule.get("grace_period_days")
        if grace_period_days is not None:
            try:
                grace_period_days = int(grace_period_days)
            except (TypeError, ValueError):
                raise AttendanceRuleError(
                    f"Attendance_Statuses.{key}.grace_period_days must be an integer"
                )

            if grace_period_days < 0:
                raise AttendanceRuleError(
                    f"Attendance_Statuses.{key}.grace_period_days cannot be negative"
                )

        normalized_statuses[key] = {
            **rule,
            "code": code,
            "description": description,
            "share_rate": share_rate,
            "requires_documentation": requires_documentation,
            "requires_approval": requires_approval,
            "late_threshold_minutes": late_threshold_minutes,
            "grace_period_days": grace_period_days,
        }

    return {"Attendance_Statuses": normalized_statuses}


@lru_cache(maxsize=1)
def load_attendance_rules() -> Dict[str, Any]:
    if not ATTENDANCE_RULES_PATH.exists():
        raise AttendanceRuleError(
            f"Attendance rules file not found: {ATTENDANCE_RULES_PATH}"
        )

    with ATTENDANCE_RULES_PATH.open("r", encoding="utf-8") as file_obj:
        raw_data = yaml.safe_load(file_obj) or {}

    return validate_attendance_rules(raw_data)


def get_all_attendance_rules() -> Dict[str, Any]:
    return load_attendance_rules()["Attendance_Statuses"]


def get_attendance_rule(status_code: str) -> Dict[str, Any]:
    rules = get_all_attendance_rules()
    if status_code not in rules:
        raise AttendanceRuleError(f"Unknown attendance status: {status_code}")
    return rules[status_code]


def get_attendance_weight(status_code: str) -> Decimal:
    return get_attendance_rule(status_code)["share_rate"]


def requires_documentation(status_code: str) -> bool:
    return bool(get_attendance_rule(status_code).get("requires_documentation", False))


def requires_approval(status_code: str) -> bool:
    return bool(get_attendance_rule(status_code).get("requires_approval", False))


def get_late_threshold_minutes(default: int = 30) -> int:
    rule = get_attendance_rule("LATE")
    value = rule.get("late_threshold_minutes")
    return int(value) if value is not None else default


def clear_attendance_rules_cache() -> None:
    load_attendance_rules.cache_clear()