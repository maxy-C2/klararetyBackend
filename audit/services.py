# audit/services.py
from django.utils import timezone
from .models import AuditEvent

class AuditService:
    """
    Service class for creating audit logs from anywhere in the application.
    """
    @staticmethod
    def log_event(user, event_type, resource_type, resource_id=None, description=None, 
                 data=None, ip_address=None, user_agent=None, endpoint=None, status='success'):
        """
        Create an audit event.
        
        Args:
            user: The user who performed the action
            event_type: Type of event (see AuditEvent.EVENT_TYPES)
            resource_type: Type of resource affected
            resource_id: ID of the resource (optional)
            description: Description of the event (optional)
            data: Additional data as JSON (optional)
            ip_address: IP address of the user (optional)
            user_agent: User agent of the client (optional)
            endpoint: API endpoint or URL (optional)
            status: Result status (default 'success')
        
        Returns:
            The created AuditEvent instance
        """
        # Create default description if none provided
        if description is None:
            description = f"{event_type} on {resource_type}"
            if resource_id:
                description += f" (ID: {resource_id})"
        
        # Create the audit event
        return AuditEvent.objects.create(
            user=user,
            user_role=getattr(user, 'role', None) if user else None,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            data=data,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            status=status,
            timestamp=timezone.now()
        )
    
    @staticmethod
    def log_login(user, ip_address=None, user_agent=None, status='success'):
        """Log a user login event"""
        return AuditService.log_event(
            user=user,
            event_type='login',
            resource_type='user.session',
            description=f"User login: {user.username}",
            ip_address=ip_address,
            user_agent=user_agent,
            status=status
        )
    
    @staticmethod
    def log_logout(user, ip_address=None, user_agent=None):
        """Log a user logout event"""
        return AuditService.log_event(
            user=user,
            event_type='logout',
            resource_type='user.session',
            description=f"User logout: {user.username}",
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_access_denied(user, resource_type, resource_id=None, ip_address=None, user_agent=None):
        """Log an access denied event"""
        return AuditService.log_event(
            user=user,
            event_type='access_denied',
            resource_type=resource_type,
            resource_id=resource_id,
            description=f"Access denied to {resource_type}",
            ip_address=ip_address,
            user_agent=user_agent,
            status='failure'
        )
    
    @staticmethod
    def log_data_export(user, resource_type, description=None, record_count=None, 
                       ip_address=None, user_agent=None):
        """Log a data export event"""
        data = {}
        if record_count is not None:
            data['record_count'] = record_count
            
        return AuditService.log_event(
            user=user,
            event_type='export',
            resource_type=resource_type,
            description=description or f"Data export of {resource_type}",
            data=data,
            ip_address=ip_address,
            user_agent=user_agent
        )
