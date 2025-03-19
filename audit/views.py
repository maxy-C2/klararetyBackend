# audit/views.py
import csv
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Q
from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import AuditEvent, AuditLogExport
from .serializers import AuditEventSerializer, AuditLogExportSerializer


class IsAdminUser(permissions.BasePermission):
    """
    Permission to only allow admin users to access audit logs.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_staff


class AuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing audit events.
    Only accessible to admin users.
    """
    queryset = AuditEvent.objects.all()
    serializer_class = AuditEventSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [filters.SearchFilter]
    search_fields = ['user__username', 'user__email', 'resource_type', 'description']
    
    def get_queryset(self):
        """
        Filter audit events based on query parameters:
        - user_id: Filter by user ID
        - event_type: Filter by event type
        - resource_type: Filter by resource type
        - start_date: Filter events after this date
        - end_date: Filter events before this date
        """
        queryset = super().get_queryset()
        
        # Apply filters from query parameters
        user_id = self.request.query_params.get('user_id')
        event_type = self.request.query_params.get('event_type')
        resource_type = self.request.query_params.get('resource_type')
        resource_id = self.request.query_params.get('resource_id')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        
        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)
        
        if resource_id:
            queryset = queryset.filter(resource_id=resource_id)
        
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def export(self, request):
        """
        Export audit events as CSV.
        Uses the same filtering as the list endpoint.
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        # Create the HttpResponse object with CSV header
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="audit_log_export.csv"'
        
        # Create CSV writer
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Timestamp', 'User ID', 'Username', 'User Role',
            'Event Type', 'Resource Type', 'Resource ID',
            'Description', 'IP Address', 'Status'
        ])
        
        # Write data rows
        for event in queryset:
            writer.writerow([
                event.id,
                event.timestamp.isoformat(),
                event.user_id if event.user else 'N/A',
                event.user.username if event.user else 'System',
                event.user_role,
                event.get_event_type_display(),
                event.resource_type,
                event.resource_id or 'N/A',
                event.description,
                event.ip_address,
                event.status
            ])
        
        # Record the export in the database
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        AuditLogExport.objects.create(
            user=request.user,
            query_params=request.query_params,
            record_count=queryset.count(),
            date_range_start=start_date if start_date else None,
            date_range_end=end_date if end_date else None,
            ip_address=self.get_client_ip(request)
        )
        
        return response
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Get a summary of audit events.
        """
        # Get date range from query params or default to last 30 days
        end_date = timezone.now()
        start_date = request.query_params.get(
            'start_date', 
            (end_date - timezone.timedelta(days=30)).isoformat()
        )
        
        # Filter by date range
        queryset = AuditEvent.objects.filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date
        )
        
        # Get counts by event type
        event_type_counts = {}
        for event_type, label in AuditEvent.EVENT_TYPES:
            event_type_counts[label] = queryset.filter(event_type=event_type).count()
        
        # Get counts by resource type
        resource_type_counts = {}
        resource_types = queryset.values_list('resource_type', flat=True).distinct()
        for resource_type in resource_types:
            resource_type_counts[resource_type] = queryset.filter(resource_type=resource_type).count()
        
        # Get counts by user role
        role_counts = {}
        roles = queryset.values_list('user_role', flat=True).distinct()
        for role in roles:
            if role:  # Skip None values
                role_counts[role] = queryset.filter(user_role=role).count()
        
        return Response({
            'total_events': queryset.count(),
            'date_range': {
                'start': start_date,
                'end': end_date.isoformat()
            },
            'event_types': event_type_counts,
            'resource_types': resource_type_counts,
            'user_roles': role_counts
        })
    
    def get_client_ip(self, request):
        """Get the client IP address accounting for proxies"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class AuditLogExportViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing audit log exports.
    Only accessible to admin users.
    """
    queryset = AuditLogExport.objects.all()
    serializer_class = AuditLogExportSerializer
    permission_classes = [IsAdminUser]
