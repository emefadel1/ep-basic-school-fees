# apps/fees/services/collection.py

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional

from django.db.models import Count, Q, Sum

from ..models import FeeCollection
from apps.school.models import SchoolClass


@dataclass
class ClassCollectionSummary:
    school_class_id: int
    class_code: str
    class_name: str
    pool_type: str

    total_students: int
    students_paid_full: int
    students_paid_partial: int
    students_unpaid: int
    students_exempt: int
    students_waived: int

    expected_amount: Decimal
    collected_amount: Decimal
    outstanding_amount: Decimal
    collection_rate: float


class CollectionService:
    def get_class_summary(
        self,
        session_id: int,
        class_id: int,
        pool_type: Optional[str] = None,
    ) -> List[ClassCollectionSummary]:
        """
        Get collection summary for one class, grouped by pool type.
        """
        school_class = SchoolClass.objects.get(id=class_id)

        qs = FeeCollection.objects.filter(
            session_id=session_id,
            school_class_id=class_id,
        )

        if pool_type:
            qs = qs.filter(pool_type=pool_type)

        summaries: List[ClassCollectionSummary] = []
        pool_types = qs.values_list("pool_type", flat=True).distinct()

        for pt in pool_types:
            pool_qs = qs.filter(pool_type=pt)

            aggregates = pool_qs.aggregate(
                total=Count("id"),
                paid_full=Count(
                    "id",
                    filter=Q(status=FeeCollection.PaymentStatus.PAID_FULL),
                ),
                paid_partial=Count(
                    "id",
                    filter=Q(status=FeeCollection.PaymentStatus.PAID_PARTIAL),
                ),
                unpaid=Count(
                    "id",
                    filter=Q(status=FeeCollection.PaymentStatus.UNPAID),
                ),
                exempt=Count(
                    "id",
                    filter=Q(status=FeeCollection.PaymentStatus.EXEMPT),
                ),
                waived=Count(
                    "id",
                    filter=Q(status=FeeCollection.PaymentStatus.WAIVED),
                ),
                expected=Sum("expected_amount"),
                collected=Sum("amount_paid"),
            )

            expected = aggregates["expected"] or Decimal("0.00")
            collected = aggregates["collected"] or Decimal("0.00")
            outstanding = expected - collected
            collection_rate = float((collected / expected) * Decimal("100")) if expected > 0 else 0.0

            summaries.append(
                ClassCollectionSummary(
                    school_class_id=school_class.id,
                    class_code=school_class.code,
                    class_name=school_class.name,
                    pool_type=pt,
                    total_students=aggregates["total"] or 0,
                    students_paid_full=aggregates["paid_full"] or 0,
                    students_paid_partial=aggregates["paid_partial"] or 0,
                    students_unpaid=aggregates["unpaid"] or 0,
                    students_exempt=aggregates["exempt"] or 0,
                    students_waived=aggregates["waived"] or 0,
                    expected_amount=expected,
                    collected_amount=collected,
                    outstanding_amount=outstanding,
                    collection_rate=collection_rate,
                )
            )

        return summaries

    def get_session_totals(self, session_id: int) -> Dict:
        """
        Get total collection stats for an entire session.
        """
        totals = FeeCollection.objects.filter(
            session_id=session_id
        ).aggregate(
            total_expected=Sum("expected_amount"),
            total_collected=Sum("amount_paid"),
            total_students=Count("student", distinct=True),
            fully_paid=Count(
                "id",
                filter=Q(status=FeeCollection.PaymentStatus.PAID_FULL),
            ),
            partially_paid=Count(
                "id",
                filter=Q(status=FeeCollection.PaymentStatus.PAID_PARTIAL),
            ),
            unpaid=Count(
                "id",
                filter=Q(status=FeeCollection.PaymentStatus.UNPAID),
            ),
            exempt=Count(
                "id",
                filter=Q(status=FeeCollection.PaymentStatus.EXEMPT),
            ),
            waived=Count(
                "id",
                filter=Q(status=FeeCollection.PaymentStatus.WAIVED),
            ),
        )

        by_pool = list(
            FeeCollection.objects.filter(session_id=session_id)
            .values("pool_type")
            .annotate(
                expected=Sum("expected_amount"),
                collected=Sum("amount_paid"),
                total_students=Count("student", distinct=True),
                paid_full=Count(
                    "id",
                    filter=Q(status=FeeCollection.PaymentStatus.PAID_FULL),
                ),
                paid_partial=Count(
                    "id",
                    filter=Q(status=FeeCollection.PaymentStatus.PAID_PARTIAL),
                ),
                unpaid=Count(
                    "id",
                    filter=Q(status=FeeCollection.PaymentStatus.UNPAID),
                ),
                exempt=Count(
                    "id",
                    filter=Q(status=FeeCollection.PaymentStatus.EXEMPT),
                ),
                waived=Count(
                    "id",
                    filter=Q(status=FeeCollection.PaymentStatus.WAIVED),
                ),
            )
            .order_by("pool_type")
        )

        for item in by_pool:
            item["expected"] = item["expected"] or Decimal("0.00")
            item["collected"] = item["collected"] or Decimal("0.00")
            item["outstanding"] = item["expected"] - item["collected"]
            item["collection_rate"] = (
                float((item["collected"] / item["expected"]) * Decimal("100"))
                if item["expected"] > 0 else 0.0
            )

        return {
            "totals": {
                "total_expected": totals["total_expected"] or Decimal("0.00"),
                "total_collected": totals["total_collected"] or Decimal("0.00"),
                "total_outstanding": (totals["total_expected"] or Decimal("0.00")) - (totals["total_collected"] or Decimal("0.00")),
                "total_students": totals["total_students"] or 0,
                "fully_paid": totals["fully_paid"] or 0,
                "partially_paid": totals["partially_paid"] or 0,
                "unpaid": totals["unpaid"] or 0,
                "exempt": totals["exempt"] or 0,
                "waived": totals["waived"] or 0,
            },
            "by_pool": by_pool,
        }

    def get_pool_total_for_session(self, session_id: int, pool_type: str) -> Dict:
        """
        Get collection totals for one pool in one session.
        Useful before fee distribution.
        """
        data = FeeCollection.objects.filter(
            session_id=session_id,
            pool_type=pool_type,
        ).aggregate(
            total_expected=Sum("expected_amount"),
            total_collected=Sum("amount_paid"),
            total_records=Count("id"),
            paid_full=Count(
                "id",
                filter=Q(status=FeeCollection.PaymentStatus.PAID_FULL),
            ),
            paid_partial=Count(
                "id",
                filter=Q(status=FeeCollection.PaymentStatus.PAID_PARTIAL),
            ),
            unpaid=Count(
                "id",
                filter=Q(status=FeeCollection.PaymentStatus.UNPAID),
            ),
            exempt=Count(
                "id",
                filter=Q(status=FeeCollection.PaymentStatus.EXEMPT),
            ),
            waived=Count(
                "id",
                filter=Q(status=FeeCollection.PaymentStatus.WAIVED),
            ),
        )

        total_expected = data["total_expected"] or Decimal("0.00")
        total_collected = data["total_collected"] or Decimal("0.00")

        return {
            "pool_type": pool_type,
            "total_expected": total_expected,
            "total_collected": total_collected,
            "total_outstanding": total_expected - total_collected,
            "total_records": data["total_records"] or 0,
            "paid_full": data["paid_full"] or 0,
            "paid_partial": data["paid_partial"] or 0,
            "unpaid": data["unpaid"] or 0,
            "exempt": data["exempt"] or 0,
            "waived": data["waived"] or 0,
        }