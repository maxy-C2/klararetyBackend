# healthcare/tests/test_views/test_medical_record_api.py
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from healthcare.models import MedicalRecord
import json

User = get_user_model()

class MedicalRecordAPITest(TestCase):
    """Test suite for the Medical Record API"""
    
    def setUp(self):
        """Set up test data and API client"""
        # Create test users with different roles
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True
        )
        
        self.provider_user = User.objects.create_user(
            username='provider',
            email='provider@example.com',
            password='providerpass123',
            role='provider',
            first_name='Test',
            last_name='Provider'
        )
        
        self.patient_user = User.objects.create_user(
            username='patient',
            email='patient@example.com',
            password='patientpass123',
            role='patient',
            first_name='Test',
            last_name='Patient'
        )
        
        self.other_patient = User.objects.create_user(
            username='otherpatient',
            email='otherpatient@example.com',
            password='patientpass123',
            role='patient',
            first_name='Other',
            last_name='Patient'
        )
        
        # Create medical records
        self.patient_record = MedicalRecord.objects.create(
            patient=self.patient_user,
            medical_record_number='AB12345678',
            date_of_birth=timezone.now().date() - timezone.timedelta(days=365*30),
            gender='Male',
            primary_physician=self.provider_user,
            blood_type='O+',
            height=175.5,
            weight=70.5
        )
        
        self.other_patient_record = MedicalRecord.objects.create(
            patient=self.other_patient,
            medical_record_number='CD87654321',
            date_of_birth=timezone.now().date() - timezone.timedelta(days=365*25),
            gender='Female',
            primary_physician=self.provider_user,
            blood_type='A-',
            height=165.0,
            weight=60.0
        )
        
        # Setup API client
        self.client = APIClient()
        
        # URLs
        self.list_url = reverse('medicalrecord-list')
        self.detail_url = reverse('medicalrecord-detail', args=[self.patient_record.id])
        self.other_detail_url = reverse('medicalrecord-detail', args=[self.other_patient_record.id])
        self.summary_url = reverse('medicalrecord-summary', args=[self.patient_record.id])
    
    def test_list_medical_records_admin(self):
        """Test that admin can list all medical records"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Should see both records
    
    def test_list_medical_records_provider(self):
        """Test that provider can list all medical records"""
        self.client.force_authenticate(user=self.provider_user)
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Should see both records
    
    def test_list_medical_records_patient(self):
        """Test that patient can only list their own medical record"""
        self.client.force_authenticate(user=self.patient_user)
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Should only see their own record
        self.assertEqual(response.data[0]['id'], self.patient_record.id)
    
    def test_retrieve_medical_record_admin(self):
        """Test that admin can retrieve any medical record"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Test retrieving first patient record
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.patient_record.id)
        
        # Test retrieving second patient record
        response = self.client.get(self.other_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.other_patient_record.id)
    
    def test_retrieve_medical_record_provider(self):
        """Test that provider can retrieve any medical record"""
        self.client.force_authenticate(user=self.provider_user)
        
        # Test retrieving first patient record
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.patient_record.id)
        
        # Test retrieving second patient record
        response = self.client.get(self.other_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.other_patient_record.id)
    
    def test_retrieve_medical_record_patient(self):
        """Test that patient can only retrieve their own medical record"""
        self.client.force_authenticate(user=self.patient_user)
        
        # Test retrieving own record
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.patient_record.id)
        
        # Test retrieving another patient's record (should be forbidden)
        response = self.client.get(self.other_detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_create_medical_record_admin(self):
        """Test that admin can create a medical record"""
        self.client.force_authenticate(user=self.admin_user)
        
        new_patient = User.objects.create_user(
            username='newpatient',
            email='new@example.com',
            password='patientpass123',
            role='patient',
            first_name='New',
            last_name='Patient'
        )
        
        data = {
            'patient': new_patient.id,
            'medical_record_number': 'EF98765432',
            'date_of_birth': (timezone.now().date() - timezone.timedelta(days=365*40)).isoformat(),
            'gender': 'Female',
            'primary_physician': self.provider_user.id,
            'blood_type': 'B+',
            'height': 165.5,
            'weight': 65.0
        }
        
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(MedicalRecord.objects.count(), 3)
        self.assertEqual(response.data['medical_record_number'], 'EF98765432')
    
    def test_update_medical_record_provider(self):
        """Test that provider can update a medical record"""
        self.client.force_authenticate(user=self.provider_user)
        
        update_data = {
            'blood_type': 'AB+',
            'height': 176.0,
            'weight': 72.0
        }
        
        response = self.client.patch(self.detail_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh from database
        self.patient_record.refresh_from_db()
        self.assertEqual(self.patient_record.blood_type, 'AB+')
        self.assertEqual(self.patient_record.height, 176.0)
        self.assertEqual(self.patient_record.weight, 72.0)
    
    def test_update_medical_record_patient(self):
        """Test that patient cannot update their medical record (read-only)"""
        self.client.force_authenticate(user=self.patient_user)
        
        update_data = {
            'blood_type': 'AB+',
            'height': 176.0,
            'weight': 72.0
        }
        
        response = self.client.patch(self.detail_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Verify record was not changed
        self.patient_record.refresh_from_db()
        self.assertEqual(self.patient_record.blood_type, 'O+')
        self.assertEqual(self.patient_record.height, 175.5)
        self.assertEqual(self.patient_record.weight, 70.5)
    
    def test_get_summary_endpoint(self):
        """Test the summary endpoint for a medical record"""
        self.client.force_authenticate(user=self.provider_user)
        
        response = self.client.get(self.summary_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify summary data structure
        self.assertIn('patient', response.data)
        self.assertIn('medical_record_number', response.data)
        self.assertIn('age', response.data)
        self.assertIn('gender', response.data)
        self.assertIn('primary_physician', response.data)
