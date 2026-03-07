\"\"\"
Custom exception handler for consistent API responses.
\"\"\"

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.db import IntegrityError
from django.utils import timezone
import logging
import traceback

logger = logging.getLogger(__name__)


class BaseAPIException(Exception):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'error'
    default_message = 'An error occurred'
    
    def __init__(self, message=None, code=None, extra=None):
        self.message = message or self.default_message
        self.code = code or self.default_code
        self.extra = extra or {}
        super().__init__(self.message)


class ValidationException(BaseAPIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = 'validation_error'
    default_message = 'Validation failed'


class AuthenticationException(BaseAPIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = 'authentication_error'
    default_message = 'Authentication failed'


class PermissionDeniedException(BaseAPIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = 'permission_denied'
    default_message = 'Permission denied'


class NotFoundException(BaseAPIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = 'not_found'
    default_message = 'Resource not found'


class ConflictException(BaseAPIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = 'conflict'
    default_message = 'Resource conflict'


class SessionException(BaseAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'session_error'
    default_message = 'Session operation failed'


class DistributionException(BaseAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'distribution_error'
    default_message = 'Distribution calculation failed'


def custom_exception_handler(exc, context):
    request = context.get('request')
    view = context.get('view')
    error_context = {
        'path': request.path if request else 'unknown',
        'method': request.method if request else 'unknown',
        'user': str(request.user) if request else 'anonymous',
        'view': view.__class__.__name__ if view else 'unknown',
    }
    
    if isinstance(exc, BaseAPIException):
        return Response(
            format_error_response(exc.code, exc.message, exc.extra),
            status=exc.status_code
        )
    
    if isinstance(exc, DjangoValidationError):
        errors = exc.message_dict if hasattr(exc, 'message_dict') else {'detail': exc.messages}
        return Response(
            format_error_response('validation_error', 'Validation failed', {'errors': errors}),
            status=status.HTTP_422_UNPROCESSABLE_ENTITY
        )
    
    if isinstance(exc, IntegrityError):
        logger.error(f"Database integrity error: {exc}", extra=error_context)
        return Response(
            format_error_response('conflict', 'A database conflict occurred'),
            status=status.HTTP_409_CONFLICT
        )
    
    if isinstance(exc, Http404):
        return Response(
            format_error_response('not_found', 'Resource not found'),
            status=status.HTTP_404_NOT_FOUND
        )
    
    response = exception_handler(exc, context)
    if response is not None:
        error_detail = response.data.get('detail', str(response.data))
        return Response(
            format_error_response('error', str(error_detail)),
            status=response.status_code
        )
    
    logger.exception(f"Unhandled exception: {exc}", extra={
        **error_context,
        'traceback': traceback.format_exc()
    })
    return Response(
        format_error_response('server_error', 'An unexpected error occurred'),
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def format_error_response(code, message, extra=None):
    response = {
        'success': False,
        'error': {
            'code': code,
            'message': message,
        },
        'timestamp': timezone.now().isoformat(),
    }
    
    if extra:
        response['error'].update(extra)
    
    return response
