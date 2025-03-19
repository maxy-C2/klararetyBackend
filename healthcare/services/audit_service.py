# healthcare/services/audit_service.py
from django.db import transaction
from ..models import MedicalHistoryAudit
import logging

logger = logging.getLogger(__name__)

class AuditService:
    """
    Service for managing audit logs for medical records.
    Follows HIPAA audit logging requirements.
    """
    
    @staticmethod
    @transaction.atomic
    def log_action(medical_record, user, action, model_name, record_id, ip_address=None, details=None):
        """
        Create an audit log entry.
        
        Args:
            medical_record: The medical record being accessed
            user: The user performing the action
            action: The action being performed (Created, Updated, Viewed, etc.)
            model_name: The name of the model being accessed
            record_id: The ID of the record being accessed
            ip_address: The IP address of the user (optional)
            details: Additional details about the action (optional)
            
        Returns:
            MedicalHistoryAudit: The created audit log entry
        """
        try:
            audit_log = MedicalHistoryAudit.objects.create(
                medical_record=medical_record,
                user=user,
                action=action,
                model_name=model_name,
                record_id=record_id,
                ip_address=ip_address,
                details=details
            )
            return audit_log
        except Exception as e:
            logger.error(f"Error creating audit log: {str(e)}")
            # Don't re-raise the exception to prevent disrupting the main workflow
            # but log the error for investigation
            return None
    
    @staticmethod
    def get_audit_logs_for_record(medical_record_id, limit=100):
        """
        Get the latest audit logs for a medical record.
        
        Args:
            medical_record_id: The ID of the medical record
            limit: The maximum number of logs to return
            
        Returns:
            QuerySet: A queryset of audit logs
        """
        return MedicalHistoryAudit.objects.filter(
            medical_record_id=medical_record_id
        ).order_by('-timestamp')[:limit]
    
    @staticmethod
    def get_user_access_logs(user_id, limit=100):
        """
        Get the latest audit logs for a specific user.
        
        Args:
            user_id: The ID of the user
            limit: The maximum number of logs to return
            
        Returns:
            QuerySet: A queryset of audit logs
        """
        return MedicalHistoryAudit.objects.filter(
            user_id=user_id
        ).order_by('-timestamp')[:limit]
    
    @staticmethod
    def get_record_access_history(medical_record_id, days=30):
        """
        Get a summary of who accessed a medical record within a time period.
        
        Args:
            medical_record_id: The ID of the medical record
            days: The number of days to look back
            
        Returns:
            dict: A summary of access by user and action
        """
        from django.utils import timezone
        from django.db.models import Count
        
        # Calculate the start date
        start_date = timezone.now() - timezone.timedelta(days=days)
        
        # Get the logs
        logs = MedicalHistoryAudit.objects.filter(
            medical_record_id=medical_record_id,
            timestamp__gte=start_date
        )
        
        # Get summary by user
        access_by_user = logs.values(
            'user__username', 'user__first_name', 'user__last_name', 'user__role'
        ).annotate(
            access_count=Count('id')
        ).order_by('-access_count')
        
        # Get summary by action
        access_by_action = logs.values('action').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return {
            'total_access_count': logs.count(),
            'access_by_user': list(access_by_user),
            'access_by_action': list(access_by_action),
            'period_days': days
        }
