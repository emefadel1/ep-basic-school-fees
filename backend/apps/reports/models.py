from django.db import models
from apps.school.models import Student, SchoolClass
from apps.fees.models import FeePool, StudentArrears
from django.utils import timezone

class DailyCollectionReport(models.Model):
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name='daily_reports')
    report_date = models.DateField(default=timezone.now)
    total_collected = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_pending = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'daily_collection_reports'
        ordering = ['-report_date']
        indexes = [
            models.Index(fields=['school_class', 'report_date']),
        ]

    def __str__(self):
        return f"{self.school_class.name} - {self.report_date}"

class ArrearsSummary(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='arrears_summary')
    total_owed = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arrears_summary'
        indexes = [
            models.Index(fields=['student']),
        ]

    def __str__(self):
        return f"{self.student.full_name} - Balance: {self.balance}"

    @property
    def balance(self):
        return max(self.total_owed - self.total_paid, 0.00)

class FeeAnalytics(models.Model):
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name='fee_analytics')
    total_students = models.PositiveIntegerField(default=0)
    total_fees_expected = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_fees_collected = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_arrears = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    report_generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'fee_analytics'
        indexes = [
            models.Index(fields=['school_class']),
        ]

    def __str__(self):
        return f"{self.school_class.name} - Analytics {self.report_generated_at.date()}"
