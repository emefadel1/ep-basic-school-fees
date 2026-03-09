from django.contrib.auth import get_user_model
from django.utils import timezone
from django_q.tasks import async_task

from apps.notifications.models import Notification, NotificationChannel, NotificationPriority, NotificationType

def _resolve_related_reference(related_object=None, related_model='', related_id=None):
    if related_object is not None:
        return related_object._meta.label_lower, related_object.pk
    return related_model, related_id

def _unique_users(users):
    unique = []
    seen = set()
    for user in users:
        if user is None or not getattr(user, 'id', None):
            continue
        if not getattr(user, 'is_active', True) or user.id in seen:
            continue
        seen.add(user.id)
        unique.append(user)
    return unique

def _users_for_roles(*roles):
    return get_user_model().objects.filter(role__in=roles, is_active=True)

def create_notification(user, title, message, notification_type, channel=NotificationChannel.IN_APP, priority=NotificationPriority.NORMAL, related_object=None, related_model='', related_id=None, action_url='', metadata=None):
    related_model, related_id = _resolve_related_reference(related_object, related_model, related_id)
    return Notification.objects.create(user=user, title=title, message=message, notification_type=notification_type, channel=channel, priority=priority, related_model=related_model, related_id=related_id, action_url=action_url, metadata=metadata or {})

def send_email_notification(subject, message, recipient_list):
    recipients = sorted({email for email in recipient_list if email})
    if not recipients:
        return None
    return async_task('apps.notifications.tasks.send_notification_email', subject, message, recipients)

def notify_users(users, title, message, notification_type, priority=NotificationPriority.NORMAL, action_url='', metadata=None, related_object=None, related_model='', related_id=None, send_email=False, email_subject=''):
    related_model, related_id = _resolve_related_reference(related_object, related_model, related_id)
    recipients = _unique_users(users)
    notifications = [
        Notification(user=user, title=title, message=message, notification_type=notification_type, channel=NotificationChannel.IN_APP, priority=priority, related_model=related_model, related_id=related_id, action_url=action_url, metadata=metadata or {})
        for user in recipients
    ]
    if notifications:
        Notification.objects.bulk_create(notifications)
    if send_email and recipients:
        send_email_notification(email_subject or title, message, [user.email for user in recipients])
    return notifications

def mark_as_read(notification):
    notification.mark_as_read()
    return notification

def mark_all_as_read(user):
    return Notification.objects.filter(user=user, is_read=False).update(is_read=True, read_at=timezone.now())


def get_unread_count(user):
    return Notification.objects.filter(user=user, is_read=False).count()

def has_notification_audit_access(user):
    role = str(getattr(user, 'role', '')).upper()
    return bool(user and user.is_authenticated and (role == 'BURSAR' or getattr(user, 'is_staff', False)))

def notification_queryset_for_user(user, target_user_id=None, include_all=False):
    queryset = Notification.objects.select_related('user')
    if has_notification_audit_access(user) and include_all:
        return queryset
    if has_notification_audit_access(user) and target_user_id:
        return queryset.filter(user_id=target_user_id)
    return queryset.filter(user=user)

def notify_session_submitted(session):
    submitter = session.submitted_by or session.opened_by
    submitter_name = submitter.get_full_name() if submitter else 'A staff member'
    return notify_users(_users_for_roles('BURSAR'), 'Session submitted for approval', f'Session for {session.date} was submitted for approval by {submitter_name}.', NotificationType.SESSION_SUBMITTED, priority=NotificationPriority.HIGH, related_object=session, action_url=f'/api/v1/sessions/{session.id}/', metadata={'session_id': session.id, 'session_date': str(session.date)}, send_email=True)

def notify_session_approved(session):
    approver_name = session.approved_by.get_full_name() if session.approved_by else 'A bursar'
    message = f'Session for {session.date} was approved by {approver_name}.'
    if session.approval_notes:
        message = f'{message} Notes: {session.approval_notes}'
    return notify_users(_users_for_roles('HEADTEACHER'), 'Session approved', message, NotificationType.SESSION_APPROVED, priority=NotificationPriority.HIGH, related_object=session, action_url=f'/api/v1/sessions/{session.id}/', metadata={'session_id': session.id, 'session_date': str(session.date)}, send_email=True)

