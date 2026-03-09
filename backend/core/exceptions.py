class BaseAppException(Exception):
    default_message = 'An application error occurred.'
    default_code = 'application_error'
    status_code = 400

    def __init__(self, message=None, code=None, extra=None, status_code=None):
        self.message = message or self.default_message
        self.code = code or self.default_code
        self.status_code = status_code or self.status_code
        self.extra = extra or {}
        super().__init__(self.message)

    def __str__(self):
        return self.message

class SessionError(BaseAppException):
    default_message = 'Session operation failed.'
    default_code = 'session_error'

class SessionNotOpenError(SessionError):
    default_message = 'Session must be open before this action can continue.'
    default_code = 'session_not_open'

class SessionAlreadyApprovedError(SessionError):
    default_message = 'Session has already been approved.'
    default_code = 'session_already_approved'

class SessionLockedError(SessionError):
    default_message = 'Session is locked and cannot be modified.'
    default_code = 'session_locked'
    status_code = 423

class CollectionError(BaseAppException):
    default_message = 'Collection operation failed.'
    default_code = 'collection_error'

class DuplicateCollectionError(CollectionError):
    default_message = 'A collection already exists for this student and pool.'
    default_code = 'duplicate_collection'
    status_code = 409

class InvalidAmountError(CollectionError):
    default_message = 'The supplied amount is invalid.'
    default_code = 'invalid_amount'

class DistributionError(BaseAppException):
    default_message = 'Distribution failed.'
    default_code = 'distribution_error'

class InsufficientDataError(DistributionError):
    default_message = 'More data is required before distribution can continue.'
    default_code = 'insufficient_data'

class AuthenticationError(BaseAppException):
    default_message = 'Authentication is required.'
    default_code = 'authentication_error'
    status_code = 401

class PermissionDeniedError(BaseAppException):
    default_message = 'You do not have permission to perform this action.'
    default_code = 'permission_denied'
    status_code = 403

class AccountLockedError(AuthenticationError):
    default_message = 'This account is locked.'
    default_code = 'account_locked'
    status_code = 423

class TokenExpiredError(AuthenticationError):
    default_message = 'Your session has expired. Please sign in again.'
    default_code = 'token_expired'
    status_code = 401

class AppValidationError(BaseAppException):
    default_message = 'Submitted data is invalid.'
    default_code = 'validation_error'

class InvalidDateError(AppValidationError):
    default_message = 'The supplied date is invalid.'
    default_code = 'invalid_date'

class FutureDateError(AppValidationError):
    default_message = 'Future dates are not allowed for this operation.'
    default_code = 'future_date'

class NotFoundError(BaseAppException):
    default_message = 'Requested resource was not found.'
    default_code = 'not_found'
    status_code = 404

class StudentNotFoundError(NotFoundError):
    default_message = 'Student was not found.'
    default_code = 'student_not_found'

class SessionNotFoundError(NotFoundError):
    default_message = 'Session was not found.'
    default_code = 'session_not_found'

class ExternalServiceError(BaseAppException):
    default_message = 'External service request failed.'
    default_code = 'external_service_error'
    status_code = 502

class PDFGenerationError(ExternalServiceError):
    default_message = 'PDF generation failed.'
    default_code = 'pdf_generation_error'
