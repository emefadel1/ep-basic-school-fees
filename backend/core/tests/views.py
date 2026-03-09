from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from core.exceptions import SessionLockedError


class ExceptionProbeView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, mode):
        if mode == "app":
            raise SessionLockedError(extra={"session_id": 123})
        if mode == "django":
            raise DjangoValidationError({"field": ["Invalid field"]})
        if mode == "drf":
            raise DRFValidationError({"field": ["This field is required."]})
        if mode == "integrity":
            raise IntegrityError("duplicate key")
        if mode == "unexpected":
            raise RuntimeError("boom")
        return Response({"ok": True})
