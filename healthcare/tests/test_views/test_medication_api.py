# healthcare/tests/test_views/test_medication_api.py
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from healthcare.models import MedicalRecord, Medication
import json

User = get_user_model()

class MedicationAPITest(TestCase):
    """Test suite for the Medication API endpoints"""
    
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
            primary_physician=self.provider_user
        )
        
        self.other_record = MedicalRecord.objects.create(
            patient=self.other_patient,
            medical_record_number='CD87654321',
            date_of_birth=timezone.now().date() - timezone.timedelta(days=365*25),
            gender='Female',
            primary_physician=self.provider_user
        )
        
        # Create medications
        self.active_medication = Medication.objects.create(
            medical_record=self.patient_record,
            name='Test Medication Active',
            dosage='10mg',
            frequency='daily',
            start_date=timezone.now().date() - timezone.timedelta(days=30),
            prescribed_by=self.provider_user,
            active=True,
            reason='Testing active medication'
        )
        
        self.inactive_medication = Medication.objects.create(
            medical_record=self.patient_record,
            name='Test Medication Inactive',
            dosage='5mg',
            frequency='twice daily',
            start_date=timezone.now().date() - timezone.timedelta(days=60),
            end_date=timezone.now().date() - timezone.timedelta(days=15),
            prescribed_by=self.provider_user,
            active=False,
            reason='Testing inactive medication'
        )
        
        self.other_medication = Medication.objects.create(
            medical_record=self.other_record,
            name='Other Patient Medication',
            dosage='20mg',
            frequency='daily',
            start_date=timezone.now().date() - timezone.timedelta(days=45),
            prescribed_by=self.provider_user,
            active=True
        )
        
        # Setup API client
        self.client = APIClient()
        
        # URLs
        self.list_url = reverse('medication-list')
        self.detail_url = reverse('medication-detail', args=[self.active_medication.id])
        self.other_detail_url = reverse('medication-detail', args=[self.other_medication.id])
        self.discontinue_url = reverse('medication-discontinue', args=[self.active_medication.id])
    
    def test_list_medications_admin(self):
        """Test that admin can list all medications"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)  # Should see all medications
    
    def test_list_medications_provider(self):
        """Test that provider can list all medications"""
        self.client.force_authenticate(user=self.provider_user)
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)  # Should see all medications
    
    def test_list_medications_patient(self):
        """Test that patient can only see their own medications"""
        self.client.force_authenticate(user=self.patient_user)
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Should only see their medications
        
        # Verify the correct medications are returned
        medication_ids = [item['id'] for item in response.data]
        self.assertIn(self.active_medication.id, medication_ids)
        self.assertIn(self.inactive_medication.id, medication_ids)
        self.assertNotIn(self.other_medication.id, medication_ids)
    
    def test_filter_active_medications(self):
        """Test filtering medications by active status"""
        self.client.force_authenticate(user=self.provider_user)
        
        # Get only active medications
        response = self.client.get(f"{self.list_url}?active=true")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Should see 2 active medications
        
        medication_ids = [item['id'] for item in response.data]
        self.assertIn(self.active_medication.id, medication_ids)
        self.assertIn(self.other_medication.id, medication_ids)
        self.assertNotIn(self.inactive_medication.id, medication_ids)
    
    def test_filter_by_medical_record(self):
        """Test filtering medications by medical record"""
        self.client.force_authenticate(user=self.provider_user)
        
        # Get medications for a specific medical record
        response = self.client.get(f"{self.list_url}?medical_record={self.patient_record.id}")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Should see 2 medications for this patient
        
        medication_ids = [item['id'] for item in response.data]
        self.assertIn(self.active_medication.id, medication_ids)
        self.assertIn(self.inactive_medication.id, medication_ids)
        self.assertNotIn(self.other_medication.id, medication_ids)
    
    def test_retrieve_medication_admin(self):
        """Test that admin can retrieve any medication"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Retrieve patient's medication
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.active_medication.id)
        
        # Retrieve other patient's medication
        response = self.client.get(self.other_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.other_medication.id)
    
    def test_retrieve_medication_patient(self):
        """Test that patient can only retrieve their own medications"""
        self.client.force_authenticate(user=self.patient_user)
        
        # Retrieve own medication
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.active_medication.id)
        
        # Try to retrieve other patient's medication
        response = self.client.get(self.other_detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_create_medication_provider(self):
        """Test that provider can create a medication"""
        self.client.force_authenticate(user=self.provider_user)
        
        data = {
            'medical_record': self.patient_record.id,
            'name': 'New Test Medication',
            'dosage': '15mg',
            'frequency': 'twice daily',
            'start_date': timezone.now().date().isoformat(),
            'prescribed_by': self.provider_user.id,
            'active': True,
            'reason': 'Testing medication creation'
        }
        
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify the medication was created
        self.assertEqual(Medication.objects.count(), 4)
        new_medication = Medication.objects.get(name='New Test Medication')
        self.assertEqual(new_medication.dosage, '15mg')
        self.assertEqual(new_medication.medical_record, self.patient_record)
    
    def test_create_medication_patient(self):
        """Test that patient cannot create a medication"""
        self.client.force_authenticate(user=self.patient_user)
        
        data = {
            'medical_record': self.patient_record.id,
            'name': 'Self-Prescribed Medication',
            'dosage': '5mg',
            'frequency': 'daily',
            'start_date': timezone.now().date().isoformat(),
            'active': True
        }
        
        response = self.client.post(self.list_url, data, format='json')
        # Patient should be forbidden from creating medications
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Verify no new medication was created
        self.assertEqual(Medication.objects.count(), 3)
    
    def test_update_medication_provider(self):
        """Test that provider can update a medication"""
        self.client.force_authenticate(user=self.provider_user)
        
        update_data = {
            'dosage': '15mg',
            'frequency': 'three times daily'
        }
        
        response = self.client.patch(self.detail_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify the medication was updated
        self.active_medication.refresh_from_db()
        self.assertEqual(self.active_medication.dosage, '15mg')
        self.assertEqual(self.active_medication.frequency, 'three times daily')
    
    def test_update_medication_patient(self):
        """Test that patient cannot update a medication"""
        self.client.force_authenticate(user=self.patient_user)
        
        update_data = {
            'dosage': '15mg',
            'frequency': 'three times daily'
        }
        
        response = self.client.patch(self.detail_url, update_data, format='json')
        # Patient should be forbidden from updating medications
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Verify the medication was not updated
        self.active_medication.refresh_from_db()
        self.assertEqual(self.active_medication.dosage, '10mg')
        self.assertEqual(self.active_medication.frequency, 'daily')
    
    def test_discontinue_medication(self):
        """Test discontinuing a medication"""
        self.client.force_authenticate(user=self.provider_user)
        
        # Verify medication is active before the test
        self.assertTrue(self.active_medication.active)
        self.assertIsNone(self.active_medication.end_date)
        
        response = self.client.post(self.discontinue_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify the medication is now inactive and has an end date
        self.active_medication.refresh_from_db()
        self.assertFalse(self.active_medication.active)
        self.assertIsNotNone(self.active_medication.end_date)
        # End date should be today
        self.assertEqual(self.active_medication.end_date, timezone.now().date())
