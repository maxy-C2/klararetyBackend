# users/tests/test_permissions.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from users.permissions import (
    IsOwnerOrProvider, IsProviderOrReadOnly, IsAdminOrSelfOnly
)
from users.models import PatientProfile

User = get_user_model()

class PermissionsTest(TestCase):
    """Test cases for custom permissions"""
    
    def setUp(self):
        self.factory = APIRequestFactory()
        
        # Create users with different roles
        self.patient_user = User.objects.create_user(
            username='patient',
            email='patient@example.com',
            password='password123',
            role='patient'
        )
        self.patient_profile = PatientProfile.objects.get(user=self.patient_user)
        
        self.provider_user = User.objects.create_user(
            username='provider',
            email='provider@example.com',
            password='password123',
            role='provider'
        )
        
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='password123',
            role='provider',
            is_staff=True
        )
        
        self.another_patient = User.objects.create_user(
            username='another_patient',
            email='another@example.com',
            password='password123',
            role='patient'
        )
    
    def test_is_owner_or_provider_permission(self):
        """Test the IsOwnerOrProvider permission"""
        permission = IsOwnerOrProvider()
        
        # Patient accessing their own profile
        request = self.factory.get('/')
        request.user = self.patient_user
        self.assertTrue(permission.has_object_permission(
            request, None, self.patient_profile
        ))
        
        # Provider accessing a patient's profile
        request = self.factory.get('/')
        request.user = self.provider_user
        self.assertTrue(permission.has_object_permission(
            request, None, self.patient_profile
        ))
        
        # Another patient accessing someone else's profile
        request = self.factory.get('/')
        request.user = self.another_patient
        self.assertFalse(permission.has_object_permission(
            request, None, self.patient_profile
        ))
    
    def test_is_provider_or_read_only_permission(self):
        """Test the IsProviderOrReadOnly permission"""
        permission = IsProviderOrReadOnly()
        
        # Provider with GET request
        request = self.factory.get('/')
        request.user = self.provider_user
        self.assertTrue(permission.has_permission(request, None))
        
        # Provider with POST request
        request = self.factory.post('/')
        request.user = self.provider_user
        self.assertTrue(permission.has_permission(request, None))
        
        # Patient with GET request
        request = self.factory.get('/')
        request.user = self.patient_user
        self.assertTrue(permission.has_permission(request, None))
        
        # Patient with POST request
        request = self.factory.post('/')
        request.user = self.patient_user
        self.assertFalse(permission.has_permission(request, None))
    
    def test_is_admin_or_self_only_permission(self):
        """Test the IsAdminOrSelfOnly permission"""
        permission = IsAdminOrSelfOnly()
        
        # Admin accessing any user
        request = self.factory.get('/')
        request.user = self.admin_user
        self.assertTrue(permission.has_object_permission(
            request, None, self.patient_user
        ))
        
        # User accessing themselves
        request = self.factory.get('/')
        request.user = self.patient_user
        self.assertTrue(permission.has_object_permission(
            request, None, self.patient_user
        ))
        
        # User accessing another user
        request = self.factory.get('/')
        request.user = self.patient_user
        self.assertFalse(permission.has_object_permission(
            request, None, self.provider_user
        ))
