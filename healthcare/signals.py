# healthcare/signals.py
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import (
    MedicalRecord, Allergy, Medication, Condition, Immunization,
    LabTest, LabResult, VitalSign, FamilyHistory, SurgicalHistory,
    MedicalNote, MedicalImage, HealthDocument, MedicalHistoryAudit
)
from .services.medical_record_service import MedicalRecordService

User = get_user_model()

@receiver(post_save, sender=User)
def create_medical_record_for_new_patient(sender, instance, created, **kwargs):
    """Create a medical record for new patient users"""
    if created and instance.role == 'patient':
        # Check if the user already has a medical record
        if not hasattr(instance, 'medical_record'):
            # Get date of birth from user if available
            date_of_birth = instance.date_of_birth or timezone.now().date()
            
            # Create the medical record
            MedicalRecordService.create_medical_record(
                patient=instance,
                date_of_birth=date_of_birth,
                gender='Not Specified'  # Default, can be updated later
            )

@receiver(pre_delete, sender=MedicalRecord)
def log_medical_record_deletion(sender, instance, **kwargs):
    """Log medical record deletion"""
    # Create a special audit log entry for deletion
    MedicalHistoryAudit.objects.create(
        medical_record=instance,
        user_id=1,  # Default system user ID
        action="Deleted",
        model_name="MedicalRecord",
        record_id=instance.id,
        details="Medical record deleted from the system"
    )
