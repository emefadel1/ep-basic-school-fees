# apps/reports/api/urls.py

from django.urls import path

from .views import (
    CustomReportView,
    DailyReportView,
    MonthlyReportView,
    StaffReportView,
    TermReportView,
    WeeklyReportView,
)

urlpatterns = [
    path("daily/", DailyReportView.as_view(), name="report-daily"),
    path("weekly/", WeeklyReportView.as_view(), name="report-weekly"),
    path("monthly/", MonthlyReportView.as_view(), name="report-monthly"),
    path("term/", TermReportView.as_view(), name="report-term"),
    path("custom/", CustomReportView.as_view(), name="report-custom"),
    path("staff/<int:staff_id>/", StaffReportView.as_view(), name="report-staff"),
]