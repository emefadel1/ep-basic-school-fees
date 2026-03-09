from django.urls import path

from .dashboard_views import (
    BoardDashboardView,
    BursarDashboardView,
    ContactDashboardView,
    HeadteacherDashboardView,
    TeacherDashboardView,
)

urlpatterns = [
    path("teacher/", TeacherDashboardView.as_view(), name="dashboard-teacher"),
    path("contact/", ContactDashboardView.as_view(), name="dashboard-contact"),
    path("headteacher/", HeadteacherDashboardView.as_view(), name="dashboard-headteacher"),
    path("bursar/", BursarDashboardView.as_view(), name="dashboard-bursar"),
    path("board/", BoardDashboardView.as_view(), name="dashboard-board"),
]