# telemedicine/middleware.py
import logging
import json
from django.utils import timezone

logger = logging.getLogger('hipaa_audit')

class HIPAAComplianceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process the request
        response = self.get_response(request)
        
        # Log access to patient data
        if request.user.is_authenticated:
            # Check if path involves patient data
            if '/api/v1/telemedicine/' in request.path:
                self.log_patient_data_access(request, response)
        
        return response
    
    def log_patient_data_access(self, request, response):
        # Log only successful requests
        if 200 <= response.status_code < 300:
            # Basic request information
            log_data = {
                'timestamp': timezone.now().isoformat(),
                'user_id': request.user.id,
                'username': request.user.username,
                'user_role': request.user.role,
                'path': request.path,
                'method': request.method,
                'ip': request.META.get('REMOTE_ADDR', ''),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')
            }
            
            # For patient data access, add additional context
            if 'patient-profiles' in request.path or 'appointments' in request.path:
                # Try to determine which patient's data was accessed
                patient_id = None
                
                # Extract patient ID from URL if possible
                if '/patient-profiles/' in request.path:
                    parts = request.path.split('/')
                    try:
                        idx = parts.index('patient-profiles')
                        if idx + 1 < len(parts) and parts[idx + 1].isdigit():
                            patient_id = parts[idx + 1]
                    except ValueError:
                        pass
                
                if patient_id:
                    log_data['patient_id'] = patient_id
            
            # Log in a structured format
            logger.info(f"HIPAA_ACCESS: {json.dumps(log_data)}")
