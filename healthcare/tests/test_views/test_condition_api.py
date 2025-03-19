# healthcare/tests/test_views/test_condition_api.py
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from healthcare.models import MedicalRecord, Condition

User = get_user_model()

class ConditionAPITest(TestCase):
    """Test suite for the Condition API endpoints"""
    
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
        
        # Create conditions
        self.active_condition = Condition.objects.create(
            medical_record=self.patient_record,
            name='Hypertension',
            icd10_code='I10',
            diagnosis_date=timezone.now().date() - timezone.timedelta(days=90),
            diagnosed_by=self.provider_user,
            active=True,
            notes='Essential hypertension'
        )
        
        self.inactive_condition = Condition.objects.create(
            medical_record=self.patient_record,
            name='Acute Bronchitis',
            icd10_code='J20.9',
            diagnosis_date=timezone.now().date() - timezone.timedelta(days=120),
            resolved_date=timezone.now().date() - timezone.timedelta(days=90),
            diagnosed_by=self.provider_user,
            active=False,
            notes='Resolved'
        )
        
        self.other_condition = Condition.objects.create(
            medical_record=self.other_record,
            name='Diabetes Type 2',
            icd10_code='E11.9',
            diagnosis_date=timezone.now().date() - timezone.timedelta(days=180),
            diagnosed_by=self.provider_user,
            active=True
        )
        
        # Setup API client
        self.client = APIClient()
        
        # URLs
        self.list_url = reverse('condition-list')
        self.detail_url = reverse('condition-detail', args=[self.active_condition.id])
        self.other_detail_url = reverse('condition-detail', args=[self.other_condition.id])
        self.resolve_url = reverse('condition-resolve', args=[self.active_condition.id])
    
    def test_list_conditions_admin(self):
        """Test that admin can list all conditions"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)  # Should see all conditions
    
    def test_list_conditions_provider(self):
        """Test that provider can list all conditions"""
        self.client.force_authenticate(user=self.provider_user)
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)  # Should see all conditions
    
    def test_list_conditions_patient(self):
        """Test that patient can only see their own conditions"""
        self.client.force_authenticate(user=self.patient_user)
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Should only see their conditions
        
        # Verify the correct conditions are returned
        condition_ids = [item['id'] for item in response.data]
        self.assertIn(self.active_condition.id, condition_ids)
        self.assertIn(self.inactive_condition.id, condition_ids)
        self.assertNotIn(self.other_condition.id, condition_ids)
    
    def test_filter_active_conditions(self):
        """Test filtering conditions by active status"""
        self.client.force_authenticate(user=self.provider_user)
        
        # Get only active conditions
        response = self.client.get(f"{self.list_url}?active=true")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Should see 2 active conditions
        
        condition_ids = [item['id'] for item in response.data]
        self.assertIn(self.active_condition.id, condition_ids)
        self.assertIn(self.other_condition.id, condition_ids)
        self.assertNotIn(self.inactive_condition.id, condition_ids)
    
    def test_filter_by_medical_record(self):
        """Test filtering conditions by medical record"""
        self.client.force_authenticate(user=self.provider_user)
        
        # Get conditions for a specific medical record
        response = self.client.get(f"{self.list_url}?medical_record={self.patient_record.id}")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Should see 2 conditions for this patient
        
        condition_ids = [item['id'] for item in response.data]
        self.assertIn(self.active_condition.id, condition_ids)
        self.assertIn(self.inactive_condition.id, condition_ids)
        self.assertNotIn(self.other_condition.id, condition_ids)
    
    def test_retrieve_condition_admin(self):
        """Test that admin can retrieve any condition"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Retrieve patient's condition
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.active_condition.id)
        self.assertEqual(response.data['name'], 'Hypertension')
        
        # Retrieve other patient's condition
        response = self.client.get(self.other_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.other_condition.id)
        self.assertEqual(response.data['name'], 'Diabetes Type 2')
    
    def test_retrieve_condition_patient(self):
        """Test that patient can only retrieve their own conditions"""
        self.client.force_authenticate(user=self.patient_user)
        
        # Retrieve own condition
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.active_condition.id)
        
        # Try to retrieve other patient's condition
        response = self.client.get(self.other_detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_create_condition_provider(self):
        """Test that provider can create a condition"""
        self.client.force_authenticate(user=self.provider_user)
        
        data = {
            'medical_record': self.patient_record.id,
            'name': 'Asthma',
            'icd10_code': 'J45.909',
            'diagnosis_date': timezone.now().date().isoformat(),
            'diagnosed_by': self.provider_user.id,
            'active': True,
            'notes': 'Mild persistent asthma'
        }
        
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify the condition was created
        self.assertEqual(Condition.objects.count(), 4)
        new_condition = Condition.objects.get(name='Asthma')
        self.assertEqual(new_condition.icd10_code, 'J45.909')
        self.assertEqual(new_condition.medical_record, self.patient_record)
    
    def test_create_condition_patient(self):
        """Test that patient cannot create a condition"""
        self.client.force_authenticate(user=self.patient_user)
        
        data = {
            'medical_record': self.patient_record.id,
            'name': 'Self-Diagnosed Condition',
            'diagnosis_date': timezone.now().date().isoformat(),
            'active': True
        }
        
        response = self.client.post(self.list_url, data, format='json')
        # Patient should be forbidden from creating conditions
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Verify no new condition was created
        self.assertEqual(Condition.objects.count(), 3)
    
    def test_update_condition_provider(self):
        """Test that provider can update a condition"""
        self.client.force_authenticate(user=self.provider_user)
        
        update_data = {
            'name': 'Hypertension, Essential',
            'notes': 'Updated diagnosis notes'
        }
        
        response = self.client.patch(self.detail_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify the condition was updated
        self.active_condition.refresh_from_db()
        self.assertEqual(self.active_condition.name, 'Hypertension, Essential')
        self.assertEqual(self.active_condition.notes, 'Updated diagnosis notes')
    
    def test_update_condition_patient(self):
        """Test that patient cannot update a condition"""
        self.client.force_authenticate(user=self.patient_user)
        
        update_data = {
            'name': 'Modified by Patient',
            'notes': 'Patient added notes'
        }
        
        response = self.client.patch(self.detail_url, update_data, format='json')
        # Patient should be forbidden from updating conditions
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Verify the condition was not updated
        self.active_condition.refresh_from_db()
        self.assertEqual(self.active_condition.name, 'Hypertension')
        self.assertEqual(self.active_condition.notes, 'Essential hypertension')
    
    def test_resolve_condition(self):
        """Test resolving a condition"""
        self.client.force_authenticate(user=self.provider_user)
        
        # Verify condition is active before the test
        self.assertTrue(self.active_condition.active)
        self.assertIsNone(self.active_condition.resolved_date)
        
        response = self.client.post(self.resolve_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify the condition is now resolved
        self.active_condition.refresh_from_db()
        self.assertFalse(self.active_condition.active)
        self.assertIsNotNone(self.active_condition.resolved_date)
        # Resolved date should be today
        self.assertEqual(self.active_condition.resolved_date, timezone.now().date())
