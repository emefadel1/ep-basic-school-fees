# apps/reports/api/dashboard_views.py

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.exceptions import PermissionDeniedError
from apps.reports.services.dashboard import DashboardService, normalize_role


class BaseDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    allowed_roles = set()

    def check_role(self, request):
        if normalize_role(request.user) not in self.allowed_roles:
            raise PermissionDeniedError()


class TeacherDashboardView(BaseDashboardView):
    allowed_roles = {"TEACHER"}

    def get(self, request):
        denied = self.check_role(request)
        if denied:
            return denied
        return Response(DashboardService(request.user).get_teacher_dashboard())


class ContactDashboardView(BaseDashboardView):
    allowed_roles = {"CONTACTPERSON"}

    def get(self, request):
        denied = self.check_role(request)
        if denied:
            return denied
        return Response(DashboardService(request.user).get_contact_dashboard())


class HeadteacherDashboardView(BaseDashboardView):
    allowed_roles = {"HEADTEACHER"}

    def get(self, request):
        denied = self.check_role(request)
        if denied:
            return denied
        return Response(DashboardService(request.user).get_headteacher_dashboard())


class BursarDashboardView(BaseDashboardView):
    allowed_roles = {"BURSAR"}

    def get(self, request):
        denied = self.check_role(request)
        if denied:
            return denied
        return Response(DashboardService(request.user).get_bursar_dashboard())

class BoardDashboardView(BaseDashboardView):
    allowed_roles = {"BOARD"}

    def get(self, request):
        denied = self.check_role(request)
        if denied:
            return denied
        return Response(DashboardService(request.user).get_board_dashboard())