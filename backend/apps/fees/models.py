# apps/fees/models.py

"""
Fee collection, distribution, and session management models.
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal


class PoolType(models.TextChoices):
    """Fee pool types"""
    GENERAL_STUDIES = 'GEN_STUDIES', 'General Studies'
    JHS_EXTRA = 'JHS_EXTRA', 'JHS Extra'
    JHS3_EXTRA = 'JHS3_EXTRA', 'JHS 3 Extra'
    SATURDAY = 'SATURDAY', 'Saturday'


class FeePool(models.Model):
    """
    Fee pool configuration and tracking.
    Defines the pools where collected fees are aggregated.
    """
    
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'
        CLOSED = 'CLOSED', 'Closed'
    
    # Basic info
    name = models.CharField(max_length=100)
    pool_type = models.CharField(
        max_length=20,
        choices=PoolType.choices,
        unique=True,
        db_index=True
    )
    description = models.TextField(blank=True)
    
    # Configuration
    academic_year = models.CharField(max_length=20)  # e.g., "2024-2025"
    term = models.CharField(max_length=20, blank=True)  # e.g., "Term 1"
    
    # Financial tracking
    total_collected = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_distributed = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Distribution configuration
    school_retention_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('10.00'),
        help_text="Percentage retained by school"
    )
    admin_fee_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('5.00'),
        help_text="Administrative fee percentage"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True
    )
    
    # Eligible staff groups (JSON list of role names)
    eligible_roles = models.JSONField(
        default=list,
        help_text="List of roles eligible for distribution"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_fee_pools'
    )
    
    class Meta:
        db_table = 'fee_pools'
        ordering = ['name']
        verbose_name = 'Fee Pool'
        verbose_name_plural = 'Fee Pools'
    
    def __str__(self):
        return f"{self.name} ({self.pool_type})"
    
    @property
    def balance(self):
        """Current pool balance"""
        return self.total_collected - self.total_distributed
    
    @property
    def distributable_amount(self):
        """Amount available for distribution after deductions"""
        retention = self.total_collected * (self.school_retention_percent / 100)
        admin_fee = self.total_collected * (self.admin_fee_percent / 100)
        return self.total_collected - retention - admin_fee - self.total_distributed
    
    def add_collection(self, amount):
        """Add to total collected"""
        self.total_collected += Decimal(str(amount))
        self.save(update_fields=['total_collected', 'updated_at'])
    
    def record_distribution(self, amount):
        """Record a distribution from this pool"""
        if amount > self.distributable_amount:
            raise ValueError("Distribution amount exceeds available balance")
        self.total_distributed += Decimal(str(amount))
        self.save(update_fields=['total_distributed', 'updated_at'])


class Session(models.Model):
    """
    Fee collection session for a specific date.
    """
    
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        OPEN = 'OPEN', 'Open'
        PENDING_APPROVAL = 'PENDING_APPROVAL', 'Pending Approval'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        DISTRIBUTED = 'DISTRIBUTED', 'Distributed'
        LOCKED = 'LOCKED', 'Locked'
    
    class SessionType(models.TextChoices):
        REGULAR = 'REGULAR', 'Regular School Day'
        SATURDAY = 'SATURDAY', 'Saturday Class'
    
    # Basic info
    date = models.DateField(unique=True, db_index=True)
    session_type = models.CharField(
        max_length=20,
        choices=SessionType.choices,
        default=SessionType.REGULAR
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True
    )
    
    # Workflow tracking
    opened_at = models.DateTimeField(null=True, blank=True)
    opened_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='opened_sessions'
    )
    
    submitted_at = models.DateTimeField(null=True, blank=True)
    
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_sessions'
    )
    approval_notes = models.TextField(blank=True)
    
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rejected_sessions'
    )
    rejection_reason = models.TextField(blank=True)
    
    distributed_at = models.DateTimeField(null=True, blank=True)
    
    locked_at = models.DateTimeField(null=True, blank=True)
    locked_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='locked_sessions'
    )
    
    # Unlock tracking
    unlock_count = models.PositiveIntegerField(default=0)
    last_unlock_reason = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sessions'
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date', 'status']),
            models.Index(fields=['session_type', 'date']),
        ]
    
    def __str__(self):
        return f"Session {self.date} ({self.status})"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        if self.date > timezone.now().date():
            raise ValidationError({
                'date': 'Cannot create session for future date'
            })
    
    def can_transition_to(self, new_status):
        """Check if transition to new status is allowed"""
        transitions = {
            self.Status.DRAFT: [self.Status.OPEN],
            self.Status.OPEN: [self.Status.PENDING_APPROVAL],
            self.Status.PENDING_APPROVAL: [self.Status.APPROVED, self.Status.REJECTED],
            self.Status.REJECTED: [self.Status.OPEN],
            self.Status.APPROVED: [self.Status.DISTRIBUTED],
            self.Status.DISTRIBUTED: [self.Status.LOCKED],
            self.Status.LOCKED: [self.Status.DISTRIBUTED],  # Unlock
        }
        return new_status in transitions.get(self.status, [])
    
    def open_session(self, user):
        """Open session for collection"""
        if self.status != self.Status.DRAFT:
            raise ValueError('Can only open DRAFT sessions')
        
        self.status = self.Status.OPEN
        self.opened_at = timezone.now()
        self.opened_by = user
        self.save()
    
    def submit_for_approval(self):
        """Submit session for approval"""
        if self.status != self.Status.OPEN:
            raise ValueError('Can only submit OPEN sessions')
        
        self.status = self.Status.PENDING_APPROVAL
        self.submitted_at = timezone.now()
        self.save()
    
    def approve(self, user, notes=''):
        """Approve session"""
        if self.status != self.Status.PENDING_APPROVAL:
            raise ValueError('Can only approve PENDING sessions')
        
        self.status = self.Status.APPROVED
        self.approved_at = timezone.now()
        self.approved_by = user
        self.approval_notes = notes
        self.save()
    
    def reject(self, user, reason):
        """Reject session"""
        if self.status != self.Status.PENDING_APPROVAL:
            raise ValueError('Can only reject PENDING sessions')
        
        if not reason:
            raise ValueError('Rejection reason is required')
        
        self.status = self.Status.REJECTED
        self.rejected_at = timezone.now()
        self.rejected_by = user
        self.rejection_reason = reason
        self.save()
    
    def mark_distributed(self):
        """Mark session as distributed"""
        if self.status != self.Status.APPROVED:
            raise ValueError('Can only distribute APPROVED sessions')
        
        self.status = self.Status.DISTRIBUTED
        self.distributed_at = timezone.now()
        self.save()
    
    def lock(self, user):
        """Lock session"""
        if self.status != self.Status.DISTRIBUTED:
            raise ValueError('Can only lock DISTRIBUTED sessions')
        
        self.status = self.Status.LOCKED
        self.locked_at = timezone.now()
        self.locked_by = user
        self.save()
    
    def unlock(self, user, reason):
        """Unlock session (Bursar only)"""
        if self.status != self.Status.LOCKED:
            raise ValueError('Can only unlock LOCKED sessions')
        
        if not reason or len(reason) < 20:
            raise ValueError('Unlock reason must be at least 20 characters')
        
        self.status = self.Status.DISTRIBUTED
        self.unlock_count += 1
        self.last_unlock_reason = reason
        self.locked_at = None
        self.locked_by = None
        self.save()


class StaffAttendance(models.Model):
    """
    Staff attendance tracking for distribution calculation.
    """
    
    class Status(models.TextChoices):
        PRESENT = 'PRESENT', 'Present'
        LATE = 'LATE', 'Late'
        SICK = 'SICK', 'Sick'
        PERMISSION = 'PERMISSION', 'Permission'
        OFFICIAL_DUTY = 'OFFICIAL_DUTY', 'Official Duty'
        ABSENT = 'ABSENT', 'Absent'
    
    SHARE_WEIGHTS = {
        'PRESENT': Decimal('1.0'),
        'LATE': Decimal('0.5'),
        'SICK': Decimal('0.5'),
        'PERMISSION': Decimal('0.5'),
        'OFFICIAL_DUTY': Decimal('1.0'),
        'ABSENT': Decimal('0.0'),
    }
    
    staff = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='attendance_records'
    )
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name='attendance_records'
    )
    date = models.DateField(db_index=True)
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PRESENT
    )
    
    # Time tracking
    check_in_time = models.TimeField(null=True, blank=True)
    check_out_time = models.TimeField(null=True, blank=True)
    
    # Documentation
    documentation = models.FileField(
        upload_to='attendance_docs/%Y/%m/',
        blank=True,
        null=True
    )
    documentation_verified = models.BooleanField(default=False)
    
    notes = models.TextField(blank=True)
    
    # Audit
    recorded_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='recorded_attendances'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'staff_attendance'
        unique_together = ['staff', 'date']
        indexes = [
            models.Index(fields=['date', 'status']),
            models.Index(fields=['staff', 'date']),
        ]
    
    def __str__(self):
        return f"{self.staff.get_full_name()} - {self.date} - {self.status}"
    
    @property
    def share_weight(self):
        return self.SHARE_WEIGHTS.get(self.status, Decimal('0.0'))
    
    @property
    def requires_documentation(self):
        return self.status in [
            self.Status.SICK,
            self.Status.PERMISSION,
            self.Status.OFFICIAL_DUTY
        ]


class FeeCollection(models.Model):
    """
    Individual fee collection record.
    """
    
    class PaymentStatus(models.TextChoices):
        EXPECTED = 'EXPECTED', 'Expected'
        PAID_FULL = 'PAID_FULL', 'Paid (Full)'
        PAID_PARTIAL = 'PAID_PARTIAL', 'Paid (Partial)'
        EXEMPT = 'EXEMPT', 'Exempt'
        WAIVED = 'WAIVED', 'Waived'
        UNPAID = 'UNPAID', 'Unpaid'
    
    class UnpaidReason(models.TextChoices):
        NO_MONEY = 'NO_MONEY', 'No Money'
        FORGOT = 'FORGOT', 'Forgot'
        PARENT_ISSUE = 'PARENT_ISSUE', 'Parent Issue'
        ABSENT = 'ABSENT', 'Student Absent'
        OTHER = 'OTHER', 'Other'
    
    # Relationships
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name='fee_collections'
    )
    school_class = models.ForeignKey(
        'school.SchoolClass',
        on_delete=models.PROTECT,
        related_name='fee_collections'
    )
    student = models.ForeignKey(
        'school.Student',
        on_delete=models.PROTECT,
        related_name='fee_collections'
    )
    pool_type = models.CharField(
        max_length=20,
        choices=PoolType.choices,
        db_index=True
    )
    
    # Amounts
    expected_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.EXPECTED,
        db_index=True
    )
    unpaid_reason = models.CharField(
        max_length=20,
        choices=UnpaidReason.choices,
        blank=True
    )
    unpaid_notes = models.TextField(blank=True)
    
    # Waiver
    waiver_approved_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_waivers'
    )
    waiver_reason = models.TextField(blank=True)
    
    # Receipt
    receipt_number = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True
    )
    receipt_generated_at = models.DateTimeField(null=True, blank=True)
    
    # Audit
    recorded_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='recorded_collections'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'fee_collections'
        unique_together = ['session', 'student', 'pool_type']
        indexes = [
            models.Index(fields=['session', 'school_class']),
            models.Index(fields=['session', 'pool_type']),
            models.Index(fields=['student', 'session']),
            models.Index(fields=['status']),
            models.Index(fields=['receipt_number']),
        ]
    
    def __str__(self):
        return f"{self.student} - {self.pool_type} - {self.status}"
    
    @property
    def amount_outstanding(self):
        return max(self.expected_amount - self.amount_paid, Decimal('0.00'))
    
    @property
    def is_fully_paid(self):
        return self.amount_paid >= self.expected_amount
    
    def save(self, *args, **kwargs):
        # Auto-update status based on payment
        if self.amount_paid >= self.expected_amount:
            self.status = self.PaymentStatus.PAID_FULL
        elif self.amount_paid > 0:
            self.status = self.PaymentStatus.PAID_PARTIAL
        
        super().save(*args, **kwargs)
        
        # Create arrears if partial or unpaid
        if self.status in [self.PaymentStatus.PAID_PARTIAL, self.PaymentStatus.UNPAID]:
            self._create_or_update_arrears()
    
    def _create_or_update_arrears(self):
        StudentArrears.objects.update_or_create(
            student=self.student,
            session=self.session,
            pool_type=self.pool_type,
            defaults={
                'amount_owed': self.amount_outstanding,
                'original_fee_collection': self,
            }
        )
    
    def generate_receipt(self):
        """Generate receipt number"""
        if self.amount_paid <= 0:
            raise ValueError("Cannot generate receipt for zero payment")
        
        date_str = self.session.date.strftime('%Y%m%d')
        count = FeeCollection.objects.filter(
            session=self.session,
            receipt_number__isnull=False
        ).count() + 1
        
        self.receipt_number = f"EP-{date_str}-{count:04d}"
        self.receipt_generated_at = timezone.now()
        self.save(update_fields=['receipt_number', 'receipt_generated_at'])
        
        return self.receipt_number


class Distribution(models.Model):
    """
    Staff distribution record.
    """
    
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name='distributions'
    )
    pool_type = models.CharField(max_length=20, choices=PoolType.choices)
    staff = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='distributions'
    )
    
    # Amounts
    base_share = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Share before attendance adjustment"
    )
    adjusted_share = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Final share after attendance adjustment"
    )
    
    # Attendance info
    attendance_status = models.CharField(max_length=20, blank=True)
    attendance_weight = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('1.00')
    )
    
    # Special shares
    special_share_type = models.CharField(max_length=50, blank=True)
    special_share_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Calculation log
    calculation_log = models.JSONField(default=dict)
    
    # Payment tracking
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    paid_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='distributions_paid'
    )
    payment_reference = models.CharField(max_length=50, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'distributions'
        unique_together = ['session', 'pool_type', 'staff']
        indexes = [
            models.Index(fields=['session', 'pool_type']),
            models.Index(fields=['staff', 'session']),
            models.Index(fields=['is_paid']),
        ]
    
    def __str__(self):
        return f"{self.staff.get_full_name()} - {self.pool_type} - {self.adjusted_share}"
    
    @property
    def total_share(self):
        return self.adjusted_share + self.special_share_amount
    
    def mark_as_paid(self, user, reference=''):
        self.is_paid = True
        self.paid_at = timezone.now()
        self.paid_by = user
        self.payment_reference = reference
        self.save()


class PoolSummary(models.Model):
    """
    Summary of pool distribution for a session.
    """
    
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name='pool_summaries'
    )
    pool_type = models.CharField(max_length=20, choices=PoolType.choices)
    
    # Collection totals
    total_expected = models.DecimalField(max_digits=10, decimal_places=2)
    total_collected = models.DecimalField(max_digits=10, decimal_places=2)
    total_outstanding = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Deductions
    school_retention = models.DecimalField(max_digits=10, decimal_places=2)
    administrative_fee = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Distribution
    total_distributed = models.DecimalField(max_digits=10, decimal_places=2)
    recipient_count = models.PositiveIntegerField()
    
    # Metadata
    calculation_timestamp = models.DateTimeField(auto_now_add=True)
    calculation_log = models.JSONField(default=dict)
    
    class Meta:
        db_table = 'pool_summaries'
        unique_together = ['session', 'pool_type']
    
    def __str__(self):
        return f"{self.session.date} - {self.pool_type}"


class StudentArrears(models.Model):
    """
    Track student fee arrears.
    """
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PARTIAL = 'PARTIAL', 'Partially Paid'
        PAID = 'PAID', 'Paid'
        WAIVED = 'WAIVED', 'Waived'
    
    student = models.ForeignKey(
        'school.Student',
        on_delete=models.CASCADE,
        related_name='arrears'
    )
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name='arrears'
    )
    pool_type = models.CharField(max_length=20)
    original_fee_collection = models.ForeignKey(
        FeeCollection,
        on_delete=models.SET_NULL,
        null=True,
        related_name='arrears_records'
    )
    
    amount_owed = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    
    due_date = models.DateField(null=True, blank=True)
    
    # Waiver
    waived_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    waiver_reason = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'student_arrears'
        unique_together = ['student', 'session', 'pool_type']
        ordering = ['-session__date', 'student']
        indexes = [
            models.Index(fields=['student', 'status']),
            models.Index(fields=['status']),
        ]
    
    @property
    def balance(self):
        return self.amount_owed - self.amount_paid
    
    def record_payment(self, amount, recorded_by):
        """Record a payment against arrears"""
        old_paid = self.amount_paid
        self.amount_paid += amount
        
        if self.amount_paid >= self.amount_owed:
            self.amount_paid = self.amount_owed
            self.status = self.Status.PAID
        else:
            self.status = self.Status.PARTIAL
        
        self.save()
