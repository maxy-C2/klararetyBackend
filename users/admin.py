# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import (
    CustomUser, PatientProfile, ProviderProfile, 
    PharmcoProfile, InsurerProfile, UserSession
)

class CustomUserAdmin(UserAdmin):
    """Admin configuration for the CustomUser model with enhanced security features"""
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff', 'two_factor_enabled')
    list_filter = ('role', 'is_staff', 'is_active', 'two_factor_enabled', 'account_locked')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email', 'phone_number', 'date_of_birth')}),
        (_('Role'), {'fields': ('role',)}),
        (_('Security'), {'fields': ('two_factor_enabled', 'two_factor_secret', 'account_locked', 'failed_login_attempts')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined', 'last_password_change')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'is_staff', 'is_active'),
        }),
    )
    
    readonly_fields = ('last_login', 'date_joined', 'last_password_change')
    actions = ['lock_accounts', 'unlock_accounts', 'disable_2fa']
    
    def lock_accounts(self, request, queryset):
        """Admin action to lock multiple user accounts"""
        for user in queryset:
            user.lock_account()
        self.message_user(request, f"{queryset.count()} account(s) have been locked.")
    lock_accounts.short_description = "Lock selected accounts"
    
    def unlock_accounts(self, request, queryset):
        """Admin action to unlock multiple user accounts"""
        for user in queryset:
            user.unlock_account()
        self.message_user(request, f"{queryset.count()} account(s) have been unlocked.")
    unlock_accounts.short_description = "Unlock selected accounts"
    
    def disable_2fa(self, request, queryset):
        """Admin action to disable two-factor authentication for multiple users"""
        queryset.update(two_factor_enabled=False)
        self.message_user(request, f"Two-factor authentication disabled for {queryset.count()} user(s).")
    disable_2fa.short_description = "Disable two-factor authentication"


class BaseProfileAdmin(admin.ModelAdmin):
    """Base admin configuration for all profile types"""
    raw_id_fields = ('user',)
    search_fields = ('user__username', 'user__email')


class PatientProfileAdmin(BaseProfileAdmin):
    """Admin configuration for patient profiles"""
    list_display = ('user', 'medical_id', 'blood_type')
    search_fields = BaseProfileAdmin.search_fields + ('medical_id',)


class ProviderProfileAdmin(BaseProfileAdmin):
    """Admin configuration for healthcare provider profiles"""
    list_display = ('user', 'license_number', 'specialty', 'practice_name')
    search_fields = BaseProfileAdmin.search_fields + ('license_number', 'specialty')


class PharmcoProfileAdmin(BaseProfileAdmin):
    """Admin configuration for pharmacy profiles"""
    list_display = ('user', 'pharmacy_name', 'pharmacy_license', 'does_delivery')
    search_fields = BaseProfileAdmin.search_fields + ('pharmacy_name', 'pharmacy_license')


class InsurerProfileAdmin(BaseProfileAdmin):
    """Admin configuration for insurance provider profiles"""
    list_display = ('user', 'company_name', 'policy_prefix')
    search_fields = BaseProfileAdmin.search_fields + ('company_name',)


class UserSessionAdmin(admin.ModelAdmin):
    """Admin configuration for user session tracking and audit"""
    list_display = ('user', 'ip_address', 'login_time', 'logout_time', 'was_forced_logout')
    list_filter = ('was_forced_logout',)
    search_fields = ('user__username', 'user__email', 'ip_address')
    readonly_fields = ('user', 'session_key', 'ip_address', 'user_agent', 'location', 'login_time', 'logout_time')


# Register models with the admin site
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(PatientProfile, PatientProfileAdmin)
admin.site.register(ProviderProfile, ProviderProfileAdmin)
admin.site.register(PharmcoProfile, PharmcoProfileAdmin)
admin.site.register(InsurerProfile, InsurerProfileAdmin)
admin.site.register(UserSession, UserSessionAdmin)
