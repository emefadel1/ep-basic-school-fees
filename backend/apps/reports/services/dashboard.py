# apps/reports/services/dashboard.py

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum, Q
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.fees.models import Distribution, FeeCollection, Session, StaffAttendance, StudentArrears
from apps.school.models import SchoolClass


def normalize_role(user) -> str:
    return str(getattr(user, "role", "")).replace("_", "").replace(" ", "").upper()


class DashboardService:
    def __init__(self, user):
        self.user = user
        self.role = normalize_role(user)

    def get_dashboard(self) -> dict:
        if self.role == "TEACHER":
            return self.get_teacher_dashboard()
        if self.role == "CONTACTPERSON":
            return self.get_contact_dashboard()
        if self.role == "HEADTEACHER":
            return self.get_headteacher_dashboard()
        if self.role == "BURSAR":
            return self.get_bursar_dashboard()
	if self.role == "BOARD":
    	return self.get_board_dashboard()
        raise ValueError("Unsupported dashboard role")

    def get_current_session(self):
        return Session.objects.order_by("-date").first()

    def _get_user_class(self):
        for attr in ["assigned_class", "school_class", "class_assigned"]:
            value = getattr(self.user, attr, None)
            if value:
                return value
        return None

    def _get_user_category(self):
        for attr in ["assigned_category", "category"]:
            value = getattr(self.user, attr, None)
            if value:
                return str(value)
        return None

    def _student_name(self, student):
        if hasattr(student, "full_name"):
            return student.full_name
        first_name = getattr(student, "first_name", "")
        last_name = getattr(student, "last_name", "")
        return f"{first_name} {last_name}".strip() or str(student)

    def _teacher_name_for_class(self, school_class):
        for attr in ["teacher", "class_teacher", "assigned_teacher"]:
            teacher = getattr(school_class, attr, None)
            if teacher:
                if hasattr(teacher, "get_full_name") and teacher.get_full_name():
                    return teacher.get_full_name()
                return getattr(teacher, "username", "-")
        return "-"

    def _session_label(self, session):
        if not session:
            return "NO SESSION"
        return session.status

    def _collection_rate(self, collected, expected):
        if not expected or expected <= 0:
            return 0.0
        return float((collected / expected) * Decimal("100"))

    def _user_earnings_summary(self):
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        qs = Distribution.objects.filter(staff=self.user)

        def total_between(start_date):
            return sum(
                (
                    dist.total_share
                    for dist in qs.filter(session__date__gte=start_date).select_related("session")
                ),
                Decimal("0.00"),
            )

        today_total = sum(
            (dist.total_share for dist in qs.filter(session__date=today)),
            Decimal("0.00"),
        )
        week_total = total_between(week_start)
        month_total = total_between(month_start)
        pending_payment = sum(
            (dist.total_share for dist in qs.filter(is_paid=False)),
            Decimal("0.00"),
        )

        return {
            "today_share": today_total,
            "week_total": week_total,
            "month_total": month_total,
            "pending_payment": pending_payment,
        }

    def get_teacher_dashboard(self) -> dict:
        session = self.get_current_session()
        school_class = self._get_user_class()

        collections = FeeCollection.objects.none()
        if session and school_class:
            collections = FeeCollection.objects.filter(
                session=session,
                school_class=school_class,
            ).select_related("student")

        totals = collections.aggregate(
            total_students=Count("student", distinct=True),
            paid_full=Count("id", filter=Q(status=FeeCollection.PaymentStatus.PAID_FULL)),
            paid_partial=Count("id", filter=Q(status=FeeCollection.PaymentStatus.PAID_PARTIAL)),
            unpaid=Count("id", filter=Q(status=FeeCollection.PaymentStatus.UNPAID)),
            expected=Sum("expected_amount"),
            collected=Sum("amount_paid"),
        )

        expected = totals["expected"] or Decimal("0.00")
        collected = totals["collected"] or Decimal("0.00")
        total_students = totals["total_students"] or 0
        progress_done = (totals["paid_full"] or 0) + (totals["paid_partial"] or 0)

        class_table = []
        for item in collections.order_by("student__last_name", "student__first_name")[:100]:
            class_table.append({
                "id": item.id,
                "student_id": item.student_id,
                "student_name": self._student_name(item.student),
                "pool_type": item.pool_type,
                "expected_fee": item.expected_amount,
                "amount_paid": item.amount_paid,
                "status": item.status,
            })

        recent_activity = []
        for item in collections.order_by("-updated_at")[:5]:
            recent_activity.append({
                "student_name": self._student_name(item.student),
                "amount_paid": item.amount_paid,
                "status": item.status,
                "updated_at": item.updated_at,
            })

        return {
            "dashboard_type": "teacher",
            "summary": {
                "session_status": self._session_label(session),
                "submission_status": "In Progress" if session and session.status == Session.Status.OPEN else self._session_label(session),
                "collection_progress": f"{progress_done}/{total_students} students" if total_students else "0/0 students",
                "collection_rate": self._collection_rate(collected, expected),
            },
            "quick_actions": {
                "can_record_fees": bool(session and session.status == Session.Status.OPEN),
                "can_view_students": bool(school_class),
                "can_view_summary": bool(session),
            },
            "class_collection_table": class_table,
            "my_earnings": self._user_earnings_summary(),
            "recent_activity": recent_activity,
            "generated_at": timezone.now(),
        }

    def get_contact_dashboard(self) -> dict:
        session = self.get_current_session()
        category = self._get_user_category()
        classes = SchoolClass.objects.filter(is_active=True)
        if category:
            classes = classes.filter(category=category)

        collections = FeeCollection.objects.none()
        if session:
            collections = FeeCollection.objects.filter(
                session=session,
                school_class__in=classes,
            ).select_related("school_class")

        classes_summary = []
        for school_class in classes.order_by("sort_order", "code"):
            class_qs = collections.filter(school_class=school_class)
            expected = class_qs.aggregate(v=Sum("expected_amount"))["v"] or Decimal("0.00")
            collected = class_qs.aggregate(v=Sum("amount_paid"))["v"] or Decimal("0.00")
            students_count = school_class.students.filter(status="ACTIVE").count() if hasattr(school_class, "students") else 0

            classes_summary.append({
                "class_id": school_class.id,
                "class_code": school_class.code,
                "class_name": school_class.name,
                "teacher_name": self._teacher_name_for_class(school_class),
                "students_count": students_count,
                "expected": expected,
                "collected": collected,
                "rate": self._collection_rate(collected, expected),
            })

        by_pool = list(
            collections.values("pool_type").annotate(
                expected=Sum("expected_amount"),
                collected=Sum("amount_paid"),
            ).order_by("pool_type")
        )

        unpaid_breakdown = list(
            collections.filter(status=FeeCollection.PaymentStatus.UNPAID)
            .values("unpaid_reason")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        total_students = sum(item["students_count"] for item in classes_summary)
        total_expected = sum((item["expected"] for item in classes_summary), Decimal("0.00"))
        total_collected = sum((item["collected"] for item in classes_summary), Decimal("0.00"))

        return {
            "dashboard_type": "contact",
            "category_overview": {
                "category_name": category or "ALL",
                "total_classes": classes.count(),
                "total_students": total_students,
                "today_collection": total_collected,
                "collection_rate": self._collection_rate(total_collected, total_expected),
            },
            "classes_summary_table": classes_summary,
            "pool_breakdown": by_pool,
            "unpaid_students_alert": {
                "count": collections.filter(status=FeeCollection.PaymentStatus.UNPAID).count(),
                "breakdown_by_reason": unpaid_breakdown,
            },
            "generated_at": timezone.now(),
        }

    def get_headteacher_dashboard(self) -> dict:
        session = self.get_current_session()
        collections = FeeCollection.objects.filter(session=session) if session else FeeCollection.objects.none()

        totals = collections.aggregate(
            total_students=Count("student", distinct=True),
            total_collected=Sum("amount_paid"),
            total_expected=Sum("expected_amount"),
        )

        total_students = totals["total_students"] or 0
        total_collected = totals["total_collected"] or Decimal("0.00")
        total_expected = totals["total_expected"] or Decimal("0.00")

        category_breakdown = []
        for row in collections.values("school_class__category").annotate(
            expected=Sum("expected_amount"),
            collected=Sum("amount_paid"),
        ):
            expected = row["expected"] or Decimal("0.00")
            collected = row["collected"] or Decimal("0.00")
            category_breakdown.append({
                "category": row["school_class__category"],
                "amount": collected,
                "rate": self._collection_rate(collected, expected),
            })

        pool_distribution_chart = list(
            collections.values("pool_type").annotate(
                total=Sum("amount_paid")
            ).order_by("pool_type")
        )

        attendance_qs = StaffAttendance.objects.filter(session=session) if session else StaffAttendance.objects.none()
        attendance_overview = {
            "present_count": attendance_qs.filter(status=StaffAttendance.Status.PRESENT).count(),
            "late_count": attendance_qs.filter(status=StaffAttendance.Status.LATE).count(),
            "absent_count": attendance_qs.filter(status=StaffAttendance.Status.ABSENT).count(),
            "on_leave_count": attendance_qs.filter(
                status__in=[StaffAttendance.Status.SICK, StaffAttendance.Status.PERMISSION, StaffAttendance.Status.OFFICIAL_DUTY]
            ).count(),
        }

        week_start = timezone.now().date() - timedelta(days=6)
        weekly_trend = []
        for s in Session.objects.filter(date__gte=week_start).order_by("date"):
            session_total = FeeCollection.objects.filter(session=s).aggregate(v=Sum("amount_paid"))["v"] or Decimal("0.00")
            weekly_trend.append({
                "date": s.date,
                "collected": session_total,
            })

        return {
            "dashboard_type": "headteacher",
            "school_wide_summary": {
                "total_students": total_students,
                "total_teachers": 0,
                "today_collection": total_collected,
                "collection_rate": self._collection_rate(total_collected, total_expected),
            },
            "category_breakdown": category_breakdown,
            "pool_distribution_chart": pool_distribution_chart,
            "session_management": {
                "session_id": session.id if session else None,
                "status": session.status if session else "NO SESSION",
                "can_open_session": bool(session and session.status == Session.Status.DRAFT),
                "can_submit_for_approval": bool(session and session.status == Session.Status.OPEN),
            },
            "staff_attendance_overview": attendance_overview,
            "weekly_trend_chart": weekly_trend,
            "quick_reports": {
                "today": True,
                "week": True,
                "month": True,
            },
            "generated_at": timezone.now(),
        }

    def get_bursar_dashboard(self) -> dict:
        session = self.get_current_session()
        collections = FeeCollection.objects.filter(session=session) if session else FeeCollection.objects.none()
        distributions = Distribution.objects.filter(session=session) if session else Distribution.objects.none()

        total_collection = collections.aggregate(v=Sum("amount_paid"))["v"] or Decimal("0.00")

        school_retention = Decimal("0.00")
        admin_fees = Decimal("0.00")
        if hasattr(self.user, "__class__"):
            try:
                from apps.school.models import SchoolSettings
                settings_obj = SchoolSettings.get_settings()
                school_retention = total_collection * (settings_obj.school_retention_percentage / Decimal("100"))
                admin_fees = total_collection * (settings_obj.admin_fee_percentage / Decimal("100"))
            except Exception:
                school_retention = Decimal("0.00")
                admin_fees = Decimal("0.00")

        pending_approvals = list(
            Session.objects.filter(status=Session.Status.PENDING_APPROVAL)
            .order_by("-date")
            .values("id", "date", "status", "submitted_at")[:10]
        )

        pending_staff_payments = distributions.filter(is_paid=False).count()
        awaiting_distribution = Session.objects.filter(status=Session.Status.APPROVED).count()

        monthly_collection_trend = []
        for s in Session.objects.order_by("-date")[:10]:
            val = FeeCollection.objects.filter(session=s).aggregate(v=Sum("amount_paid"))["v"] or Decimal("0.00")
            monthly_collection_trend.append({
                "date": s.date,
                "collected": val,
            })
        monthly_collection_trend.reverse()

        outstanding_arrears = StudentArrears.objects.aggregate(
            total=Sum("amount_owed")
        )["total"] or Decimal("0.00")

        audit_preview = list(
            AuditLog.objects.order_by("-timestamp").values(
                "action", "table_name", "notes", "timestamp"
            )[:10]
        )

        return {
            "dashboard_type": "bursar",
            "admin_summary": {
                "total_collection": total_collection,
                "school_retention": school_retention,
                "admin_fees": admin_fees,
                "staff_distribution": sum((d.total_share for d in distributions), Decimal("0.00")),
            },
            "pending_approvals": pending_approvals,
            "distribution_status": {
                "awaiting_distribution": awaiting_distribution,
                "pending_staff_payments": pending_staff_payments,
                "completed_distributions": distributions.count(),
            },
            "financial_summary": {
                "monthly_collection_trend": monthly_collection_trend,
                "outstanding_arrears": outstanding_arrears,
            },
            "audit_log_preview": audit_preview,
            "quick_actions": {
                "approve_collections": True,
                "run_distribution": True,
                "generate_reports": True,
                "manage_users": True,
                "system_settings": True,
            },
            "generated_at": timezone.now(),
        }
def get_board_dashboard(self) -> dict:
    today = timezone.now().date()
    month_start = today.replace(day=1)

    sessions = Session.objects.all()
    collections = FeeCollection.objects.all()
    distributions = Distribution.objects.all()

    total_students = collections.values("student").distinct().count()
    total_collection = collections.aggregate(v=Sum("amount_paid"))["v"] or Decimal("0.00")
    monthly_collection = collections.filter(
        session__date__gte=month_start
    ).aggregate(v=Sum("amount_paid"))["v"] or Decimal("0.00")

    school_retention_total = Decimal("0.00")
    try:
        from apps.school.models import SchoolSettings
        settings_obj = SchoolSettings.get_settings()
        school_retention_total = total_collection * (
            settings_obj.school_retention_percentage / Decimal("100")
        )
    except Exception:
        pass

    category_breakdown = []
    for row in collections.values("school_class__category").annotate(
        expected=Sum("expected_amount"),
        collected=Sum("amount_paid"),
    ).order_by("school_class__category"):
        expected = row["expected"] or Decimal("0.00")
        collected = row["collected"] or Decimal("0.00")
        rate = self._collection_rate(collected, expected)
        category_breakdown.append({
            "category": row["school_class__category"],
            "collected": collected,
            "rate": rate,
        })

    monthly_trend = []
    for s in Session.objects.order_by("-date")[:12]:
        session_total = FeeCollection.objects.filter(session=s).aggregate(
            v=Sum("amount_paid")
        )["v"] or Decimal("0.00")
        monthly_trend.append({
            "date": s.date,
            "collected": session_total,
        })
    monthly_trend.reverse()

    arrears_summary = {
        "total_outstanding": StudentArrears.objects.aggregate(
            v=Sum("amount_owed")
        )["v"] or Decimal("0.00"),
        "pending_count": StudentArrears.objects.filter(status="PENDING").count(),
        "partial_count": StudentArrears.objects.filter(status="PARTIAL").count(),
    }

    staff_earnings_summary = list(
        distributions.values("staff__username")
        .annotate(total=Sum("adjusted_share") + Sum("special_share_amount"))
        .order_by("-total")[:10]
    )

    recent_audit = list(
        AuditLog.objects.order_by("-timestamp").values(
            "action", "table_name", "notes", "timestamp"
        )[:10]
    )

    return {
        "dashboard_type": "board",
        "board_summary": {
            "total_students": total_students,
            "total_collection": total_collection,
            "monthly_collection": monthly_collection,
            "school_retention_total": school_retention_total,
        },
        "category_breakdown": category_breakdown,
        "monthly_trend_chart": monthly_trend,
        "arrears_summary": arrears_summary,
        "staff_earnings_summary": staff_earnings_summary,
        "recent_audit_log": recent_audit,
        "generated_at": timezone.now(),
    }