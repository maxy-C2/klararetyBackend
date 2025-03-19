# consent/models.py
from django.db import models
from users.models import CustomUser

class ConsentAgreement(models.Model):
    CONSENT_TYPES = [
        ('data_sharing', 'Data Sharing'),
        ('research', 'Research Participation'),
        ('marketing', 'Marketing Communications'),
        ('third_party', 'Third Party Access'),
    ]
    
    patient = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='consent_agreements',
        limit_choices_to={'role': 'patient'}
    )
    consent_type = models.CharField(max_length=50, choices=CONSENT_TYPES)
    
    granted = models.BooleanField(default=False)
    granted_to = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='received_consents'
    )
    
    details = models.TextField()
    
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    
    class Meta:
        ordering = ['-granted_at']
        unique_together = ['patient', 'consent_type', 'granted_to']