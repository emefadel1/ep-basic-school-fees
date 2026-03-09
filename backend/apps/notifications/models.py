from django.db import models
from django.utils import timezone

class NotificationType(models.TextChoices):
    SESSION_SUBMITTED = 'SESSION_SUBMITTED', 'Session Submitted'
    SESSION_APPROVED = 'SESSION_APPROVED', 'Session Approved'
    SESSION_REJECTED = 'SESSION_REJECTED', 'Session Rejected'
    SESSION_DISTRIBUTED = 'SESSION_DISTRIBUTED', 'Session Distributed'
    SESSION_UNLOCKED = 'SESSION_UNLOCKED', 'Session Unlocked'
    ARREARS_PAYMENT_RECORDED = 'ARREARS_PAYMENT_RECORDED', 'Arrears Payment Recorded'
    FEE_WAIVER_APPROVED = 'FEE_WAIVER_APPROVED', 'Fee Waiver Approved'

class NotificationChannel(models.TextChoices):
    IN_APP = 'IN_APP', 'In-App'
    EMAIL = 'EMAIL', 'Email'
    SYSTEM = 'SYSTEM', 'System'

class NotificationPriority(models.TextChoices):
    LOW = 'LOW', 'Low'
    NORMAL = 'NORMAL', 'Normal'
    HIGH = 'HIGH', 'High'
    URGENT = 'URGENT', 'Urgent'

class NotificationQuerySet(models.QuerySet):
    def unread(self):
        return self.filter(is_read=False)

class Notification(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=64, choices=NotificationType.choices, db_index=True)
    channel = models.CharField(max_length=20, choices=NotificationChannel.choices, default=NotificationChannel.IN_APP)
    priority = models.CharField(max_length=20, choices=NotificationPriority.choices, default=NotificationPriority.NORMAL)
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    related_model = models.CharField(max_length=100, blank=True)
    related_id = models.PositiveBigIntegerField(null=True, blank=True)
    action_url = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = NotificationQuerySet.as_manager()

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', 'created_at'], name='notif_user_read_created_idx'),
            models.Index(fields=['notification_type', 'created_at'], name='notif_type_created_idx'),
        ]

    def __str__(self):
        return f'{self.title} for {self.user}'

    def mark_as_read(self):
        if self.is_read:
            return
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=['is_read', 'read_at'])

class NotificationPreference(models.Model):
    user = models.OneToOneField('users.User', on_delete=models.CASCADE, related_name='notification_preferences')
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    push_enabled = models.BooleanField(default=True)
    disabled_types = models.JSONField(default=list)
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(default='22:00')
    quiet_hours_end = models.TimeField(default='07:00')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notification_preferences'

    def __str__(self):
        return f'Preferences for {self.user.username}'