def notify_session_rejected(session):
    recipients = list(_users_for_roles('HEADTEACHER'))
    if session.submitted_by:
        recipients.append(session.submitted_by)
    rejected_by = session.rejected_by.get_full_name() if session.rejected_by else 'A bursar'
    return notify_users(recipients, 'Session rejected', f'Session for {session.date} was rejected by {rejected_by}. Reason: {session.rejection_reason}', NotificationType.SESSION_REJECTED, priority=NotificationPriority.URGENT, related_object=session, action_url=f'/api/v1/sessions/{session.id}/', metadata={'session_id': session.id, 'session_date': str(session.date)}, send_email=True)

def notify_session_distributed(session):
    recipients = [distribution.staff for distribution in session.distributions.select_related('staff').all()]
    return notify_users(recipients, 'Session distributed', f'Distribution for session {session.date} has been finalized.', NotificationType.SESSION_DISTRIBUTED, priority=NotificationPriority.NORMAL, related_object=session, action_url=f'/api/v1/distributions/?session_id={session.id}', metadata={'session_id': session.id, 'session_date': str(session.date)}, send_email=True)

def notify_session_unlocked(session):
    return notify_users(list(_users_for_roles('BURSAR', 'HEADTEACHER')), 'Session unlocked', f'Session for {session.date} was unlocked. Reason: {session.last_unlock_reason}', NotificationType.SESSION_UNLOCKED, priority=NotificationPriority.URGENT, related_object=session, action_url=f'/api/v1/sessions/{session.id}/', metadata={'session_id': session.id, 'session_date': str(session.date), 'unlock_count': session.unlock_count}, send_email=True)

def notify_arrears_payment_recorded(arrears, amount, recorded_by=None):
    recorded_by_name = recorded_by.get_full_name() if recorded_by else 'A staff member'
    return notify_users(_users_for_roles('BURSAR'), 'Arrears payment recorded', f'{recorded_by_name} recorded an arrears payment of {amount} for {arrears.student.full_name}. Remaining balance: {arrears.balance}.', NotificationType.ARREARS_PAYMENT_RECORDED, priority=NotificationPriority.HIGH, related_model='fees.studentarrears', related_id=arrears.id, action_url=f'/api/v1/collections/?session_id={arrears.session_id}', metadata={'arrears_id': arrears.id, 'student_id': arrears.student_id, 'session_id': arrears.session_id, 'amount_paid': str(amount), 'balance': str(arrears.balance)}, send_email=True)

def notify_fee_waiver_approved(collection):
    school_class = getattr(collection, 'school_class', None)
    recipients = []
    if school_class is not None and hasattr(school_class, 'assigned_teachers'):
        recipients.extend(list(school_class.assigned_teachers.filter(is_active=True)))
    recipients.extend(_users_for_roles('BURSAR'))
    student = getattr(collection, 'student', None)
    student_name = getattr(student, 'full_name', None) or str(getattr(collection, 'student_id', 'student'))
    class_code = getattr(school_class, 'code', str(getattr(collection, 'school_class_id', 'class')))
    approved_by = getattr(collection, 'waiver_approved_by', None)
    approved_by_name = approved_by.get_full_name() if approved_by else 'A staff member'
    reason = getattr(collection, 'waiver_reason', '')
    action_url = '/api/v1/collections/?session_id={0}'.format(getattr(collection, 'session_id', ''))
    message = f'{approved_by_name} approved a fee waiver for {student_name} in {class_code}. Reason: {reason}'
    return notify_users(recipients, 'Fee waiver approved', message, NotificationType.FEE_WAIVER_APPROVED, priority=NotificationPriority.HIGH, related_model='fees.feecollection', related_id=getattr(collection, 'id', None), action_url=action_url, metadata={'collection_id': getattr(collection, 'id', None), 'student_id': getattr(collection, 'student_id', None), 'session_id': getattr(collection, 'session_id', None), 'school_class_id': getattr(collection, 'school_class_id', None)}, send_email=True)