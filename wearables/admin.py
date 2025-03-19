from datetime import timezone
from django.contrib import admin
from .models import WithingsProfile, WithingsMeasurement

class WithingsMeasurementInline(admin.TabularInline):
    model = WithingsMeasurement
    extra = 0
    fields = ('measurement_type', 'value', 'unit', 'measured_at')
    readonly_fields = ('measurement_type', 'value', 'unit', 'measured_at')
    max_num = 10
    can_delete = False
    verbose_name_plural = "Recent Measurements"
    
    def get_queryset(self, request):
        """Limit to the 10 most recent measurements"""
        queryset = super().get_queryset(request)
        return queryset.order_by('-measured_at')[:10]

@admin.register(WithingsProfile)
class WithingsProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'connection_status', 'last_updated')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'updated_at', 'token_expires_at')
    list_filter = ('created_at', 'updated_at')
    inlines = [WithingsMeasurementInline]
    
    def connection_status(self, obj):
        """Display connection status based on token validity"""
        if not obj.access_token:
            return "Not Connected"
        if obj.token_expires_at and obj.token_expires_at < timezone.now():
            return "Token Expired"
        return "Connected"
    connection_status.short_description = "Status"
    
    def last_updated(self, obj):
        return obj.updated_at
    last_updated.short_description = "Last Updated"
    
    def has_delete_permission(self, request, obj=None):
        """Override to prevent accidental deletion of profiles"""
        return False

@admin.register(WithingsMeasurement)
class WithingsMeasurementAdmin(admin.ModelAdmin):
    list_display = ('withings_profile', 'measurement_type', 'value', 'unit', 'measured_at')
    list_filter = ('measurement_type', 'measured_at', 'withings_profile')
    search_fields = ('withings_profile__user__username', 'measurement_type')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'measured_at'
    
    def get_queryset(self, request):
        """Add prefetch for better performance"""
        queryset = super().get_queryset(request)
        return queryset.select_related('withings_profile__user')
