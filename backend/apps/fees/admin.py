# apps/fees/admin.py

from django.contrib import admin
from .models import Session, StaffAttendance, FeeCollection, Distribution, PoolSummary, StudentArrears


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['date', 'session_type', 'status', 'opened_by', 'approved_by']
    list_filter = ['status', 'session_type']
    search_fields = ['date']
    ordering = ['-date']
    date_hierarchy = 'date'
    
    readonly_fields = ['created_at', 'updated_at', 'opened_at', 'submitted_at', 
                       'approved_at', 'rejected_at', 'distributed_at', 'locked_at']


@admin.register(StaffAttendance)
class StaffAttendanceAdmin(admin.ModelAdmin):
    list_display = ['staff', 'date', 'status', 'check_in_time', 'recorded_by']
    list_filter = ['status', 'date']
    search_fields = ['staff__username', 'staff__first_name', 'staff__last_name']
    date_hierarchy = 'date'


@admin.register(FeeCollection)
class FeeCollectionAdmin(admin.ModelAdmin):
    list_display = ['student', 'session', 'pool_type', 'expected_amount', 'amount_paid', 'status']
    list_filter = ['status', 'pool_type', 'school_class']
    search_fields = ['student__student_id', 'student__first_name', 'student__last_name']
    raw_id_fields = ['student', 'session']


@admin.register(Distribution)
class DistributionAdmin(admin.ModelAdmin):
    list_display = ['staff', 'session', 'pool_type', 'adjusted_share', 'is_paid']
    list_filter = ['pool_type', 'is_paid']
    search_fields = ['staff__username', 'staff__first_name']


@admin.register(PoolSummary)
class PoolSummaryAdmin(admin.ModelAdmin):
    list_display = ['session', 'pool_type', 'total_collected', 'total_distributed', 'recipient_count']
    list_filter = ['pool_type']


@admin.register(StudentArrears)
class StudentArrearsAdmin(admin.ModelAdmin):
    list_display = ['student', 'session', 'pool_type', 'amount_owed', 'amount_paid', 'status']
    list_filter = ['status', 'pool_type']
    search_fields = ['student__student_id', 'student__first_name']