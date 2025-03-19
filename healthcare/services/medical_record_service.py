# healthcare/services/medical_record_service.py
import random
import string
from django.db import transaction
from ..models import MedicalRecord

class MedicalRecordService:
    """Service for medical record operations"""
    
    @staticmethod
    def generate_mrn():
        """
        Generate a unique Medical Record Number
        
        Returns:
            str: A unique MRN
        """
        # Generate a random 8-digit number with a 2-letter prefix
        prefix = ''.join(random.choices(string.ascii_uppercase, k=2))
        digits = ''.join(random.choices(string.digits, k=8))
        mrn = f"{prefix}{digits}"
        
        # Check if it already exists
        while MedicalRecord.objects.filter(medical_record_number=mrn).exists():
            # If it exists, generate a new one
            digits = ''.join(random.choices(string.digits, k=8))
            mrn = f"{prefix}{digits}"
        
        return mrn
    
    @staticmethod
    @transaction.atomic
    def create_medical_record(patient, **kwargs):
        """
        Create a new medical record for a patient
        
        Args:
            patient: The patient user
            **kwargs: Additional fields for the medical record
            
        Returns:
            MedicalRecord: The created medical record
        """
        # Generate a unique MRN
        mrn = MedicalRecordService.generate_mrn()
        
        # Create the medical record
        record = MedicalRecord.objects.create(
            patient=patient,
            medical_record_number=mrn,
            **kwargs
        )
        
        return record
    
    @staticmethod
    def transfer_primary_physician(medical_record, new_physician):
        """
        Transfer a patient's primary physician
        
        Args:
            medical_record: The patient's medical record
            new_physician: The new primary physician
            
        Returns:
            MedicalRecord: The updated medical record
        """
        # Update the primary physician
        medical_record.primary_physician = new_physician
        medical_record.save()
        
        return medical_record
    
@staticmethod
def get_patient_summary(medical_record_id):
    """
    Get a summary of a patient's medical record
    
    Args:
        medical_record_id: The ID of the medical record
        
    Returns:
        dict: A summary of the patient's medical record
    """
    from ..models import (
        Allergy, Medication, Condition, VitalSign, LabTest
    )
    from ..serializers import (
        AllergySerializer, MedicationSerializer, ConditionSerializer,
        VitalSignSerializer, LabTestSerializer
    )
    
    # Get the medical record
    try:
        record = MedicalRecord.objects.get(id=medical_record_id)
    except MedicalRecord.DoesNotExist:
        return None
    
    # Get current conditions and medications
    current_conditions = record.get_active_conditions()
    current_medications = record.get_active_medications()
    allergies = record.get_allergies()
    
    # Get most recent vital signs
    recent_vitals = record.get_latest_vitals()
    
    # Get recent lab tests
    recent_labs = record.get_recent_lab_tests(limit=5)
    
    # Compile the summary using serializers
    summary = {
        'patient': record.patient.get_full_name(),
        'medical_record_number': record.medical_record_number,
        'age': record.calculate_age(),
        'gender': record.gender,
        'primary_physician': record.primary_physician.get_full_name() if record.primary_physician else None,
        'current_conditions': ConditionSerializer(current_conditions, many=True).data,
        'current_medications': MedicationSerializer(current_medications, many=True).data,
        'allergies': AllergySerializer(allergies, many=True).data,
        'recent_vitals': VitalSignSerializer(recent_vitals).data if recent_vitals else None,
        'recent_labs': LabTestSerializer(recent_labs, many=True).data
    }
    
    return summary
