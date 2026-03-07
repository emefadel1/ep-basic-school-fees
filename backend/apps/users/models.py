# apps/users/models.py

"""
Custom User model and related models for authentication and authorization.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """
    Custom User model with role-based access control.
    """
    
    class Role(models.TextChoices):
        TEACHER = 'TEACHER', 'Teacher'
        CONTACT_PERSON = 'CONTACT_PERSON', 'Contact Person'
        HEADTEACHER = 'HEADTEACHER', 'Headteacher'
        BURSAR = 'BURSAR', 'Bursar'
        BOARD = 'BOARD', 'Board Member'
    
    # Role
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.TEACHER,
        db_index=True
    )
    
    # Profile info
    phone_number = models.CharField(max_length=15, blank=True)
    profile_picture = models.ImageField(
        upload_to='profiles/%Y/%m/',
        blank=True,
        null=True
    )
    
    # Staff info
    staff_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    is_active_staff = models.BooleanField(default=True)
    date_joined_school = models.DateField(null=True, blank=True)
    
    # Assignment (for teachers)
    assigned_class = models.ForeignKey(
        'school.SchoolClass',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_teachers'
    )
    
    # For contact persons
    assigned_category = models.CharField(
        max_length=20,
        choices=[
            ('PRE_SCHOOL', 'Pre-School'),
            ('PRIMARY', 'Primary'),
            ('JHS', 'JHS'),
        ],
        blank=True,
        null=True
    )
    
    # Security
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users'
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['is_active_staff']),
            models.Index(fields=['assigned_class']),
            models.Index(fields=['email']),
        ]
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username
    
    @property
    def is_locked(self):
        if self.locked_until:
            return timezone.now() < self.locked_until
        return False
    
    def lock_account(self, minutes=15):
        """Lock account for specified minutes"""
        self.locked_until = timezone.now() + timezone.timedelta(minutes=minutes)
        self.save(update_fields=['locked_until'])
    
    def unlock_account(self):
        """Unlock account"""
        self.locked_until = None
        self.failed_login_attempts = 0
        self.save(update_fields=['locked_until', 'failed_login_attempts'])
    
    def record_login_attempt(self, success, ip_address=None):
        """Record login attempt"""
        if success:
            self.failed_login_attempts = 0
            self.last_login_ip = ip_address
            self.last_login = timezone.now()
        else:
            self.failed_login_attempts += 1
            if self.failed_login_attempts >= 5:
                self.lock_account(15)  # Lock for 15 minutes
        self.save()


class PushSubscription(models.Model):
    """Store push notification subscriptions"""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='push_subscriptions'
    )
    endpoint = models.URLField(max_length=500)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'push_subscriptions'
        unique_together = ['user', 'endpoint']
    
    def __str__(self):
        return f"Push sub for {self.user.username}"