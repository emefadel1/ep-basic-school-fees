# apps/audit/models.py

"""
Audit trail models for tracking all system changes.
"""

from django.db import models


class AuditLog(models.Model):
    """
    Complete audit trail for all system actions.
    """

    class Action(models.TextChoices):
        CREATE = 'CREATE', 'Create'
        UPDATE = 'UPDATE', 'Update'
        DELETE = 'DELETE', 'Delete'
        LOGIN = 'LOGIN', 'Login'
        LOGOUT = 'LOGOUT', 'Logout'
        LOGIN_FAILED = 'LOGIN_FAILED', 'Login Failed'
        SESSION_TRANSITION = 'SESSION_TRANSITION', 'Session Transition'
        APPROVAL = 'APPROVAL', 'Approval'
        REJECTION = 'REJECTION', 'Rejection'
        DISTRIBUTION = 'DISTRIBUTION', 'Distribution'
        EXPORT = 'EXPORT', 'Export/Download'
        UNLOCK = 'UNLOCK', 'Session Unlock'
        ARREARS_PAYMENT = 'ARREARS_PAYMENT', 'Arrears Payment'
        FEE_WAIVER = 'FEE_WAIVER', 'Fee Waiver'

    action = models.CharField(
        max_length=30,
        choices=Action.choices,
        db_index=True,
    )
    table_name = models.CharField(
        max_length=50,
        db_index=True,
    )
    record_id = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    user = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
    )

    previous_value = models.JSONField(
        null=True,
        blank=True,
    )
    new_value = models.JSONField(
        null=True,
        blank=True,
    )

    notes = models.TextField(blank=True)

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )
    user_agent = models.TextField(blank=True)

    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['table_name', 'record_id']),
            models.Index(fields=['user', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.action} - {self.table_name} - {self.timestamp}"

    @classmethod
    def log_action(
        cls,
        *,
        action,
        table_name,
        user=None,
        record_id=None,
        previous_value=None,
        new_value=None,
        notes='',
        ip_address=None,
        user_agent='',
    ):
        """
        Convenience helper for writing audit logs from services.
        """
        return cls.objects.create(
            action=action,
            table_name=table_name,
            record_id=record_id,
            user=user,
            previous_value=previous_value,
            new_value=new_value,
            notes=notes,
            ip_address=ip_address,
            user_agent=user_agent,
        )