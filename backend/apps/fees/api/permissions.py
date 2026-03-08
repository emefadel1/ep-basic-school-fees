# apps/fees/api/permissions.py

from rest_framework.permissions import BasePermission


def user_role(user):
    return str(getattr(user, "role", "")).upper()


class IsTeacherContactHeadteacherBursarBoard(BasePermission):
    allowed = {"TEACHER", "CONTACTPERSON", "HEADTEACHER", "BURSAR", "BOARD"}

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and user_role(request.user) in self.allowed


class IsTeacherHeadteacherBursar(BasePermission):
    allowed = {"TEACHER", "HEADTEACHER", "BURSAR"}

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and user_role(request.user) in self.allowed


class IsHeadteacherOrBursar(BasePermission):
    allowed = {"HEADTEACHER", "BURSAR"}

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and user_role(request.user) in self.allowed


class IsBursar(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and user_role(request.user) == "BURSAR"


class IsSelfOrBursar(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return obj.staff_id == request.user.id or user_role(request.user) == "BURSAR"