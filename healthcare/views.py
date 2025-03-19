# healthcare/views.py
from rest_framework import viewsets, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.schemas.openapi import AutoSchema

from .models import (
    MedicalRecord, Allergy, Medication, Condition, Immunization,
    LabTest, LabResult, VitalSign, FamilyHistory, SurgicalHistory,
    MedicalNote, MedicalImage, HealthDocument, MedicalHistoryAudit
)
from .serializers import (
    MedicalRecordSerializer, AllergySerializer, MedicationSerializer,
    ConditionSerializer, ImmunizationSerializer, LabTestSerializer,
    LabResultSerializer, VitalSignSerializer, FamilyHistorySerializer,
    SurgicalHistorySerializer, MedicalNoteSerializer, MedicalImageSerializer,
    HealthDocumentSerializer
)
from .permissions import IsProviderOrPatientOwner, ProviderWritePatientReadOnly
from users.models import CustomUser
from .viewsets import AuditedModelViewSet

class MedicalRecordViewSet(AuditedModelViewSet):
    """
    API endpoint for managing medical records.
    
    list:
        Returns a list of medical records filtered by the user's role
        - Staff and providers can see all medical records
        - Patients can only see their own medical record
        
    retrieve:
        Returns detailed information about a specific medical record
        
    create:
        Creates a new medical record
        
    update:
        Updates a medical record
        
    partial_update:
        Updates one or more fields of a medical record
        
    destroy:
        Deletes a medical record
    """
    queryset = MedicalRecord.objects.all()
    serializer_class = MedicalRecordSerializer
    permission_classes = [IsProviderOrPatientOwner]
    filter_backends = [filters.SearchFilter]
    search_fields = ['patient__first_name', 'patient__last_name', 'medical_record_number']
    audit_model_name = "MedicalRecord"
    
    def get_queryset(self):
        """Filter records based on user role"""
        user = self.request.user
        
        # Admin can see all records
        if user.is_staff:
            return MedicalRecord.objects.all()
        
        # Providers can see all patient records
        if user.role == 'provider':
            return MedicalRecord.objects.all()
        
        # Patients can only see their own record
        if user.role == 'patient':
            return MedicalRecord.objects.filter(patient=user)
        
        return MedicalRecord.objects.none()
    
@action(detail=True, methods=['get'])
def summary(self, request, pk=None):
    """
    Get a summary of the patient's medical record
    
    Returns key information about the patient including:
    - Current conditions
    - Current medications
    - Allergies
    - Recent vital signs
    - Recent lab tests
    """
    record = self.get_object()
    
    # Create audit log for viewing summary
    self._create_audit_log(record, "Viewed Summary")
    
    # Use the service to get the summary data
    from .services.medical_record_service import MedicalRecordService
    summary = MedicalRecordService.get_patient_summary(record.id)
    
    if not summary:
        return Response({"error": "Could not generate summary"}, 
                       status=status.HTTP_404_NOT_FOUND)
    
    return Response(summary)


class AllergyViewSet(AuditedModelViewSet):
    """
    API endpoint for managing patient allergies.
    
    Supports filtering by medical_record parameter.
    
    list:
        Returns a list of allergies
        
    retrieve:
        Returns detailed information about a specific allergy
        
    create:
        Creates a new allergy record
        
    update:
        Updates an allergy record
        
    partial_update:
        Updates one or more fields of an allergy record
        
    destroy:
        Deletes an allergy record
    """
    queryset = Allergy.objects.all()
    serializer_class = AllergySerializer
    permission_classes = [ProviderWritePatientReadOnly]
    audit_model_name = "Allergy"


class MedicationViewSet(AuditedModelViewSet):
    """
    API endpoint for managing patient medications.
    
    Supports filtering by medical_record and active parameters.
    
    list:
        Returns a list of medications
        
    retrieve:
        Returns detailed information about a specific medication
        
    create:
        Creates a new medication record
        
    update:
        Updates a medication record
        
    partial_update:
        Updates one or more fields of a medication record
        
    destroy:
        Deletes a medication record
    """
    queryset = Medication.objects.all()
    serializer_class = MedicationSerializer
    permission_classes = [ProviderWritePatientReadOnly]
    filterset_fields = ['active', 'medical_record']
    audit_model_name = "Medication"
    
    def get_queryset(self):
        """Filter medications based on user role and active status"""
        queryset = super().get_queryset()
        active_only = self.request.query_params.get('active') == 'true'
        
        # Filter active medications if requested
        if active_only:
            queryset = queryset.filter(active=True)
            
        return queryset
    
    @action(detail=True, methods=['post'])
    def discontinue(self, request, pk=None):
        """
        Discontinue a medication
        
        Sets the medication as inactive and sets the end date to current date
        """
        medication = self.get_object()
        medication.active = False
        medication.end_date = timezone.now().date()
        medication.save()
        
        # Create audit log
        self._create_audit_log(medication, "Discontinued")
        
        serializer = self.get_serializer(medication)
        return Response(serializer.data)


