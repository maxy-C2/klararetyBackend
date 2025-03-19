# audit/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone

class AuditEvent(models.Model):
    """
    Main model for storing audit events across the application.
    Complies with HIPAA audit requirements by tracking who, what, when, and where.
    """
    EVENT_TYPES = [
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('view', 'Record Viewed'),
        ('create', 'Record Created'),
        ('update', 'Record Updated'),
        ('delete', 'Record Deleted'),
        ('export', 'Data Exported'),
        ('import', 'Data Imported'),
        ('download', 'File Downloaded'),
        ('print', 'Data Printed'),
        ('share', 'Data Shared'),
        ('access_denied', 'Access Denied'),
        ('other', 'Other Activity'),
    ]

    # Who
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,  # Don't delete audit logs when a user is deleted
        related_name='audit_events',
        null=True,  # Allow null for system-generated events
        blank=True,
    )
    user_role = models.CharField(max_length=50, null=True, blank=True)
    user_session = models.CharField(max_length=100, null=True, blank=True)
    
    # What
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    resource_type = models.CharField(max_length=100)  # Model or resource type
    resource_id = models.CharField(max_length=100, null=True, blank=True)  # ID of the resource
    description = models.TextField()
    data = models.JSONField(null=True, blank=True)  # Additional context data
    
    # When
    timestamp = models.DateTimeField(default=timezone.now)
    
    # Where
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    endpoint = models.CharField(max_length=255, null=True, blank=True)  # API endpoint or URL
    
    # Result
    status = models.CharField(max_length=50, default='success')  # success, failure, etc.
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['event_type']),
            models.Index(fields=['resource_type']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['resource_type', 'resource_id']),
        ]
    
    def __str__(self):
        if self.user:
            user_str = f"{self.user.username} ({self.user_role or 'unknown role'})"
        else:
            user_str = "System"
        
        return f"{self.get_event_type_display()} by {user_str} on {self.resource_type} at {self.timestamp}"


class AuditLogExport(models.Model):
    """
    Tracks exports of audit logs for compliance reporting.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='audit_exports'
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to='audit_exports/%Y/%m/%d/')
    query_params = models.JSONField(null=True, blank=True)  # Store the filters used
    record_count = models.PositiveIntegerField(default=0)
    date_range_start = models.DateTimeField(null=True, blank=True)
    date_range_end = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    def __str__(self):
        return f"Audit log export by {self.user.username} at {self.timestamp}"
