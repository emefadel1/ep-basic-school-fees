# apps/reports/tests/test_api.py

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.audit.models import AuditLog
from apps.reports.api.views import (
    CustomReportView,
    DailyReportView,
    MonthlyReportView,
    StaffReportView,
    TermReportView,
    WeeklyReportView,
)

User = get_user_model()


def make_user(username: str, role: str):
    user = User.objects.create_user(
        username=username,
        password="testpass123",
    )
    user.role = role
    user.save(update_fields=["role"])
    return user


def sample_report_payload(title="Sample Report"):
    return {
        "title": title,
        "date_range": {
            "start": "2026-03-01",
            "end": "2026-03-08",
        },
        "summary": {
            "total_students_present": 20,
            "total_students": 20,
            "total_expected": "100.00",
            "total_collected": "80.00",
            "total_outstanding": "20.00",
            "collection_rate": 80.0,
            "students_paid_full": 10,
            "students_paid_partial": 5,
            "students_unpaid": 5,
        },
        "by_category": [],
        "by_pool": [],
        "by_class": [],
        "staff_distribution": [],
        "unpaid_students": [],
        "totals": {
            "classes_count": 2,
            "students_count": 20,
        },
        "pool_totals": {
            "collected": "80.00",
            "school_retention": "8.00",
            "staff_share": "72.00",
            "admin_fee": "0.00",
        },
        "distribution_totals": {
            "general_studies": "50.00",
            "jhs_extra": "10.00",
            "other": "12.00",
            "total": "72.00",
        },
        "total_unpaid_amount": "20.00",
        "generated_at": "2026-03-08T12:00:00Z",
        "generated_by": "Test User",
    }


def sample_staff_report_payload(staff_id=5, staff_name="John Doe"):
    return {
        "title": f"Staff Earnings Report - {staff_name}",
        "staff_id": staff_id,
        "staff_name": staff_name,
        "staff_role": "Teacher",
        "date_range": {
            "start": "2026-03-01",
            "end": "2026-03-31",
        },
        "summary": {
            "total_earned": "150.00",
            "total_paid": "100.00",
            "total_pending": "50.00",
            "distribution_count": 3,
        },
        "distributions": [
            {
                "id": 1,
                "session_id": 1,
                "session_date": "2026-03-08",
                "pool_type": "GEN_STUDIES",
                "base_share": "40.00",
                "adjusted_share": "40.00",
                "special_share_amount": "0.00",
                "total_share": "40.00",
                "attendance_status": "PRESENT",
                "attendance_weight": "1.00",
                "is_paid": True,
                "paid_at": "2026-03-08T13:00:00Z",
                "payment_reference": "PAY-1",
            }
        ],
        "generated_at": "2026-03-08T12:00:00Z",
        "generated_by": "Bursar User",
    }


