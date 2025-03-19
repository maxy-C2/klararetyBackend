# telemedicine/permissions.py
from rest_framework import permissions

class IsProviderOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow providers to edit objects.
    """
    def has_permission(self, request, view):
        # Read permissions are allowed to any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        
        # Write permissions are only allowed to providers
        return request.user.is_authenticated and request.user.role == 'provider'


class IsPatientOrProvider(permissions.BasePermission):
    """
    Custom permission to only allow patients or providers to access objects.
    """
    def has_permission(self, request, view):
        # Only allow authenticated users
        if not request.user.is_authenticated:
            return False
        
        # Allow access to patients and providers
        return request.user.role in ['patient', 'provider'] or request.user.is_staff


class IsAppointmentParticipant(permissions.BasePermission):
    """
    Custom permission to only allow participants of an appointment to access it.
    """
    def has_object_permission(self, request, view, obj):
        # Staff can access anything
        if request.user.is_staff:
            return True
        
        # Only allow access to participants
        return request.user == obj.patient or request.user == obj.provider
