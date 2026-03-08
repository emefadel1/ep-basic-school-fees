# apps/fees/tests/test_pool_config.py

from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.fees.services import pool_config


VALID_POOLS_YAML = """
Pool_1_General_Studies:
  name: "General Studies"
  code: "GEN_STUDIES"
  description: "Daily studies fee from all classes"
  source_classes: ALL
  fee_field: "daily_fee"
  deductions:
    school_retention:
      percentage: 10%
    administrative_fee:
      percentage: 0%
  distribution:
    method: "attendance_weighted"
    eligible_staff: "all_teaching_staff"
    include_headteacher: true
    attendance_rules: true
  special_rules: []

Pool_2_JHS_Extra:
  name: "JHS Extra Classes"
  code: "JHS_EXTRA"
  description: "Extra class fees from JHS 1, 2, and 3"
  source_classes: [B7, B8, B9]
  fee_field: "jhs_extra_fee"
  deductions:
    school_retention:
      percentage: 10%
    administrative_fee:
      percentage: 3%
  distribution:
    method: "fixed_split"
    splits:
      - name: "Class Teacher Bonus"
        percentage: 10%
        recipients: "jhs_class_teachers"
        split_method: "equal"
      - name: "JHS Staff Share"
        percentage: 77%
        recipients: "all_jhs_staff"
        split_method: "equal"
  special_rules:
    - "Class teachers receive both CT bonus and staff share"

Pool_3_JHS3_Extra:
  name: "JHS 3 Extra"
  code: "JHS3_EXTRA"
  description: "Additional preparation fee for JHS 3 only"
  source_classes: [B9]
  fee_field: "jhs3_extra_fee"
  deductions:
    school_retention:
      percentage: 10%
    administrative_fee:
      percentage: 3%
  distribution:
    method: "equal"
    eligible_staff: "all_jhs_staff"
    include_headteacher: true
    attendance_rules: false

Pool_4_Saturday:
  name: "Saturday Classes"
  code: "SATURDAY"
  description: "Saturday extra class fees"
  source_classes: [B7, B8, B9]
  fee_field: "saturday_fee"
  deductions:
    school_retention:
      percentage: 10%
    administrative_fee:
      percentage: 3%
  distribution:
    method: "equal"
    eligible_staff: "saturday_attendees"
    include_headteacher: true
    attendance_rules: false
"""


class PoolConfigTests(SimpleTestCase):
    def tearDown(self):
        pool_config.clear_pool_cache()
        super().tearDown()

    def test_load_pool_definitions_success(self):
        with TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "fee_pools.yaml"
            yaml_path.write_text(VALID_POOLS_YAML, encoding="utf-8")

            with patch.object(pool_config, "POOL_CONFIG_PATH", yaml_path):
                pool_config.clear_pool_cache()
                pools = pool_config.load_pool_definitions()

        self.assertIn("Pool_1_General_Studies", pools)
        self.assertEqual(pools["Pool_1_General_Studies"]["code"], "GEN_STUDIES")
        self.assertEqual(
            pools["Pool_1_General_Studies"]["deductions"]["school_retention"]["rate"],
            Decimal("0.10"),
        )
        self.assertEqual(
            pools["Pool_2_JHS_Extra"]["distribution"]["splits"][0]["rate"],
            Decimal("0.10"),
        )

    def test_get_pool_by_code(self):
        with TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "fee_pools.yaml"
            yaml_path.write_text(VALID_POOLS_YAML, encoding="utf-8")

            with patch.object(pool_config, "POOL_CONFIG_PATH", yaml_path):
                pool_config.clear_pool_cache()
                pool = pool_config.get_pool_by_code("SATURDAY")

        self.assertEqual(pool["name"], "Saturday Classes")

    def test_duplicate_pool_code_fails(self):
        bad_yaml = """
Pool_A:
  name: "A"
  code: "GEN_STUDIES"
  description: "A"
  source_classes: ALL
  fee_field: "daily_fee"
  deductions:
    school_retention:
      percentage: 10%
    administrative_fee:
      percentage: 0%
  distribution:
    method: "attendance_weighted"
    eligible_staff: "all_teaching_staff"

Pool_B:
  name: "B"
  code: "GEN_STUDIES"
  description: "B"
  source_classes: [B7]
  fee_field: "x"
  deductions:
    school_retention:
      percentage: 10%
    administrative_fee:
      percentage: 3%
  distribution:
    method: "equal"
    eligible_staff: "all_jhs_staff"
"""
        with TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "fee_pools.yaml"
            yaml_path.write_text(bad_yaml, encoding="utf-8")

            with patch.object(pool_config, "POOL_CONFIG_PATH", yaml_path):
                pool_config.clear_pool_cache()
                with self.assertRaises(pool_config.PoolConfigError):
                    pool_config.load_pool_definitions()