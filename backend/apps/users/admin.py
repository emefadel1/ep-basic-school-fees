# apps/users/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, PushSubscription


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'full_name', 'role', 'assigned_class', 'is_active']
    list_filter = ['role', 'is_active', 'is_staff', 'assigned_class']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'staff_id']
    ordering = ['last_name', 'first_name']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Role & Assignment', {
            'fields': ('role', 'staff_id', 'assigned_class', 'assigned_category')
        }),
        ('Contact', {
            'fields': ('phone_number', 'profile_picture')
        }),
        ('Staff Status', {
            'fields': ('is_active_staff', 'date_joined_school')
        }),
    )
    
    def full_name(self, obj):
        return obj.get_full_name()
    full_name.short_description = 'Name'


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['user__username', 'user__email']