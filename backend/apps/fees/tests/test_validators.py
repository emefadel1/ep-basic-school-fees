# apps/fees/tests/test_validators.py

from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.fees.services.distribution import DistributionResult
from apps.fees.services.validators import DistributionValidator


def fake_get_pool_by_code(pool_code):
    return {
        "code": pool_code,
        "deductions": {
            "school_retention": {"rate": Decimal("0.10")},
            "administrative_fee": {"rate": Decimal("0.00") if pool_code == "GEN_STUDIES" else Decimal("0.03")},
        },
        "distribution": {
            "splits": [
                {
                    "name": "Class Teacher Bonus",
                    "rate": Decimal("0.10"),
                }
            ]
        },
    }


class DistributionValidatorTests(SimpleTestCase):
    @patch("apps.fees.services.validators.get_pool_by_code", side_effect=fake_get_pool_by_code)
    def test_validator_accepts_valid_general_studies_result(self, _mock_pool):
        result = DistributionResult(
            pool_code="GEN_STUDIES",
            total_collected=Decimal("1000.00"),
            school_retention=Decimal("100.00"),
            administrative_fee=Decimal("0.00"),
            distributable_amount=Decimal("900.00"),
            staff_shares={
                1: Decimal("450.00"),
                2: Decimal("450.00"),
            },
            special_shares={},
            staff_metadata={},
        )

        validation = DistributionValidator().validate(result, expected_total=Decimal("1000.00"))
        self.assertTrue(validation.is_valid)
        self.assertEqual(validation.errors, [])

    @patch("apps.fees.services.validators.get_pool_by_code", side_effect=fake_get_pool_by_code)
    def test_validator_rejects_bad_totals(self, _mock_pool):
        result = DistributionResult(
            pool_code="GEN_STUDIES",
            total_collected=Decimal("1000.00"),
            school_retention=Decimal("100.00"),
            administrative_fee=Decimal("0.00"),
            distributable_amount=Decimal("900.00"),
            staff_shares={
                1: Decimal("400.00"),
                2: Decimal("400.00"),
            },
            special_shares={},
            staff_metadata={},
        )

        validation = DistributionValidator().validate(result, expected_total=Decimal("1000.00"))
        self.assertFalse(validation.is_valid)
        self.assertTrue(any("Staff shares do not reconcile" in e for e in validation.errors))

    @patch("apps.fees.services.validators.get_pool_by_code", side_effect=fake_get_pool_by_code)
    def test_validator_checks_jhs_extra_bonus_total(self, _mock_pool):
        result = DistributionResult(
            pool_code="JHS_EXTRA",
            total_collected=Decimal("1000.00"),
            school_retention=Decimal("100.00"),
            administrative_fee=Decimal("30.00"),
            distributable_amount=Decimal("870.00"),
            staff_shares={
                10: Decimal("242.50"),
                11: Decimal("242.50"),
                12: Decimal("192.50"),
                99: Decimal("192.50"),
            },
            special_shares={
                "class_teacher_bonus": {
                    10: Decimal("50.00"),
                    11: Decimal("50.00"),
                }
            },
            staff_metadata={},
        )

        validation = DistributionValidator().validate(result, expected_total=Decimal("1000.00"))
        self.assertTrue(validation.is_valid)