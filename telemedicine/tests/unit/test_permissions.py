# telemedicine/tests/test_permissions.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView
from datetime import timedelta
from unittest.mock import MagicMock

from telemedicine.models import Appointment
from telemedicine.permissions import (
    IsProviderOrReadOnly, IsPatientOrProvider, IsAppointmentParticipant
)

User = get_user_model()

class IsProviderOrReadOnlyTests(TestCase):
    def setUp(self):
        # Create test users
        self.patient = User.objects.create_user(
            username='testpatient',
            email='patient@example.com',
            password='testpass123',
            role='patient'
        )
        self.provider = User.objects.create_user(
            username='testprovider',
            email='provider@example.com',
            password='testpass123',
            role='provider'
        )
        self.admin = User.objects.create_user(
            username='testadmin',
            email='admin@example.com',
            password='testpass123',
            role='admin',
            is_staff=True
        )
        
        self.permission = IsProviderOrReadOnly()
        self.factory = APIRequestFactory()
        self.view = APIView()
    
    def test_allows_read_to_authenticated_users(self):
        """Test that read methods are allowed for all authenticated users"""
        # Test GET method
        request = self.factory.get('/')
        request.user = self.patient
        self.assertTrue(self.permission.has_permission(request, self.view))
        
        # Test HEAD method
        request = self.factory.head('/')
        request.user = self.patient
        self.assertTrue(self.permission.has_permission(request, self.view))
        
        # Test OPTIONS method
        request = self.factory.options('/')
        request.user = self.patient
        self.assertTrue(self.permission.has_permission(request, self.view))
    
    def test_allows_write_only_to_providers(self):
        """Test that write methods are only allowed for providers"""
        # Test POST method with provider
        request = self.factory.post('/')
        request.user = self.provider
        self.assertTrue(self.permission.has_permission(request, self.view))
        
        # Test PUT method with provider
        request = self.factory.put('/')
        request.user = self.provider
        self.assertTrue(self.permission.has_permission(request, self.view))
        
        # Test PATCH method with provider
        request = self.factory.patch('/')
        request.user = self.provider
        self.assertTrue(self.permission.has_permission(request, self.view))
        
        # Test DELETE method with provider
        request = self.factory.delete('/')
        request.user = self.provider
        self.assertTrue(self.permission.has_permission(request, self.view))
    
    def test_denies_write_to_non_providers(self):
        """Test that write methods are denied for non-providers"""
        # Test POST method with patient
        request = self.factory.post('/')
        request.user = self.patient
        self.assertFalse(self.permission.has_permission(request, self.view))
        
        # Test PUT method with patient
        request = self.factory.put('/')
        request.user = self.patient
        self.assertFalse(self.permission.has_permission(request, self.view))
        
        # Test PATCH method with admin (not a provider)
        request = self.factory.patch('/')
        request.user = self.admin
        self.assertFalse(self.permission.has_permission(request, self.view))
    
    def test_denies_unauthenticated_requests(self):
        """Test that unauthenticated requests are denied"""
        # Anonymous user for GET
        request = self.factory.get('/')
        request.user = MagicMock(is_authenticated=False)
        self.assertFalse(self.permission.has_permission(request, self.view))
        
        # Anonymous user for POST
        request = self.factory.post('/')
        request.user = MagicMock(is_authenticated=False)
        self.assertFalse(self.permission.has_permission(request, self.view))


class IsPatientOrProviderTests(TestCase):
    def setUp(self):
        # Create test users
        self.patient = User.objects.create_user(
            username='testpatient',
            email='patient@example.com',
            password='testpass123',
            role='patient'
        )
        self.provider = User.objects.create_user(
            username='testprovider',
            email='provider@example.com',
            password='testpass123',
            role='provider'
        )
        self.admin = User.objects.create_user(
            username='testadmin',
            email='admin@example.com',
            password='testpass123',
            role='admin',
            is_staff=True
        )
        self.pharmco = User.objects.create_user(
            username='testpharmco',
            email='pharmacy@example.com',
            password='testpass123',
            role='pharmco'
        )
        
        self.permission = IsPatientOrProvider()
        self.factory = APIRequestFactory()
        self.view = APIView()
    
    def test_allows_patients(self):
        """Test that patients are allowed"""
        request = self.factory.get('/')
        request.user = self.patient
        self.assertTrue(self.permission.has_permission(request, self.view))
    
    def test_allows_providers(self):
        """Test that providers are allowed"""
        request = self.factory.get('/')
        request.user = self.provider
        self.assertTrue(self.permission.has_permission(request, self.view))
    
    def test_allows_admin(self):
        """Test that admin staff are allowed"""
        request = self.factory.get('/')
        request.user = self.admin
        self.assertTrue(self.permission.has_permission(request, self.view))
    
    def test_denies_other_roles(self):
        """Test that other roles are denied"""
        request = self.factory.get('/')
        request.user = self.pharmco
        self.assertFalse(self.permission.has_permission(request, self.view))
    
    def test_denies_unauthenticated_requests(self):
        """Test that unauthenticated requests are denied"""
        request = self.factory.get('/')
        request.user = MagicMock(is_authenticated=False)
        self.assertFalse(self.permission.has_permission(request, self.view))


class IsAppointmentParticipantTests(TestCase):
    def setUp(self):
        # Create test users
        self.patient = User.objects.create_user(
            username='testpatient',
            email='patient@example.com',
            password='testpass123',
            role='patient'
        )
        self.provider = User.objects.create_user(
            username='testprovider',
            email='provider@example.com',
            password='testpass123',
            role='provider'
        )
        self.other_patient = User.objects.create_user(
            username='otherpatient',
            email='other@example.com',
            password='testpass123',
            role='patient'
        )
        self.admin = User.objects.create_user(
            username='testadmin',
            email='admin@example.com',
            password='testpass123',
            role='admin',
            is_staff=True
        )
        
        # Create a test appointment
        self.now = timezone.now()
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            provider=self.provider,
            scheduled_time=self.now + timedelta(days=1),
            end_time=self.now + timedelta(days=1, hours=1),
            reason='Annual checkup',
            appointment_type='video_consultation'
        )
        
        self.permission = IsAppointmentParticipant()
        self.factory = APIRequestFactory()
        self.view = APIView()
    
    def test_allows_patient_participant(self):
        """Test that the patient who is part of the appointment is allowed"""
        request = self.factory.get('/')
        request.user = self.patient
        self.assertTrue(self.permission.has_object_permission(request, self.view, self.appointment))
    
    def test_allows_provider_participant(self):
        """Test that the provider who is part of the appointment is allowed"""
        request = self.factory.get('/')
        request.user = self.provider
        self.assertTrue(self.permission.has_object_permission(request, self.view, self.appointment))
    
    def test_allows_admin(self):
        """Test that admin staff are allowed"""
        request = self.factory.get('/')
        request.user = self.admin
        self.assertTrue(self.permission.has_object_permission(request, self.view, self.appointment))
    
    def test_denies_non_participants(self):
        """Test that non-participants are denied"""
        request = self.factory.get('/')
        request.user = self.other_patient
        self.assertFalse(self.permission.has_object_permission(request, self.view, self.appointment))
