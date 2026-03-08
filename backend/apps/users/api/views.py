# apps/users/api/views.py

from django.contrib.auth import update_session_auth_hash
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.audit.models import AuditLog
from .serializers import ChangePasswordSerializer, LoginSerializer, LogoutSerializer


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        refresh_token = serializer.validated_data["refresh"]
        token = RefreshToken(refresh_token)
        token.blacklist()

        AuditLog.log_action(
            action=AuditLog.Action.LOGOUT,
            table_name="users",
            record_id=request.user.id,
            user=request.user,
            notes="User logged out",
            ip_address=self._get_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        return Response({"detail": "Successfully logged out"}, status=status.HTTP_200_OK)

    def _get_ip(self, request):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        old_password = serializer.validated_data["old_password"]
        new_password = serializer.validated_data["new_password"]

        if not user.check_password(old_password):
            return Response(
                {"old_password": ["Old password is incorrect."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])
        update_session_auth_hash(request, user)

        AuditLog.log_action(
            action=AuditLog.Action.UPDATE,
            table_name="users",
            record_id=user.id,
            user=user,
            notes="Password changed",
            ip_address=self._get_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        return Response({"detail": "Password changed successfully"}, status=status.HTTP_200_OK)

    def _get_ip(self, request):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")