class ConditionViewSet(AuditedModelViewSet):
    """
    API endpoint for managing patient conditions/diagnoses.
    
    Supports filtering by medical_record and active parameters.
    
    list:
        Returns a list of medical conditions
        
    retrieve:
        Returns detailed information about a specific condition
        
    create:
        Creates a new condition record
        
    update:
        Updates a condition record
        
    partial_update:
        Updates one or more fields of a condition record
        
    destroy:
        Deletes a condition record
    """
    queryset = Condition.objects.all()
    serializer_class = ConditionSerializer
    permission_classes = [ProviderWritePatientReadOnly]
    filterset_fields = ['active', 'medical_record']
    audit_model_name = "Condition"
    
    def get_queryset(self):
        """Filter conditions based on user role and active status"""
        queryset = super().get_queryset()
        active_only = self.request.query_params.get('active') == 'true'
        
        # Filter active conditions if requested
        if active_only:
            queryset = queryset.filter(active=True)
            
        return queryset
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """
        Mark a condition as resolved
        
        Sets the condition as inactive and sets the resolved date to current date
        """
        condition = self.get_object()
        condition.active = False
        condition.resolved_date = timezone.now().date()
        condition.save()
        
        # Create audit log
        self._create_audit_log(condition, "Resolved")
        
        serializer = self.get_serializer(condition)
        return Response(serializer.data)


class ImmunizationViewSet(AuditedModelViewSet):
    """
    API endpoint for managing patient immunizations/vaccinations.
    
    Supports filtering by medical_record parameter.
    
    list:
        Returns a list of immunizations
        
    retrieve:
        Returns detailed information about a specific immunization
        
    create:
        Creates a new immunization record
        
    update:
        Updates an immunization record
        
    partial_update:
        Updates one or more fields of an immunization record
        
    destroy:
        Deletes an immunization record
    """
    queryset = Immunization.objects.all()
    serializer_class = ImmunizationSerializer
    permission_classes = [ProviderWritePatientReadOnly]
    audit_model_name = "Immunization"


class LabTestViewSet(AuditedModelViewSet):
    """
    API endpoint for managing patient laboratory tests.
    
    Supports filtering by medical_record parameter.
    
    list:
        Returns a list of laboratory tests
        
    retrieve:
        Returns detailed information about a specific laboratory test
        
    create:
        Creates a new laboratory test record
        
    update:
        Updates a laboratory test record
        
    partial_update:
        Updates one or more fields of a laboratory test record
        
    destroy:
        Deletes a laboratory test record
    """
    queryset = LabTest.objects.all()
    serializer_class = LabTestSerializer
    permission_classes = [ProviderWritePatientReadOnly]
    audit_model_name = "LabTest"


class LabResultViewSet(AuditedModelViewSet):
    """
    API endpoint for managing patient laboratory test results.
    
    Supports filtering by lab_test parameter.
    
    list:
        Returns a list of laboratory test results
        
    retrieve:
        Returns detailed information about a specific laboratory test result
        
    create:
        Creates a new laboratory test result record
        
    update:
        Updates a laboratory test result record
        
    partial_update:
        Updates one or more fields of a laboratory test result record
        
    destroy:
        Deletes a laboratory test result record
    """
    queryset = LabResult.objects.all()
    serializer_class = LabResultSerializer
    permission_classes = [ProviderWritePatientReadOnly]
    audit_model_name = "LabResult"
    
    def get_queryset(self):
        """Filter lab results based on user role and lab test ID"""
        queryset = super().get_queryset()
        lab_test_id = self.request.query_params.get('lab_test')
        
        # Filter by lab test if specified
        if lab_test_id:
            queryset = queryset.filter(lab_test_id=lab_test_id)
            
        return queryset
    
    def perform_create(self, serializer):
        """Create lab result and update parent lab test if needed"""
        lab_result = super().perform_create(serializer)
        
        # Update the parent lab test to mark results as available
        lab_test = lab_result.lab_test
        if not lab_test.results_available:
            lab_test.results_available = True
            lab_test.results_date = timezone.now().date()
            lab_test.save()
            
        return lab_result


class VitalSignViewSet(AuditedModelViewSet):
    """
    API endpoint for managing patient vital signs.
    
    Supports filtering by medical_record parameter.
    
    list:
        Returns a list of vital sign records
        
    retrieve:
        Returns detailed information about a specific vital sign record
        
    create:
        Creates a new vital sign record
        
    update:
        Updates a vital sign record
        
    partial_update:
        Updates one or more fields of a vital sign record
        
    destroy:
        Deletes a vital sign record
    """
    queryset = VitalSign.objects.all()
    serializer_class = VitalSignSerializer
    permission_classes = [ProviderWritePatientReadOnly]
    audit_model_name = "VitalSign"