class ReportAPITests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.teacher = make_user("teacher1", "TEACHER")
        self.bursar = make_user("bursar1", "BURSAR")
        self.headteacher = make_user("head1", "HEADTEACHER")
        self.board = make_user("board1", "BOARD")

    @patch("apps.reports.api.views.ReportGenerator.generate_daily_report")
    def test_daily_report_json(self, mock_generate):
        mock_generate.return_value = sample_report_payload("Daily Report")

        request = self.factory.get(
            "/api/v1/reports/daily/",
            {"date": "2026-03-08"},
        )
        force_authenticate(request, user=self.teacher)

        response = DailyReportView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Daily Report")

        audit = AuditLog.objects.get(action=AuditLog.Action.EXPORT, table_name="reports")
        self.assertIn("daily report JSON", audit.notes)

    @patch("apps.reports.api.views.BaseReportView.get_requested_output_format", return_value="pdf")
    @patch("apps.reports.api.views.EnhancedPDFGenerator.generate_daily_report")
    @patch("apps.reports.api.views.ReportGenerator.generate_daily_report")
    def test_daily_report_pdf(self, mock_generate, mock_pdf, mock_format):
        mock_generate.return_value = sample_report_payload("Daily Report")
        mock_pdf.return_value = b"%PDF-1.4 fake pdf"

        request = self.factory.get(
            "/api/v1/reports/daily/",
            {"date": "2026-03-08"},
        )
        force_authenticate(request, user=self.teacher)

        response = DailyReportView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment;", response["Content-Disposition"])

        audit = AuditLog.objects.get(action=AuditLog.Action.EXPORT, table_name="reports")
        self.assertIn("daily report PDF", audit.notes)

    def test_daily_report_requires_date(self):
        request = self.factory.get("/api/v1/reports/daily/")
        force_authenticate(request, user=self.teacher)

        response = DailyReportView.as_view()(request)

        self.assertEqual(response.status_code, 400)
        self.assertIn("date is required", response.data["detail"])

    def test_daily_report_invalid_date(self):
        request = self.factory.get(
            "/api/v1/reports/daily/",
            {"date": "bad-date"},
        )
        force_authenticate(request, user=self.teacher)

        response = DailyReportView.as_view()(request)

        self.assertEqual(response.status_code, 400)

    @patch("apps.reports.api.views.ReportGenerator.generate_weekly_report")
    def test_weekly_report_json(self, mock_generate):
        mock_generate.return_value = sample_report_payload("Weekly Report")

        request = self.factory.get(
            "/api/v1/reports/weekly/",
            {"week_start": "2026-03-02"},
        )
        force_authenticate(request, user=self.teacher)

        response = WeeklyReportView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Weekly Report")

    @patch("apps.reports.api.views.ReportGenerator.generate_monthly_report")
    def test_monthly_report_json(self, mock_generate):
        mock_generate.return_value = sample_report_payload("Monthly Report")

        request = self.factory.get(
            "/api/v1/reports/monthly/",
            {"year": 2026, "month": 3},
        )
        force_authenticate(request, user=self.teacher)

        response = MonthlyReportView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Monthly Report")

    def test_monthly_report_rejects_bad_month(self):
        request = self.factory.get(
            "/api/v1/reports/monthly/",
            {"year": 2026, "month": 13},
        )
        force_authenticate(request, user=self.teacher)

        response = MonthlyReportView.as_view()(request)

        self.assertEqual(response.status_code, 400)
        self.assertIn("month must be between 1 and 12", response.data["detail"])

    @patch("apps.reports.api.views.ReportGenerator.generate_term_report")
    def test_term_report_json_for_bursar(self, mock_generate):
        mock_generate.return_value = sample_report_payload("Term Report")

        request = self.factory.get(
            "/api/v1/reports/term/",
            {"year": 2026, "term": 1},
        )
        force_authenticate(request, user=self.bursar)

        response = TermReportView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Term Report")

    def test_term_report_forbidden_for_teacher(self):
        request = self.factory.get(
            "/api/v1/reports/term/",
            {"year": 2026, "term": 1},
        )
        force_authenticate(request, user=self.teacher)

        response = TermReportView.as_view()(request)

        self.assertEqual(response.status_code, 403)

    @patch("apps.reports.api.views.ReportGenerator.generate_custom_report")
    def test_custom_report_json_for_headteacher(self, mock_generate):
        mock_generate.return_value = sample_report_payload("Custom Report")

        request = self.factory.get(
            "/api/v1/reports/custom/",
            {"date_from": "2026-03-01", "date_to": "2026-03-08"},
        )
        force_authenticate(request, user=self.headteacher)

        response = CustomReportView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Custom Report")

    def test_custom_report_forbidden_for_teacher(self):
        request = self.factory.get(
            "/api/v1/reports/custom/",
            {"date_from": "2026-03-01", "date_to": "2026-03-08"},
        )
        force_authenticate(request, user=self.teacher)

        response = CustomReportView.as_view()(request)

        self.assertEqual(response.status_code, 403)

    def test_custom_report_rejects_bad_range(self):
        request = self.factory.get(
            "/api/v1/reports/custom/",
            {"date_from": "2026-03-10", "date_to": "2026-03-01"},
        )
        force_authenticate(request, user=self.bursar)

        response = CustomReportView.as_view()(request)

        self.assertEqual(response.status_code, 400)
        self.assertIn("date_from cannot be after date_to", response.data["detail"])

    @patch("apps.reports.api.views.ReportGenerator.generate_staff_report")
    def test_staff_report_self_json(self, mock_generate):
        mock_generate.return_value = sample_staff_report_payload(
            staff_id=self.teacher.id,
            staff_name="John Doe",
        )

        request = self.factory.get(f"/api/v1/reports/staff/{self.teacher.id}/")
        force_authenticate(request, user=self.teacher)

        response = StaffReportView.as_view()(request, staff_id=self.teacher.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["staff_name"], "John Doe")
        self.assertEqual(response.data["staff_id"], self.teacher.id)

    @patch("apps.reports.api.views.ReportGenerator.generate_staff_report")
    def test_staff_report_bursar_can_view_any_staff(self, mock_generate):
        mock_generate.return_value = sample_staff_report_payload(staff_id=5)

        request = self.factory.get("/api/v1/reports/staff/5/")
        force_authenticate(request, user=self.bursar)

        response = StaffReportView.as_view()(request, staff_id=5)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["staff_id"], 5)

    def test_staff_report_forbidden_for_other_teacher(self):
        request = self.factory.get("/api/v1/reports/staff/5/")
        force_authenticate(request, user=self.teacher)

        response = StaffReportView.as_view()(request, staff_id=5)

        self.assertEqual(response.status_code, 403)

    @patch("apps.reports.api.views.BaseReportView.get_requested_output_format", return_value="pdf")
    @patch("apps.reports.api.views.EnhancedPDFGenerator.generate_staff_report")
    @patch("apps.reports.api.views.ReportGenerator.generate_staff_report")
    def test_staff_report_pdf(self, mock_generate, mock_pdf, mock_format):
        mock_generate.return_value = sample_staff_report_payload(staff_id=5)
        mock_pdf.return_value = b"%PDF-1.4 fake staff pdf"

        request = self.factory.get("/api/v1/reports/staff/5/")
        force_authenticate(request, user=self.bursar)

        response = StaffReportView.as_view()(request, staff_id=5)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment;", response["Content-Disposition"])