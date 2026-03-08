# apps/school/models.py

"""
School structure models - Classes, Students, Categories.
"""

from decimal import Decimal
from io import BytesIO
import sys

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.validators import (
    FileExtensionValidator,
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models
from PIL import Image


class Category(models.TextChoices):
    """School category choices"""
    PRE_SCHOOL = 'PRE_SCHOOL', 'Pre-School'
    PRIMARY = 'PRIMARY', 'Primary'
    JHS = 'JHS', 'JHS'


class SchoolClass(models.Model):
    """
    School class model with fee structure.
    """

    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=50)
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        db_index=True
    )

    # Fee structure
    daily_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    jhs_extra_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Extra fee for JHS classes"
    )
    jhs3_extra_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Additional fee for JHS 3 only"
    )
    saturday_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Saturday class fee"
    )

    # Metadata
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'school_classes'
        ordering = ['sort_order', 'code']
        verbose_name = 'Class'
        verbose_name_plural = 'Classes'
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def is_jhs(self):
        return self.category == Category.JHS

    @property
    def is_jhs3(self):
        return self.code == 'B9'

    def get_all_fees(self):
        """Get dictionary of all applicable fees"""
        fees = {
            'daily_fee': self.daily_fee,
        }
        if self.is_jhs:
            fees['jhs_extra_fee'] = self.jhs_extra_fee
            if self.is_jhs3:
                fees['jhs3_extra_fee'] = self.jhs3_extra_fee
        if self.saturday_fee > 0:
            fees['saturday_fee'] = self.saturday_fee
        return fees

    def get_total_daily_fee(self, include_extras=True):
        """Calculate total possible daily fee"""
        total = self.daily_fee
        if include_extras and self.is_jhs:
            total += self.jhs_extra_fee
            if self.is_jhs3:
                total += self.jhs3_extra_fee
        return total


class Student(models.Model):
    """
    Student model with fee exemption support.
    """

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'
        TRANSFERRED = 'TRANSFERRED', 'Transferred'
        GRADUATED = 'GRADUATED', 'Graduated'

    class Gender(models.TextChoices):
        MALE = 'M', 'Male'
        FEMALE = 'F', 'Female'

    # Identification
    student_id = models.CharField(max_length=20, unique=True)

    # Personal info
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    other_names = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=Gender.choices)

    # Academic
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.PROTECT,
        related_name='students'
    )
    admission_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True
    )

    # Contact
    parent_name = models.CharField(max_length=100)
    parent_phone = models.CharField(max_length=15)
    parent_phone_alt = models.CharField(max_length=15, blank=True)
    parent_email = models.EmailField(blank=True)
    address = models.TextField(blank=True)

    # Fee exemption
    has_fee_exemption = models.BooleanField(default=False)
    exemption_percentage = models.PositiveIntegerField(
        default=0,
        validators=[MaxValueValidator(100)]
    )
    exemption_reason = models.TextField(blank=True)
    exemption_approved_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_exemptions'
    )
    exemption_valid_until = models.DateField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'students'
        ordering = ['school_class', 'last_name', 'first_name']
        indexes = [
            models.Index(fields=['school_class', 'status']),
            models.Index(fields=['student_id']),
            models.Index(fields=['last_name', 'first_name']),
        ]

    def __str__(self):
        return f"{self.student_id} - {self.full_name}"

    @property
    def full_name(self):
        names = [self.first_name]
        if self.other_names:
            names.append(self.other_names)
        names.append(self.last_name)
        return ' '.join(names)

    def get_daily_fee(self, pool_type='GEN_STUDIES'):
        """Get daily fee for specific pool with exemption applied"""
        from apps.fees.models import PoolType

        if pool_type == PoolType.GENERAL_STUDIES:
            base_fee = self.school_class.daily_fee
        elif pool_type == PoolType.JHS_EXTRA:
            base_fee = self.school_class.jhs_extra_fee
        elif pool_type == PoolType.JHS3_EXTRA:
            base_fee = self.school_class.jhs3_extra_fee
        elif pool_type == PoolType.SATURDAY:
            base_fee = self.school_class.saturday_fee
        else:
            base_fee = self.school_class.daily_fee

        if self.has_fee_exemption and self.exemption_percentage > 0:
            discount = base_fee * (Decimal(self.exemption_percentage) / Decimal('100'))
            return base_fee - discount

        return base_fee

    def get_arrears_balance(self):
        """Calculate total outstanding arrears"""
        from django.db.models import F, Sum
        from apps.fees.models import StudentArrears

        result = StudentArrears.objects.filter(
            student=self,
            status__in=['PENDING', 'PARTIAL']
        ).aggregate(
            total=Sum(F('amount_owed') - F('amount_paid'))
        )
        return result['total'] or Decimal('0.00')


class SchoolSettings(models.Model):
    """
    School-wide settings (singleton model).
    Used by reports/PDF generation for branding and defaults.
    """

    # School info
    school_name = models.CharField(
        max_length=200,
        default="E.P Basic School Ashaiman"
    )
    school_motto = models.CharField(
        max_length=200,
        default="Now Or Never"
    )
    school_address = models.TextField(
        default="Ashaiman, Greater Accra Region, Ghana"
    )
    school_phone = models.CharField(max_length=20, blank=True)
    school_email = models.EmailField(blank=True)
    school_po_box = models.CharField(max_length=50, blank=True)

    # Branding
    logo = models.ImageField(
        upload_to='school/logo/',
        validators=[FileExtensionValidator(allowed_extensions=['png', 'jpg', 'jpeg'])],
        blank=True,
        null=True
    )
    logo_watermark = models.ImageField(
        upload_to='school/watermark/',
        blank=True,
        null=True,
        help_text="Auto-generated faded version for watermarks"
    )

    # Fee distribution settings
    school_retention_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('10.00'),
        help_text="Percentage retained by school"
    )
    admin_fee_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('3.00'),
        help_text="Administrative fee percentage"
    )

    # Report settings
    report_header_color = models.CharField(max_length=7, default="#1a365d")
    report_accent_color = models.CharField(max_length=7, default="#3182ce")
    watermark_opacity = models.FloatField(default=0.06)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'school_settings'
        verbose_name = 'School Settings'
        verbose_name_plural = 'School Settings'

    def __str__(self):
        return self.school_name

    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        self.pk = 1

        super().save(*args, **kwargs)

        if self.logo:
            self._generate_watermark()
            super().save(update_fields=['logo_watermark', 'updated_at'])

    def _generate_watermark(self):
        """
        Generate a faded watermark version of the uploaded logo.
        """
        if not self.logo:
            return

        self.logo.open()
        img = Image.open(self.logo)
        img = img.convert('RGBA')

        max_size = (800, 800)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        alpha = img.split()[3]
        alpha = alpha.point(lambda p: int(p * self.watermark_opacity))
        img.putalpha(alpha)

        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        original_name = self.logo.name.split('/')[-1].split('.')[0]
        file_name = f"watermark_{original_name}.png"

        self.logo_watermark = InMemoryUploadedFile(
            buffer,
            field_name='ImageField',
            name=file_name,
            content_type='image/png',
            size=sys.getsizeof(buffer),
            charset=None,
        )

    @classmethod
    def get_settings(cls):
        """Get or create singleton settings"""
        settings_obj, _ = cls.objects.get_or_create(pk=1)
        return settings_obj

    def get_logo_url(self):
        if self.logo:
            return self.logo.url
        return '/static/images/default_logo.png'

    def get_watermark_url(self):
        if self.logo_watermark:
            return self.logo_watermark.url
        return self.get_logo_url()