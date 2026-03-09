from rest_framework.permissions import BasePermission


def normalize_role(user):
    return str(getattr(user, "role", "")).replace("_", "").replace(" ", "").upper()


class HasAnyRole(BasePermission):
    allowed_roles = set()

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and normalize_role(request.user) in self.allowed_roles


class IsBursar(HasAnyRole):
    allowed_roles = {"BURSAR"}


class IsHeadteacherOrBursar(HasAnyRole):
    allowed_roles = {"HEADTEACHER", "BURSAR"}


class IsTeacherHeadteacherOrBursar(HasAnyRole):
    allowed_roles = {"TEACHER", "HEADTEACHER", "BURSAR"}


class IsBoardHeadteacherOrBursar(HasAnyRole):
    allowed_roles = {"BOARD", "HEADTEACHER", "BURSAR"}

class IsAuditViewer(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                normalize_role(request.user) == "BURSAR"
                or getattr(request.user, "is_staff", False)
                or getattr(request.user, "is_superuser", False)
            )
        )
