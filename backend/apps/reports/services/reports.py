# apps/reports/services/reports.py

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.fees.models import Distribution, FeeCollection, PoolSummary, Session

User = get_user_model()


class ReportGenerator:
    """
    Report data builder for JSON and PDF output.
    """

    CATEGORY_LABELS = {
        "PRE_SCHOOL": "Pre-School",
        "PRIMARY": "Primary",
        "JHS": "JHS",
    }

    # Default term month windows. Adjust if your school uses different dates.
    TERM_MONTH_RANGES = {
        1: (1, 4),
        2: (5, 8),
        3: (9, 12),
    }

    def __init__(self, user):
        self.user = user
        self.is_bursar = str(getattr(user, "role", "")).upper() == "BURSAR"

    def generate_daily_report(self, report_date: date) -> Dict:
        session = Session.objects.filter(date=report_date).first()
        if not session:
            raise ValueError(f"No session found for {report_date}")

        collections = FeeCollection.objects.filter(session=session)
        distributions = Distribution.objects.filter(session=session).select_related("staff")
        pool_summaries = PoolSummary.objects.filter(session=session)

        return self._build_report_payload(
            title=f"Daily Collection Report - {report_date.strftime('%d %B %Y')}",
            start_date=report_date,
            end_date=report_date,
            collections=collections,
            distributions=distributions,
            pool_summaries=pool_summaries,
        )

    def generate_weekly_report(self, week_start: date) -> Dict:
        week_end = week_start + timedelta(days=6)
        return self._generate_range_report(
            start_date=week_start,
            end_date=week_end,
            title=f"Weekly Collection Report - {week_start:%d %b %Y} to {week_end:%d %b %Y}",
        )

    def generate_monthly_report(self, year: int, month: int) -> Dict:
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        return self._generate_range_report(
            start_date=start_date,
            end_date=end_date,
            title=f"Monthly Collection Report - {start_date:%B %Y}",
        )

    def generate_term_report(self, year: int, term: int) -> Dict:
        if term not in self.TERM_MONTH_RANGES:
            raise ValueError("term must be 1, 2, or 3")

        start_month, end_month = self.TERM_MONTH_RANGES[term]
        start_date = date(year, start_month, 1)

        if end_month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, end_month + 1, 1) - timedelta(days=1)

        report = self._generate_range_report(
            start_date=start_date,
            end_date=end_date,
            title=f"Term {term} Collection Report - {year}",
        )
        report["term"] = term
        report["year"] = year
        return report

    def generate_custom_report(self, start_date: date, end_date: date) -> Dict:
        return self._generate_range_report(
            start_date=start_date,
            end_date=end_date,
            title=f"Custom Collection Report - {start_date:%d %b %Y} to {end_date:%d %b %Y}",
        )

    def generate_staff_report(
        self,
        *,
        staff_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict:
        distributions = Distribution.objects.filter(staff_id=staff_id).select_related("staff", "session")

        if start_date:
            distributions = distributions.filter(session__date__gte=start_date)
        if end_date:
            distributions = distributions.filter(session__date__lte=end_date)

        if not distributions.exists():
            raise ValueError("No distributions found for this staff/date range")

        staff = distributions.first().staff
        all_distributions = distributions.order_by("-session__date", "pool_type")

        total_earned = sum((d.total_share for d in all_distributions), Decimal("0.00"))
        total_paid = sum((d.total_share for d in all_distributions if d.is_paid), Decimal("0.00"))
        total_pending = total_earned - total_paid

        items = []
        for dist in all_distributions:
            items.append({
                "id": dist.id,
                "session_id": dist.session_id,
                "session_date": dist.session.date,
                "pool_type": dist.pool_type,
                "base_share": dist.base_share,
                "adjusted_share": dist.adjusted_share,
                "special_share_amount": dist.special_share_amount,
                "total_share": dist.total_share,
                "attendance_status": dist.attendance_status or "N/A",
                "attendance_weight": dist.attendance_weight,
                "is_paid": dist.is_paid,
                "paid_at": dist.paid_at,
                "payment_reference": dist.payment_reference,
            })

        return {
            "title": f"Staff Earnings Report - {self._user_name(staff)}",
            "staff_id": staff.id,
            "staff_name": self._user_name(staff),
            "staff_role": self._user_role(staff),
            "date_range": {
                "start": start_date or min(d.session.date for d in all_distributions),
                "end": end_date or max(d.session.date for d in all_distributions),
            },
            "summary": {
                "total_earned": total_earned,
                "total_paid": total_paid,
                "total_pending": total_pending,
                "distribution_count": len(items),
            },
            "distributions": items,
            "generated_at": timezone.now(),
            "generated_by": self._user_name(self.user),
        }

    def _generate_range_report(self, start_date: date, end_date: date, title: str) -> Dict:
        sessions = Session.objects.filter(date__gte=start_date, date__lte=end_date)
        if not sessions.exists():
            raise ValueError(f"No sessions found between {start_date} and {end_date}")

        collections = FeeCollection.objects.filter(session__in=sessions)
        distributions = Distribution.objects.filter(session__in=sessions).select_related("staff")
        pool_summaries = PoolSummary.objects.filter(session__in=sessions)

        return self._build_report_payload(
            title=title,
            start_date=start_date,
            end_date=end_date,
            collections=collections,
            distributions=distributions,
            pool_summaries=pool_summaries,
        )

    def _build_report_payload(
        self,
        *,
        title: str,
        start_date: date,
        end_date: date,
        collections,
        distributions,
        pool_summaries,
    ) -> Dict:
        summary = self._get_collection_summary_for_queryset(collections)
        by_category = self._get_category_breakdown_for_queryset(collections)
        by_pool = self._get_pool_breakdown_for_queryset(pool_summaries)
        by_class = self._get_class_breakdown_for_queryset(collections)
        staff_distribution = self._get_staff_distribution_for_queryset(distributions)
        unpaid_students = self._get_unpaid_students_for_queryset(
            collections.filter(
                status__in=[
                    FeeCollection.PaymentStatus.UNPAID,
                    FeeCollection.PaymentStatus.PAID_PARTIAL,
                ]
            ).select_related("student", "school_class")
        )

        totals = {
            "classes_count": len({item["class_code"] for item in by_class}),
            "students_count": summary["total_students"],
        }

        pool_totals = {
            "collected": sum((item["total_collected"] for item in by_pool), Decimal("0.00")),
            "school_retention": sum((item["school_retention"] for item in by_pool), Decimal("0.00")),
            "staff_share": sum((item["distributed_to_staff"] for item in by_pool), Decimal("0.00")),
            "admin_fee": sum((item.get("administrative_fee", Decimal("0.00")) for item in by_pool), Decimal("0.00")),
        }

        distribution_totals = {
            "general_studies": sum(
                (item["pools"].get("GEN_STUDIES", Decimal("0.00")) for item in staff_distribution),
                Decimal("0.00"),
            ),
            "jhs_extra": sum(
                (item["pools"].get("JHS_EXTRA", Decimal("0.00")) for item in staff_distribution),
                Decimal("0.00"),
            ),
            "other": sum((item["other_pools"] for item in staff_distribution), Decimal("0.00")),
            "total": sum((item["total"] for item in staff_distribution), Decimal("0.00")),
        }

        total_unpaid_amount = sum((item["amount_owed"] for item in unpaid_students), Decimal("0.00"))

        return {
            "title": title,
            "date_range": {"start": start_date, "end": end_date},
            "summary": summary,
            "by_category": by_category,
            "by_pool": by_pool,
            "by_class": by_class,
            "staff_distribution": staff_distribution,
            "unpaid_students": unpaid_students,
            "totals": totals,
            "pool_totals": pool_totals,
            "distribution_totals": distribution_totals,
            "total_unpaid_amount": total_unpaid_amount,
            "generated_at": timezone.now(),
            "generated_by": self._user_name(self.user),
        }

    def _get_collection_summary_for_queryset(self, collections) -> Dict:
        totals = collections.aggregate(
            expected=Sum("expected_amount"),
            collected=Sum("amount_paid"),
            paid_count=Count("id", filter=Q(status=FeeCollection.PaymentStatus.PAID_FULL)),
            partial_count=Count("id", filter=Q(status=FeeCollection.PaymentStatus.PAID_PARTIAL)),
            unpaid_count=Count("id", filter=Q(status=FeeCollection.PaymentStatus.UNPAID)),
            total_students=Count("student", distinct=True),
        )

        expected = totals["expected"] or Decimal("0.00")
        collected = totals["collected"] or Decimal("0.00")

        return {
            "total_students_present": totals["total_students"] or 0,
            "total_students": totals["total_students"] or 0,
            "total_expected": expected,
            "total_collected": collected,
            "total_outstanding": expected - collected,
            "collection_rate": float((collected / expected) * Decimal("100")) if expected > 0 else 0.0,
            "students_paid_full": totals["paid_count"] or 0,
            "students_paid_partial": totals["partial_count"] or 0,
            "students_unpaid": totals["unpaid_count"] or 0,
        }

    def _get_category_breakdown_for_queryset(self, collections) -> List[Dict]:
        rows = (
            collections.values("school_class__category")
            .annotate(
                classes_count=Count("school_class", distinct=True),
                students_count=Count("student", distinct=True),
                expected=Sum("expected_amount"),
                collected=Sum("amount_paid"),
            )
            .order_by("school_class__category")
        )

        result = []
        for row in rows:
            expected = row["expected"] or Decimal("0.00")
            collected = row["collected"] or Decimal("0.00")
            rate = float((collected / expected) * Decimal("100")) if expected > 0 else 0.0
            category_code = row["school_class__category"] or "UNCATEGORIZED"

            result.append({
                "name": self.CATEGORY_LABELS.get(category_code, category_code.title().replace("_", " ")),
                "code": category_code,
                "classes_count": row["classes_count"] or 0,
                "students_count": row["students_count"] or 0,
                "expected": expected,
                "collected": collected,
                "rate": rate,
            })

        return result

    def _get_pool_breakdown_for_queryset(self, pool_summaries) -> List[Dict]:
        result = []

        for pool in pool_summaries.order_by("pool_type"):
            per_staff = (
                pool.total_distributed / pool.recipient_count
                if pool.recipient_count else Decimal("0.00")
            )

            pool_data = {
                "pool_name": pool.get_pool_type_display() if hasattr(pool, "get_pool_type_display") else pool.pool_type,
                "pool_code": pool.pool_type,
                "total_collected": pool.total_collected,
                "school_retention": pool.school_retention,
                "distributed_to_staff": pool.total_distributed,
                "recipient_count": pool.recipient_count,
                "per_staff": per_staff,
            }

            if self.is_bursar:
                pool_data["administrative_fee"] = pool.administrative_fee

            result.append(pool_data)

        return result

    def _get_class_breakdown_for_queryset(self, collections) -> List[Dict]:
        rows = (
            collections.values(
                "school_class_id",
                "school_class__code",
                "school_class__name",
            )
            .annotate(
                student_count=Count("student", distinct=True),
                expected=Sum("expected_amount"),
                collected=Sum("amount_paid"),
                unpaid_count=Count(
                    "id",
                    filter=Q(status=FeeCollection.PaymentStatus.UNPAID),
                ),
            )
            .order_by("school_class__code")
        )

        result = []
        for row in rows:
            expected = row["expected"] or Decimal("0.00")
            collected = row["collected"] or Decimal("0.00")
            rate = float((collected / expected) * Decimal("100")) if expected > 0 else 0.0

            result.append({
                "class_id": row["school_class_id"],
                "class_code": row["school_class__code"],
                "class_name": row["school_class__name"],
                "teacher_name": self._class_teacher_name(row["school_class_id"]),
                "student_count": row["student_count"] or 0,
                "expected": expected,
                "collected": collected,
                "rate": rate,
                "unpaid_count": row["unpaid_count"] or 0,
            })

        return result

    def _get_staff_distribution_for_queryset(self, distributions) -> List[Dict]:
        grouped: Dict[int, Dict] = {}

        for dist in distributions:
            staff_id = dist.staff_id

            if staff_id not in grouped:
                grouped[staff_id] = {
                    "staff_name": self._user_name(dist.staff),
                    "role": self._user_role(dist.staff),
                    "attendance": dist.attendance_status or "N/A",
                    "pools": {},
                    "other_pools": Decimal("0.00"),
                    "total": Decimal("0.00"),
                }

            total_share = dist.total_share
            grouped[staff_id]["pools"][dist.pool_type] = total_share
            grouped[staff_id]["total"] += total_share

            if dist.pool_type not in {"GEN_STUDIES", "JHS_EXTRA"}:
                grouped[staff_id]["other_pools"] += total_share

        return sorted(grouped.values(), key=lambda item: item["staff_name"].lower())

    def _get_unpaid_students_for_queryset(self, collections) -> List[Dict]:
        result = []

        for item in collections.order_by("school_class__code", "student__last_name", "student__first_name"):
            result.append({
                "student_name": self._student_name(item.student),
                "class_code": getattr(item.school_class, "code", ""),
                "amount_owed": item.amount_outstanding,
                "reason": item.unpaid_reason or item.status,
                "notes": item.unpaid_notes or "",
            })

        return result

    def _student_name(self, student) -> str:
        if hasattr(student, "get_full_name"):
            full_name = student.get_full_name()
            if full_name:
                return full_name

        first_name = getattr(student, "first_name", "")
        last_name = getattr(student, "last_name", "")
        full_name = f"{first_name} {last_name}".strip()
        return full_name or str(student)

    def _user_name(self, user) -> str:
        if hasattr(user, "get_full_name"):
            full_name = user.get_full_name()
            if full_name:
                return full_name
        return getattr(user, "username", str(user))

    def _user_role(self, user) -> str:
        if hasattr(user, "get_role_display"):
            try:
                return user.get_role_display()
            except Exception:
                pass
        return str(getattr(user, "role", "") or "")

    def _class_teacher_name(self, class_id: int) -> str:
        from apps.school.models import SchoolClass

        school_class = SchoolClass.objects.filter(id=class_id).first()
        if not school_class:
            return "-"

        for attr in ["teacher", "class_teacher", "assigned_teacher"]:
            teacher = getattr(school_class, attr, None)
            if teacher:
                return self._user_name(teacher)

        return "-"