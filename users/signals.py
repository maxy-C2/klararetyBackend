# users/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import (
    CustomUser, PatientProfile, ProviderProfile, 
    PharmcoProfile, InsurerProfile
)

@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Signal to automatically create the appropriate profile when a user is created.
    
    This ensures that each user has the proper profile object associated with their role,
    allowing role-specific data to be stored and retrieved correctly.
    """
    if created:
        # Create profile based on user role if it doesn't exist yet
        if instance.role == 'patient' and not hasattr(instance, 'patient_profile'):
            PatientProfile.objects.create(user=instance)
        elif instance.role == 'provider' and not hasattr(instance, 'provider_profile'):
            ProviderProfile.objects.create(user=instance)
        elif instance.role == 'pharmco' and not hasattr(instance, 'pharmco_profile'):
            PharmcoProfile.objects.create(user=instance)
        elif instance.role == 'insurer' and not hasattr(instance, 'insurer_profile'):
            InsurerProfile.objects.create(user=instance)
