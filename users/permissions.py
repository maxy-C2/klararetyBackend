# users/permissions.py
from rest_framework import permissions

class IsOwnerOrProvider(permissions.BasePermission):
    """
    Custom permission to only allow owners of a profile or providers to view/edit it.
    
    - Provider role can access any patient profile
    - An owner (e.g., patient) can access their own profile
    """
    def has_object_permission(self, request, view, obj):
        # Provider role can access any patient profile
        if request.user.role == 'provider':
            return True
        
        # Owner can access their own profile
        return obj.user == request.user

class IsProviderOrReadOnly(permissions.BasePermission):
    """
    Allow only providers to modify data, all authenticated users can read.
    
    - Any authenticated user can perform read operations
    - Only providers can perform write operations
    """
    def has_permission(self, request, view):
        # Allow reading for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        
        # Allow writing only for providers
        return request.user.is_authenticated and request.user.role == 'provider'

class IsAdminOrSelfOnly(permissions.BasePermission):
    """
    Allow only admins or the user themselves to access.
    
    - Admins can access any user's data
    - Users can only access their own data
    """
    def has_object_permission(self, request, view, obj):
        # Admin can do anything
        if request.user.is_staff:
            return True
        
        # User can access only their own data
        return obj == request.user

class IsRoleOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission for role-based profiles that:
    - Allows users to edit only their own profile
    - Allows role-specific access patterns
    - Allows read-only access to other authenticated users
    
    For different roles:
    - Patients: Can edit their own profile, read other profiles
    - Providers: Can edit their own profile, read other profiles
    - Pharmacies: Can edit their own profile, read other profiles
    - Insurers: Can edit their own profile, read other profiles
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated

        # Write permissions are only allowed to the owner
        return obj.user == request.user
