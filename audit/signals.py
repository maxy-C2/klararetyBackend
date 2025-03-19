# audit/signals.py
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from .services import AuditService

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Log when a user logs in"""
    ip_address = None
    user_agent = None
    
    if request:
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT')
    
    AuditService.log_login(
        user=user,
        ip_address=ip_address,
        user_agent=user_agent
    )

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Log when a user logs out"""
    ip_address = None
    user_agent = None
    
    if request:
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT')
    
    if user:  # user can be None if session expired
        AuditService.log_logout(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent
        )