class FamilyHistoryViewSet(AuditedModelViewSet):
    """
    API endpoint for managing patient family history.
    
    Supports filtering by medical_record parameter.
    
    list:
        Returns a list of family history records
        
    retrieve:
        Returns detailed information about a specific family history record
        
    create:
        Creates a new family history record
        
    update:
        Updates a family history record
        
    partial_update:
        Updates one or more fields of a family history record
        
    destroy:
        Deletes a family history record
    """
    queryset = FamilyHistory.objects.all()
    serializer_class = FamilyHistorySerializer
    permission_classes = [ProviderWritePatientReadOnly]
    audit_model_name = "FamilyHistory"


class SurgicalHistoryViewSet(AuditedModelViewSet):
    """
    API endpoint for managing patient surgical history.
    
    Supports filtering by medical_record parameter.
    
    list:
        Returns a list of surgical history records
        
    retrieve:
        Returns detailed information about a specific surgical history record
        
    create:
        Creates a new surgical history record
        
    update:
        Updates a surgical history record
        
    partial_update:
        Updates one or more fields of a surgical history record
        
    destroy:
        Deletes a surgical history record
    """
    queryset = SurgicalHistory.objects.all()
    serializer_class = SurgicalHistorySerializer
    permission_classes = [ProviderWritePatientReadOnly]
    audit_model_name = "SurgicalHistory"


class MedicalNoteViewSet(AuditedModelViewSet):
    """
    API endpoint for managing clinical notes (progress notes, SOAP notes, etc.).
    
    Supports filtering by medical_record parameter.
    
    list:
        Returns a list of medical notes
        
    retrieve:
        Returns detailed information about a specific medical note
        
    create:
        Creates a new medical note
        
    update:
        Updates a medical note
        
    partial_update:
        Updates one or more fields of a medical note
        
    destroy:
        Deletes a medical note
    """
    queryset = MedicalNote.objects.all()
    serializer_class = MedicalNoteSerializer
    permission_classes = [ProviderWritePatientReadOnly]
    audit_model_name = "MedicalNote"
    
    def perform_create(self, serializer):
        """Validate SOAP notes and set provider if not provided"""
        # If this is a SOAP note, ensure proper fields are provided
        if serializer.validated_data.get('note_type') == 'soap':
            from rest_framework import serializers as rest_serializers
            for field in ['subjective', 'objective', 'assessment', 'plan']:
                if not serializer.validated_data.get(field):
                    raise rest_serializers.ValidationError({field: f"{field} is required for SOAP notes"})
        
        # Set the provider to the current user if not provided
        if not serializer.validated_data.get('provider'):
            instance = serializer.save(provider=self.request.user)
        else:
            instance = serializer.save()
            
        self._create_audit_log(instance, "Created")
        return instance


class MedicalImageViewSet(AuditedModelViewSet):
    """
    API endpoint for managing medical images (X-rays, MRIs, CT scans, etc.).
    
    Supports filtering by medical_record parameter.
    
    list:
        Returns a list of medical images
        
    retrieve:
        Returns detailed information about a specific medical image
        
    create:
        Creates a new medical image record
        
    update:
        Updates a medical image record
        
    partial_update:
        Updates one or more fields of a medical image record
        
    destroy:
        Deletes a medical image record
    """
    queryset = MedicalImage.objects.all()
    serializer_class = MedicalImageSerializer
    permission_classes = [ProviderWritePatientReadOnly]
    audit_model_name = "MedicalImage"
    
    def perform_create(self, serializer):
        """Set the ordering provider to current user if not provided"""
        # Set the ordering provider to the current user if not provided
        if not serializer.validated_data.get('ordered_by'):
            instance = serializer.save(ordered_by=self.request.user)
        else:
            instance = serializer.save()
            
        self._create_audit_log(instance, "Created")
        return instance


class HealthDocumentViewSet(AuditedModelViewSet):
    """
    API endpoint for managing health documents (referrals, consent forms, etc.).
    
    Supports filtering by medical_record parameter.
    
    list:
        Returns a list of health documents
        
    retrieve:
        Returns detailed information about a specific health document
        
    create:
        Creates a new health document record
        
    update:
        Updates a health document record
        
    partial_update:
        Updates one or more fields of a health document record
        
    destroy:
        Deletes a health document record
    """
    queryset = HealthDocument.objects.all()
    serializer_class = HealthDocumentSerializer
    permission_classes = [ProviderWritePatientReadOnly]
    audit_model_name = "HealthDocument"
    
    def perform_create(self, serializer):
        """Set the added_by field to current user"""
        # Set the added_by to the current user
        instance = serializer.save(added_by=self.request.user)
        self._create_audit_log(instance, "Created")
        return instance
