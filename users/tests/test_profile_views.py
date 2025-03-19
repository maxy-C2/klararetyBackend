# users/tests/test_profile_views.py
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from users.models import (
    PatientProfile, ProviderProfile, PharmcoProfile, InsurerProfile
)

User = get_user_model()

class PatientProfileViewSetTest(TestCase):
    """Test cases for the PatientProfileViewSet"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create a patient user
        self.patient_user = User.objects.create_user(
            username='patient',
            email='patient@example.com',
            password='password123',
            role='patient'
        )
        self.patient_profile = PatientProfile.objects.get(user=self.patient_user)
        
        # Create a provider user
        self.provider_user = User.objects.create_user(
            username='provider',
            email='provider@example.com',
            password='password123',
            role='provider'
        )
        
        # Create tokens
        self.patient_token = Token.objects.create(user=self.patient_user)
        self.provider_token = Token.objects.create(user=self.provider_user)
    
    def test_list_profiles_as_provider(self):
        """Test listing all patient profiles as a provider"""
        # Authenticate as provider
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.provider_token.key}')
        
        # Make request
        response = self.client.get(reverse('patientprofile-list'))
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)  # One patient profile
    
    def test_list_profiles_as_patient(self):
        """Test listing patient profiles as a patient (should only see own)"""
        # Authenticate as patient
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.patient_token.key}')
        
        # Make request
        response = self.client.get(reverse('patientprofile-list'))
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)  # Only own profile
        self.assertEqual(response.data['results'][0]['id'], self.patient_profile.id)
    
    def test_retrieve_own_profile(self):
        """Test retrieving own patient profile"""
        # Authenticate as patient
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.patient_token.key}')
        
        # Make request
        response = self.client.get(
            reverse('patientprofile-detail', kwargs={'pk': self.patient_profile.pk})
        )
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.patient_profile.id)
    
    def test_update_own_profile(self):
        """Test updating own patient profile"""
        # Authenticate as patient
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.patient_token.key}')
        
        # Update data
        update_data = {
            'medical_id': 'MED12345',
            'blood_type': 'O+',
            'allergies': 'Penicillin'
        }
        
        # Make request
        response = self.client.patch(
            reverse('patientprofile-detail', kwargs={'pk': self.patient_profile.pk}),
            data=update_data
        )
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify data was updated
        self.patient_profile.refresh_from_db()
        self.assertEqual(self.patient_profile.medical_id, 'MED12345')
        self.assertEqual(self.patient_profile.blood_type, 'O+')
        self.assertEqual(self.patient_profile.allergies, 'Penicillin')


class ProviderProfileViewSetTest(TestCase):
    """Test cases for the ProviderProfileViewSet"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create a provider user
        self.provider_user = User.objects.create_user(
            username='provider',
            email='provider@example.com',
            password='password123',
            role='provider'
        )
        self.provider_profile = ProviderProfile.objects.get(user=self.provider_user)
        
        # Create a patient user
        self.patient_user = User.objects.create_user(
            username='patient',
            email='patient@example.com',
            password='password123',
            role='patient'
        )
        
        # Create tokens
        self.provider_token = Token.objects.create(user=self.provider_user)
        self.patient_token = Token.objects.create(user=self.patient_user)
    
    def test_list_profiles_as_provider(self):
        """Test listing provider profiles as a provider (should only see own)"""
        # Authenticate as provider
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.provider_token.key}')
        
        # Make request
        response = self.client.get(reverse('providerprofile-list'))
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)  # Only own profile
        self.assertEqual(response.data['results'][0]['id'], self.provider_profile.id)
    
    def test_list_profiles_as_patient(self):
        """Test listing all provider profiles as a patient"""
        # Authenticate as patient
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.patient_token.key}')
        
        # Make request
        response = self.client.get(reverse('providerprofile-list'))
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)  # One provider profile
    
    def test_update_own_profile(self):
        """Test updating own provider profile"""
        # Authenticate as provider
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.provider_token.key}')
        
        # Update data
        update_data = {
            'license_number': 'LIC12345',
            'specialty': 'Cardiology',
            'practice_name': 'Heart Health Clinic'
        }
        
        # Make request
        response = self.client.patch(
            reverse('providerprofile-detail', kwargs={'pk': self.provider_profile.pk}),
            data=update_data
        )
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify data was updated
        self.provider_profile.refresh_from_db()
        self.assertEqual(self.provider_profile.license_number, 'LIC12345')
        self.assertEqual(self.provider_profile.specialty, 'Cardiology')
        self.assertEqual(self.provider_profile.practice_name, 'Heart Health Clinic')
