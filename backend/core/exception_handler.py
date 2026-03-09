import logging
import traceback

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.http import Http404
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from .exceptions import BaseAppException

logger = logging.getLogger("api.errors")


def _request_context(request):
    return {
        "path": getattr(request, "path", ""),
        "method": getattr(request, "method", ""),
    }


def _normalize_list(value):
    return [str(item) for item in value]


def _extract_message(detail, default_message):
    if isinstance(detail, dict):
        if "detail" in detail:
            return str(detail["detail"] or default_message)
        for value in detail.values():
            if isinstance(value, list) and value:
                return str(value[0])
            return str(value)
    if isinstance(detail, list) and detail:
        return str(detail[0])
    return str(detail or default_message)

def _normalize_errors(detail):
    if not detail:
        return {}

    if isinstance(detail, dict):
        if set(detail.keys()) == {"detail"}:
            return {}
        errors = {}
        for field, value in detail.items():
            if isinstance(value, dict):
                errors[field] = _normalize_errors(value)
            elif isinstance(value, list):
                errors[field] = _normalize_list(value)
            else:
                errors[field] = [str(value)]
        return errors

    if isinstance(detail, list):
        return {"non_field_errors": _normalize_list(detail)}

    return {"non_field_errors": [str(detail)]}


def _extract_code(exc, default_code="error"):
    if hasattr(exc, "get_codes"):
        codes = exc.get_codes()
        if isinstance(codes, dict):
            for value in codes.values():
                if isinstance(value, list) and value:
                    return str(value[0])
                return str(value)
        if isinstance(codes, list) and codes:
            return str(codes[0])
        if codes:
            return str(codes)
    return default_code

def format_error_response(*, request, code, message, status_code, errors=None, extra=None):
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "status": status_code,
            "errors": errors or {},
            "extra": extra or {},
        },
        "timestamp": timezone.now().isoformat(),
        "context": _request_context(request),
    }


def custom_exception_handler(exc, context):
    request = context.get("request")

    if isinstance(exc, BaseAppException):
        payload = format_error_response(
            request=request,
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
            extra=exc.extra,
        )
        return Response(payload, status=exc.status_code)

    if isinstance(exc, DjangoValidationError):
        detail = getattr(exc, "message_dict", None) or getattr(exc, "messages", None) or str(exc)
        errors = _normalize_errors(detail)
        payload = format_error_response(
            request=request,
            code="validation_error",
            message=_extract_message(detail, "Submitted data is invalid."),
            status_code=400,
            errors=errors,
        )
        return Response(payload, status=400)

    if isinstance(exc, IntegrityError):
        logger.warning("IntegrityError on %s %s", getattr(request, "method", ""), getattr(request, "path", ""), exc_info=exc)
        payload = format_error_response(
            request=request,
            code="integrity_error",
            message="A data conflict prevented the request from completing.",
            status_code=409,
        )
        return Response(payload, status=409)

    if isinstance(exc, Http404):
        payload = format_error_response(
            request=request,
            code="not_found",
            message="Requested resource was not found.",
            status_code=404,
        )
        return Response(payload, status=404)

    response = drf_exception_handler(exc, context)
    if response is not None:
        detail = response.data
        errors = _normalize_errors(detail)
        code = _extract_code(exc, default_code="api_error")
        if response.status_code == 400 and errors:
            code = "validation_error"
        payload = format_error_response(
            request=request,
            code=code,
            message=_extract_message(detail, "Request failed."),
            status_code=response.status_code,
            errors=errors,
        )
        response.data = payload
        return response

    logger.exception("Unhandled exception on %s %s", getattr(request, "method", ""), getattr(request, "path", ""), exc_info=exc)
    extra = {}
    if settings.DEBUG:
        extra["trace"] = traceback.format_exc()

    payload = format_error_response(
        request=request,
        code="internal_server_error",
        message="An unexpected error occurred. Please try again.",
        status_code=500,
        extra=extra,
    )
    return Response(payload, status=500)
