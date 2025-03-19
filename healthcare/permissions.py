# healthcare/permissions.py
from rest_framework import permissions

class IsProviderOrPatientOwner(permissions.BasePermission):
    """
    Allow access if the user is:
    1. A provider, or
    2. The patient who owns the medical record
    """
    def has_permission(self, request, view):
        # Ensure user is authenticated
        if not request.user.is_authenticated:
            return False
        
        # Providers have general access
        if request.user.role == 'provider':
            return True
        
        # Patients only have access to their own records
        if request.user.role == 'patient':
            # For list views, filter in the queryset
            # For detail views, check in has_object_permission
            return True
        
        # Admin users have access
        if request.user.is_staff:
            return True
        
        return False
    
    def has_object_permission(self, request, view, obj):
        # Staff can access anything
        if request.user.is_staff:
            return True
        
        # Providers can access any patient record
        if request.user.role == 'provider':
            return True
        
        # For patients, check if they own the record
        return self._check_patient_ownership(request.user, obj)
    
    def _check_patient_ownership(self, user, obj):
        """
        Check if the user is the patient who owns the record.
        Handles different models with different relations to patient.
        """
        if hasattr(obj, 'medical_record'):
            return obj.medical_record.patient == user
        elif hasattr(obj, 'patient'):
            return obj.patient == user
        elif hasattr(obj, 'lab_test') and hasattr(obj.lab_test, 'medical_record'):
            return obj.lab_test.medical_record.patient == user
        
        return False


class ProviderWritePatientReadOnly(permissions.BasePermission):
    """
    Allow read access for patients to their own data,
    but only providers can create/update/delete
    """
    def has_permission(self, request, view):
        # For safe methods (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            # Apply the rules from IsProviderOrPatientOwner
            if not request.user.is_authenticated:
                return False
            
            if request.user.role in ['provider', 'patient'] or request.user.is_staff:
                return True
            
            return False
        
        # For write methods (POST, PUT, PATCH, DELETE)
        return request.user.is_authenticated and (request.user.role == 'provider' or request.user.is_staff)
    
    def has_object_permission(self, request, view, obj):
        # For safe methods (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            # Apply the rules from IsProviderOrPatientOwner
            if request.user.is_staff:
                return True
            
            if request.user.role == 'provider':
                return True
            
            # For patients, check if they own the record
            return self._check_patient_ownership(request.user, obj)
        
        # For write methods (POST, PUT, PATCH, DELETE)
        return request.user.is_authenticated and (request.user.role == 'provider' or request.user.is_staff)
    
    def _check_patient_ownership(self, user, obj):
        """
        Check if the user is the patient who owns the record.
        Handles different models with different relations to patient.
        """
        if hasattr(obj, 'medical_record'):
            return obj.medical_record.patient == user
        elif hasattr(obj, 'patient'):
            return obj.patient == user
        elif hasattr(obj, 'lab_test') and hasattr(obj.lab_test, 'medical_record'):
            return obj.lab_test.medical_record.patient == user
        
        return False
    