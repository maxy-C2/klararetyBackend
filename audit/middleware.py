# audit/middleware.py
import json
import logging
from django.utils import timezone
from .models import AuditEvent

logger = logging.getLogger('hipaa_audit')

class AuditLoggingMiddleware:
    """
    Middleware to log HIPAA-relevant activities to both the database and log files.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process the request and get the response
        response = self.get_response(request)
        
        # Skip static and media files
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return response
        
        # Log only authenticated requests
        if request.user.is_authenticated:
            self.log_request(request, response)
        
        return response
    
    def log_request(self, request, response):
        """Log API requests that might contain PHI"""
        
        # Skip certain paths that don't need to be audited
        skip_paths = ['/admin/jsi18n/', '/api/docs/', '/api/redoc/']
        if any(request.path.startswith(path) for path in skip_paths):
            return
        
        # Determine if this is a sensitive endpoint
        sensitive_paths = [
            '/api/v1/healthcare/',
            '/api/v1/telemedicine/',
            '/api/v1/users/'
        ]
        
        is_sensitive = any(request.path.startswith(path) for path in sensitive_paths)
        
        # For non-sensitive paths, only log modifying operations
        if not is_sensitive and request.method in ['GET', 'HEAD', 'OPTIONS']:
            return
        
        # Extract request details
        method = request.method
        path = request.path
        
        # Determine event type based on HTTP method
        event_type_map = {
            'GET': 'view',
            'POST': 'create',
            'PUT': 'update',
            'PATCH': 'update',
            'DELETE': 'delete'
        }
        event_type = event_type_map.get(method, 'other')
        
        # Determine resource type from path
        resource_type = self.get_resource_type_from_path(path)
        resource_id = self.get_resource_id_from_path(path)
        
        # Create description
        description = f"{method} request to {path}"
        
        # Create the audit event
        AuditEvent.objects.create(
            user=request.user,
            user_role=getattr(request.user, 'role', None),
            user_session=request.session.session_key,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            endpoint=path,
            status='success' if 200 <= response.status_code < 400 else 'failure'
        )
        
        # Also log to file for HIPAA compliance
        if is_sensitive:
            log_data = {
                'timestamp': timezone.now().isoformat(),
                'user_id': request.user.id,
                'username': request.user.username,
                'user_role': getattr(request.user, 'role', None),
                'event_type': event_type,
                'resource_type': resource_type,
                'resource_id': resource_id,
                'method': method,
                'path': path,
                'ip': self.get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'status_code': response.status_code
            }
            logger.info(f"HIPAA_AUDIT: {json.dumps(log_data)}")
    
    def get_resource_type_from_path(self, path):
        """Extract resource type from the path"""
        # Remove API prefix and split by slashes
        parts = path.replace('/api/v1/', '').split('/')
        
        if len(parts) >= 2:
            app = parts[0]  # e.g., healthcare, telemedicine
            resource = parts[1]  # e.g., medical-records, appointments
            return f"{app}.{resource}"
        
        return path
    
    def get_resource_id_from_path(self, path):
        """Extract resource ID from the path if present"""
        parts = path.split('/')
        
        # Check for ID pattern in path (typically after resource name)
        for i, part in enumerate(parts):
            if i > 0 and part.isdigit() and not parts[i-1].isdigit():
                return part
        
        return None
    
    def get_client_ip(self, request):
        """Get the client IP address accounting for proxies"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
