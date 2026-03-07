# apps/school/admin.py

from django.contrib import admin
from .models import SchoolClass, Student, SchoolSettings


@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category', 'daily_fee', 'is_active', 'sort_order']
    list_filter = ['category', 'is_active']
    search_fields = ['code', 'name']
    ordering = ['sort_order']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('code', 'name', 'category', 'sort_order', 'is_active')
        }),
        ('Fees', {
            'fields': ('daily_fee', 'jhs_extra_fee', 'jhs3_extra_fee', 'saturday_fee')
        }),
    )


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['student_id', 'full_name', 'school_class', 'gender', 'status']
    list_filter = ['school_class', 'status', 'gender', 'has_fee_exemption']
    search_fields = ['student_id', 'first_name', 'last_name', 'parent_phone']
    ordering = ['school_class', 'last_name', 'first_name']
    
    fieldsets = (
        ('Identification', {
            'fields': ('student_id',)
        }),
        ('Personal Info', {
            'fields': ('first_name', 'other_names', 'last_name', 'date_of_birth', 'gender')
        }),
        ('Academic', {
            'fields': ('school_class', 'admission_date', 'status')
        }),
        ('Contact', {
            'fields': ('parent_name', 'parent_phone', 'parent_phone_alt', 'parent_email', 'address')
        }),
        ('Fee Exemption', {
            'fields': ('has_fee_exemption', 'exemption_percentage', 'exemption_reason', 
                      'exemption_approved_by', 'exemption_valid_until'),
            'classes': ['collapse']
        }),
    )


@admin.register(SchoolSettings)
class SchoolSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('School Information', {
            'fields': ('school_name', 'school_motto', 'school_address')
        }),
        ('Contact', {
            'fields': ('school_phone', 'school_email', 'school_po_box')
        }),
        ('Branding', {
            'fields': ('logo', 'report_header_color', 'watermark_opacity')
        }),
        ('Fee Settings', {
            'fields': ('school_retention_percentage', 'admin_fee_percentage')
        }),
    )
    
    def has_add_permission(self, request):
        return not SchoolSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False