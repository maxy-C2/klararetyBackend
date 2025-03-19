# audit/serializers.py
from rest_framework import serializers
from .models import AuditEvent, AuditLogExport
from users.serializers import CustomUserSerializer

class AuditEventSerializer(serializers.ModelSerializer):
    """Serializer for audit events"""
    user_details = CustomUserSerializer(source='user', read_only=True)
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    
    class Meta:
        model = AuditEvent
        fields = [
            'id', 'user', 'user_details', 'user_role', 'event_type', 
            'event_type_display', 'resource_type', 'resource_id', 
            'description', 'data', 'timestamp', 'ip_address', 
            'user_agent', 'endpoint', 'status'
        ]
        read_only_fields = fields


class AuditLogExportSerializer(serializers.ModelSerializer):
    """Serializer for audit log exports"""
    user_details = CustomUserSerializer(source='user', read_only=True)
    
    class Meta:
        model = AuditLogExport
        fields = [
            'id', 'user', 'user_details', 'timestamp', 'file',
            'query_params', 'record_count', 'date_range_start',
            'date_range_end', 'ip_address'
        ]
        read_only_fields = ['timestamp', 'record_count', 'file']
