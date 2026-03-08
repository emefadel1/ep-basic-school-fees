# apps/reports/api/views.py

from __future__ import annotations

from datetime import date

from django.http import HttpResponse
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditLog
from apps.reports.services.pdf_generator import EnhancedPDFGenerator
from apps.reports.services.reports import ReportGenerator


def normalize_role(user) -> str:
    return str(getattr(user, "role", "")).replace("_", "").replace(" ", "").upper()


def request_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class BaseReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    allowed_roles = {"TEACHER", "CONTACTPERSON", "HEADTEACHER", "BURSAR", "BOARD"}

    def get_format_suffix(self, **kwargs):
        return None

    def get_requested_output_format(self, request) -> str:
        return (
            request.query_params.get("output")
            or request.query_params.get("format")
            or "json"
        ).lower()

    def check_role(self, request):
        if normalize_role(request.user) not in self.allowed_roles:
            return Response({"detail": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        return None

    def audit_export(self, request, notes: str):
        AuditLog.log_action(
            action=AuditLog.Action.EXPORT,
            table_name="reports",
            record_id=None,
            user=request.user,
            previous_value=None,
            new_value=None,
            notes=notes,
            ip_address=request_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

    def render_pdf_response(self, pdf_bytes: bytes, filename: str):
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class DailyReportView(BaseReportView):
    def get(self, request):
        denied = self.check_role(request)
        if denied:
            return denied

        date_str = request.query_params.get("date")
        fmt = self.get_requested_output_format(request)

        if not date_str:
            return Response({"detail": "date is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            report_date = date.fromisoformat(date_str)
        except ValueError:
            return Response(
                {"detail": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            report_data = ReportGenerator(request.user).generate_daily_report(report_date)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        if fmt == "pdf":
            pdf_bytes = EnhancedPDFGenerator().generate_daily_report(report_data, request.user)
            self.audit_export(request, f"Generated daily report PDF for {report_date}")
            return self.render_pdf_response(pdf_bytes, f"EP_Basic_Daily_Report_{report_date}.pdf")

        self.audit_export(request, f"Generated daily report JSON for {report_date}")
        return Response(report_data)


class WeeklyReportView(BaseReportView):
    def get(self, request):
        denied = self.check_role(request)
        if denied:
            return denied

        week_start_str = request.query_params.get("week_start")
        fmt = self.get_requested_output_format(request)

        if not week_start_str:
            return Response({"detail": "week_start is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            week_start = date.fromisoformat(week_start_str)
        except ValueError:
            return Response(
                {"detail": "Invalid week_start format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            report_data = ReportGenerator(request.user).generate_weekly_report(week_start)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        if fmt == "pdf":
            pdf_bytes = EnhancedPDFGenerator().generate_daily_report(report_data, request.user)
            self.audit_export(request, f"Generated weekly report PDF for week starting {week_start}")
            return self.render_pdf_response(pdf_bytes, f"EP_Basic_Weekly_Report_{week_start}.pdf")

        self.audit_export(request, f"Generated weekly report JSON for week starting {week_start}")
        return Response(report_data)


class MonthlyReportView(BaseReportView):
    def get(self, request):
        denied = self.check_role(request)
        if denied:
            return denied

        year_str = request.query_params.get("year")
        month_str = request.query_params.get("month")
        fmt = self.get_requested_output_format(request)

        if not year_str or not month_str:
            return Response({"detail": "year and month are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            year = int(year_str)
            month = int(month_str)
        except ValueError:
            return Response(
                {"detail": "year and month must be integers"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if month < 1 or month > 12:
            return Response(
                {"detail": "month must be between 1 and 12"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            report_data = ReportGenerator(request.user).generate_monthly_report(year, month)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        if fmt == "pdf":
            pdf_bytes = EnhancedPDFGenerator().generate_daily_report(report_data, request.user)
            self.audit_export(request, f"Generated monthly report PDF for {year}-{month:02d}")
            return self.render_pdf_response(
                pdf_bytes,
                f"EP_Basic_Monthly_Report_{year}_{month:02d}.pdf",
            )

        self.audit_export(request, f"Generated monthly report JSON for {year}-{month:02d}")
        return Response(report_data)


class TermReportView(BaseReportView):
    allowed_roles = {"HEADTEACHER", "BURSAR", "BOARD"}

    def get(self, request):
        denied = self.check_role(request)
        if denied:
            return denied

        year_str = request.query_params.get("year")
        term_str = request.query_params.get("term")
        fmt = self.get_requested_output_format(request)

        if not year_str or not term_str:
            return Response({"detail": "year and term are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            year = int(year_str)
            term = int(term_str)
        except ValueError:
            return Response(
                {"detail": "year and term must be integers"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            report_data = ReportGenerator(request.user).generate_term_report(year, term)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if fmt == "pdf":
            pdf_bytes = EnhancedPDFGenerator().generate_daily_report(report_data, request.user)
            self.audit_export(request, f"Generated term report PDF for year={year}, term={term}")
            return self.render_pdf_response(pdf_bytes, f"EP_Basic_Term_Report_{year}_T{term}.pdf")

        self.audit_export(request, f"Generated term report JSON for year={year}, term={term}")
        return Response(report_data)


class CustomReportView(BaseReportView):
    allowed_roles = {"HEADTEACHER", "BURSAR", "BOARD"}

    def get(self, request):
        denied = self.check_role(request)
        if denied:
            return denied

        date_from_str = request.query_params.get("date_from")
        date_to_str = request.query_params.get("date_to")
        fmt = self.get_requested_output_format(request)

        if not date_from_str or not date_to_str:
            return Response(
                {"detail": "date_from and date_to are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            date_from = date.fromisoformat(date_from_str)
            date_to = date.fromisoformat(date_to_str)
        except ValueError:
            return Response(
                {"detail": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if date_from > date_to:
            return Response(
                {"detail": "date_from cannot be after date_to"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            report_data = ReportGenerator(request.user).generate_custom_report(date_from, date_to)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        if fmt == "pdf":
            pdf_bytes = EnhancedPDFGenerator().generate_daily_report(report_data, request.user)
            self.audit_export(request, f"Generated custom report PDF for {date_from} to {date_to}")
            return self.render_pdf_response(
                pdf_bytes,
                f"EP_Basic_Custom_Report_{date_from}_{date_to}.pdf",
            )

        self.audit_export(request, f"Generated custom report JSON for {date_from} to {date_to}")
        return Response(report_data)


class StaffReportView(BaseReportView):
    def get(self, request, staff_id: int):
        role = normalize_role(request.user)
        if role != "BURSAR" and request.user.id != staff_id:
            return Response({"detail": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        fmt = self.get_requested_output_format(request)
        date_from_str = request.query_params.get("date_from")
        date_to_str = request.query_params.get("date_to")

        start_date = None
        end_date = None

        try:
            if date_from_str:
                start_date = date.fromisoformat(date_from_str)
            if date_to_str:
                end_date = date.fromisoformat(date_to_str)
        except ValueError:
            return Response(
                {"detail": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            report_data = ReportGenerator(request.user).generate_staff_report(
                staff_id=staff_id,
                start_date=start_date,
                end_date=end_date,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        if fmt == "pdf":
            pdf_bytes = EnhancedPDFGenerator().generate_staff_report(report_data, request.user)
            self.audit_export(request, f"Generated staff report PDF for staff_id={staff_id}")
            return self.render_pdf_response(pdf_bytes, f"EP_Basic_Staff_Report_{staff_id}.pdf")

        self.audit_export(request, f"Generated staff report JSON for staff_id={staff_id}")
        return Response(report_data)