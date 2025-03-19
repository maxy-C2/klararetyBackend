# healthcare/viewsets.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.utils import timezone
from .models import MedicalHistoryAudit

class AuditedModelViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet that automatically creates audit logs for CRUD operations
    and handles common filtering based on user roles.
    """
    audit_model_name = None  # Override in child class
    
    def get_queryset(self):
        """
        Filter queryset based on user role.
        
        - Staff and providers can see all records
        - Patients can only see their own records
        """
        user = self.request.user
        queryset = super().get_queryset()
        
        # Apply common filters from query parameters
        medical_record_id = self.request.query_params.get('medical_record')
        if medical_record_id and hasattr(self.queryset.model, 'medical_record'):
            queryset = queryset.filter(medical_record_id=medical_record_id)
        
        # Admin and providers can see all records
        if user.is_staff or user.role == 'provider':
            return queryset
        
        # Patients can only see their own records
        if user.role == 'patient':
            # Different models have different relations to patient
            if hasattr(self.queryset.model, 'medical_record'):
                return queryset.filter(medical_record__patient=user)
            elif hasattr(self.queryset.model, 'patient'):
                return queryset.filter(patient=user)
            elif hasattr(self.queryset.model, 'lab_test'):
                return queryset.filter(lab_test__medical_record__patient=user)
                
        return self.queryset.model.objects.none()
    
    def _create_audit_log(self, instance, action):
        """Create an audit log entry for the given instance and action"""
        if not self.audit_model_name:
            return  # Skip if no audit_model_name defined
            
        # Determine the medical record for different model types
        if hasattr(instance, 'medical_record'):
            medical_record = instance.medical_record
        elif hasattr(instance, 'lab_test') and hasattr(instance.lab_test, 'medical_record'):
            medical_record = instance.lab_test.medical_record
        else:
            return  # No medical record found
        
        # Create the audit log
        MedicalHistoryAudit.objects.create(
            medical_record=medical_record,
            user=self.request.user,
            action=action,
            model_name=self.audit_model_name,
            record_id=instance.id,
            ip_address=self.request.META.get('REMOTE_ADDR', '')
        )
    
    def perform_create(self, serializer):
        """Create object and audit log"""
        instance = serializer.save()
        self._create_audit_log(instance, "Created")
        return instance
    
    def perform_update(self, serializer):
        """Update object and create audit log"""
        instance = serializer.save()
        self._create_audit_log(instance, "Updated")
        return instance
        
    def perform_destroy(self, instance):
        """Delete object and create audit log"""
        self._create_audit_log(instance, "Deleted")
        super().perform_destroy(instance)
    
    def retrieve(self, request, *args, **kwargs):
        """Get object and log view"""
        instance = self.get_object()
        self._create_audit_log(instance, "Viewed")
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
