# apps/fees/tests/test_attendance_rules.py

from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.fees.services import attendance_rules


VALID_ATTENDANCE_YAML = """
Attendance_Statuses:
  PRESENT:
    code: "PRESENT"
    description: "Staff is present and teaching"
    share_percentage: 100%
    requires_documentation: false

  LATE:
    code: "LATE"
    description: "Staff arrived late"
    share_percentage: 50%
    requires_documentation: false
    late_threshold_minutes: 30

  SICK:
    code: "SICK"
    description: "Staff is sick"
    share_percentage: 50%
    requires_documentation: true
    documentation_type: "sick_note"
    grace_period_days: 3

  PERMISSION:
    code: "PERMISSION"
    description: "Staff has approved permission"
    share_percentage: 50%
    requires_documentation: true
    documentation_type: "permission_form"
    requires_approval: true

  OFFICIAL_DUTY:
    code: "OFFICIAL_DUTY"
    description: "Staff on official school duty"
    share_percentage: 100%
    requires_documentation: true
    documentation_type: "duty_letter"

  ABSENT:
    code: "ABSENT"
    description: "Unexcused absence"
    share_percentage: 0%
    requires_documentation: false
"""


class AttendanceRulesTests(SimpleTestCase):
    def tearDown(self):
        attendance_rules.clear_attendance_rules_cache()
        super().tearDown()

    def test_load_attendance_rules_success(self):
        with TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "attendance_rules.yaml"
            yaml_path.write_text(VALID_ATTENDANCE_YAML, encoding="utf-8")

            with patch.object(attendance_rules, "ATTENDANCE_RULES_PATH", yaml_path):
                attendance_rules.clear_attendance_rules_cache()
                rules = attendance_rules.load_attendance_rules()

        self.assertIn("PRESENT", rules["Attendance_Statuses"])
        self.assertEqual(
            rules["Attendance_Statuses"]["PRESENT"]["share_rate"],
            Decimal("1"),
        )
        self.assertEqual(
            rules["Attendance_Statuses"]["LATE"]["share_rate"],
            Decimal("0.5"),
        )

    def test_get_late_threshold_minutes(self):
        with TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "attendance_rules.yaml"
            yaml_path.write_text(VALID_ATTENDANCE_YAML, encoding="utf-8")

            with patch.object(attendance_rules, "ATTENDANCE_RULES_PATH", yaml_path):
                attendance_rules.clear_attendance_rules_cache()
                threshold = attendance_rules.get_late_threshold_minutes()

        self.assertEqual(threshold, 30)

    def test_invalid_percentage_fails(self):
        bad_yaml = """
Attendance_Statuses:
  PRESENT:
    code: "PRESENT"
    description: "Present"
    share_percentage: 150%
    requires_documentation: false
"""
        with TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "attendance_rules.yaml"
            yaml_path.write_text(bad_yaml, encoding="utf-8")

            with patch.object(attendance_rules, "ATTENDANCE_RULES_PATH", yaml_path):
                attendance_rules.clear_attendance_rules_cache()
                with self.assertRaises(attendance_rules.AttendanceRuleError):
                    attendance_rules.load_attendance_rules()