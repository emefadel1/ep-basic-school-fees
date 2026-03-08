# apps/fees/tests/test_distribution.py

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from apps.fees.services.distribution import FeeDistributionEngine


GEN_STUDIES_POOL = {
    "code": "GEN_STUDIES",
    "deductions": {
        "school_retention": {"rate": Decimal("0.10")},
        "administrative_fee": {"rate": Decimal("0.00")},
    },
    "distribution": {
        "method": "attendance_weighted",
    },
}

JHS_EXTRA_POOL = {
    "code": "JHS_EXTRA",
    "deductions": {
        "school_retention": {"rate": Decimal("0.10")},
        "administrative_fee": {"rate": Decimal("0.03")},
    },
    "distribution": {
        "method": "fixed_split",
        "splits": [
            {
                "name": "Class Teacher Bonus",
                "rate": Decimal("0.10"),
                "recipients": "jhs_class_teachers",
                "split_method": "equal",
            },
            {
                "name": "JHS Staff Share",
                "rate": Decimal("0.77"),
                "recipients": "all_jhs_staff",
                "split_method": "equal",
            },
        ],
    },
}

JHS3_POOL = {
    "code": "JHS3_EXTRA",
    "deductions": {
        "school_retention": {"rate": Decimal("0.10")},
        "administrative_fee": {"rate": Decimal("0.03")},
    },
    "distribution": {
        "method": "equal",
    },
}

SATURDAY_POOL = {
    "code": "SATURDAY",
    "deductions": {
        "school_retention": {"rate": Decimal("0.10")},
        "administrative_fee": {"rate": Decimal("0.03")},
    },
    "distribution": {
        "method": "equal",
    },
}


def fake_get_pool_by_code(pool_code):
    pools = {
        "GEN_STUDIES": GEN_STUDIES_POOL,
        "JHS_EXTRA": JHS_EXTRA_POOL,
        "JHS3_EXTRA": JHS3_POOL,
        "SATURDAY": SATURDAY_POOL,
    }
    return pools[pool_code]


class DistributionEngineTests(TestCase):
    def setUp(self):
        self.session = SimpleNamespace(date=date.today())
        self.engine = FeeDistributionEngine(session=self.session)

    @patch("apps.fees.services.distribution.get_pool_by_code", side_effect=fake_get_pool_by_code)
    def test_distribute_general_studies(self, _mock_pool):
        result = self.engine.distribute_general_studies(
            total_collected=Decimal("1000.00"),
            staff_attendance={
                1: "PRESENT",
                2: "LATE",
                3: "ABSENT",
            },
            headteacher_id=99,
        )

        self.assertEqual(result.school_retention, Decimal("100.00"))
        self.assertEqual(result.administrative_fee, Decimal("0.00"))
        self.assertEqual(result.distributable_amount, Decimal("900.00"))
        self.assertEqual(sum(result.staff_shares.values(), Decimal("0.00")), Decimal("900.00"))
        self.assertEqual(result.staff_shares[1], Decimal("360.00"))
        self.assertEqual(result.staff_shares[2], Decimal("180.00"))
        self.assertEqual(result.staff_shares[3], Decimal("0.00"))
        self.assertEqual(result.staff_shares[99], Decimal("360.00"))

    @patch("apps.fees.services.distribution.get_pool_by_code", side_effect=fake_get_pool_by_code)
    def test_distribute_jhs_extra(self, _mock_pool):
        result = self.engine.distribute_jhs_extra(
            total_collected=Decimal("1000.00"),
            jhs_class_teachers=[10, 11],
            all_jhs_staff=[10, 11, 12],
            headteacher_id=99,
        )

        self.assertEqual(result.school_retention, Decimal("100.00"))
        self.assertEqual(result.administrative_fee, Decimal("30.00"))
        self.assertEqual(result.distributable_amount, Decimal("870.00"))
        self.assertEqual(sum(result.staff_shares.values(), Decimal("0.00")), Decimal("870.00"))

        self.assertEqual(result.staff_shares[10], Decimal("242.50"))
        self.assertEqual(result.staff_shares[11], Decimal("242.50"))
        self.assertEqual(result.staff_shares[12], Decimal("192.50"))
        self.assertEqual(result.staff_shares[99], Decimal("192.50"))

        self.assertEqual(
            sum(result.special_shares["class_teacher_bonus"].values(), Decimal("0.00")),
            Decimal("100.00"),
        )

    @patch("apps.fees.services.distribution.get_pool_by_code", side_effect=fake_get_pool_by_code)
    def test_distribute_jhs3_extra(self, _mock_pool):
        result = self.engine.distribute_jhs3_extra(
            total_collected=Decimal("870.00"),
            all_jhs_staff=[10, 11, 12],
            headteacher_id=99,
        )

        self.assertEqual(result.school_retention, Decimal("87.00"))
        self.assertEqual(result.administrative_fee, Decimal("26.10"))
        self.assertEqual(
            sum(result.staff_shares.values(), Decimal("0.00")),
            result.distributable_amount,
        )

    @patch("apps.fees.services.distribution.get_pool_by_code", side_effect=fake_get_pool_by_code)
    def test_distribute_saturday(self, _mock_pool):
        result = self.engine.distribute_saturday(
            total_collected=Decimal("500.00"),
            saturday_attendees=[20, 21],
            headteacher_id=99,
        )

        self.assertEqual(result.school_retention, Decimal("50.00"))
        self.assertEqual(result.administrative_fee, Decimal("15.00"))
        self.assertEqual(result.distributable_amount, Decimal("435.00"))
        self.assertEqual(sum(result.staff_shares.values(), Decimal("0.00")), Decimal("435.00"))