# audit/admin.py
from django.contrib import admin
from .models import AuditEvent, AuditLogExport

@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'timestamp', 'user', 'user_role', 'event_type', 'resource_type', 'status')
    list_filter = ('event_type', 'resource_type', 'status', 'user_role')
    search_fields = ('user__username', 'user__email', 'description', 'ip_address')
    readonly_fields = (
        'timestamp', 'user', 'user_role', 'user_session', 'event_type', 
        'resource_type', 'resource_id', 'description', 'data', 
        'ip_address', 'user_agent', 'endpoint', 'status'
    )
    date_hierarchy = 'timestamp'

@admin.register(AuditLogExport)
class AuditLogExportAdmin(admin.ModelAdmin):
    list_display = ('id', 'timestamp', 'user', 'record_count')
    list_filter = ('timestamp',)
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('timestamp', 'user', 'file', 'query_params', 'record_count', 'date_range_start', 'date_range_end', 'ip_address')
