# healthcare/tests/test_integration/test_audit_trail.py
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from healthcare.models import (
    MedicalRecord, Allergy, MedicalHistoryAudit
)

User = get_user_model()

class AuditTrailIntegrationTest(TestCase):
    """
    Integration test for the audit trail functionality.
    Tests that audit logs are properly created during API operations.
    """
    
    def setUp(self):
        """Set up test data and API client"""
        # Create test users with different roles
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True
        )
        
        self.provider = User.objects.create_user(
            username='provider',
            email='provider@example.com',
            password='providerpass123',
            role='provider',
            first_name='Test',
            last_name='Provider'
        )
        
        self.patient = User.objects.create_user(
            username='patient',
            email='patient@example.com',
            password='patientpass123',
            role='patient',
            first_name='Test',
            last_name='Patient',
            date_of_birth=timezone.now().date() - timezone.timedelta(days=365*30)
        )
        
        # Create medical record
        self.medical_record = MedicalRecord.objects.create(
            patient=self.patient,
            medical_record_number='AB12345678',
            date_of_birth=timezone.now().date() - timezone.timedelta(days=365*30),
            gender='Male',
            primary_physician=self.provider
        )
        
        # Setup API client
        self.client = APIClient()
        
        # Clear any initial audit logs from setup
        MedicalHistoryAudit.objects.all().delete()
    
    def test_audit_trail_creation(self):
        """Test that audit logs are created for various API operations"""
        
        # 1. Provider views a medical record
        self.client.force_authenticate(user=self.provider)
        
        # Get initial audit log count
        initial_count = MedicalHistoryAudit.objects.count()
        
        # View medical record
        medical_record_url = reverse('medicalrecord-detail', args=[self.medical_record.id])
        response = self.client.get(medical_record_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify audit log was created
        self.assertEqual(MedicalHistoryAudit.objects.count(), initial_count + 1)
        log = MedicalHistoryAudit.objects.latest('timestamp')
        self.assertEqual(log.user, self.provider)
        self.assertEqual(log.action, "Viewed")
        self.assertEqual(log.model_name, "MedicalRecord")
        self.assertEqual(log.record_id, self.medical_record.id)
        
        # 2. Provider adds an allergy (Create operation)
        allergies_url = reverse('allergy-list')
        allergy_data = {
            'medical_record': self.medical_record.id,
            'allergen': 'Penicillin',
            'reaction': 'Rash',
            'severity': 'Moderate',
            'diagnosed_date': timezone.now().date().isoformat()
        }
        
        response = self.client.post(allergies_url, allergy_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        allergy_id = response.data['id']
        
        # Verify audit log was created for allergy creation
        self.assertEqual(MedicalHistoryAudit.objects.count(), initial_count + 2)
        log = MedicalHistoryAudit.objects.latest('timestamp')
        self.assertEqual(log.user, self.provider)
        self.assertEqual(log.action, "Created")
        self.assertEqual(log.model_name, "Allergy")
        self.assertEqual(log.record_id, allergy_id)
        
        # 3. Provider updates the allergy (Update operation)
        allergy_url = reverse('allergy-detail', args=[allergy_id])
        update_data = {
            'severity': 'Severe'
        }
        
        response = self.client.patch(allergy_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify audit log was created for allergy update
        self.assertEqual(MedicalHistoryAudit.objects.count(), initial_count + 3)
        log = MedicalHistoryAudit.objects.latest('timestamp')
        self.assertEqual(log.user, self.provider)
        self.assertEqual(log.action, "Updated")
        self.assertEqual(log.model_name, "Allergy")
        self.assertEqual(log.record_id, allergy_id)
        
        # 4. Provider deletes the allergy (Delete operation)
        response = self.client.delete(allergy_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify audit log was created for allergy deletion
        self.assertEqual(MedicalHistoryAudit.objects.count(), initial_count + 4)
        log = MedicalHistoryAudit.objects.latest('timestamp')
        self.assertEqual(log.user, self.provider)
        self.assertEqual(log.action, "Deleted")
        self.assertEqual(log.model_name, "Allergy")
        self.assertEqual(log.record_id, allergy_id)
        
        # 5. Patient views their own record
        self.client.force_authenticate(user=self.patient)
        response = self.client.get(medical_record_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify audit log was created for patient viewing their record
        self.assertEqual(MedicalHistoryAudit.objects.count(), initial_count + 5)
        log = MedicalHistoryAudit.objects.latest('timestamp')
        self.assertEqual(log.user, self.patient)
        self.assertEqual(log.action, "Viewed")
        self.assertEqual(log.model_name, "MedicalRecord")
    
    def test_audit_trail_for_admin_operations(self):
        """Test that audit logs are created for admin operations"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Get initial audit log count
        initial_count = MedicalHistoryAudit.objects.count()
        
        # Admin views a medical record
        medical_record_url = reverse('medicalrecord-detail', args=[self.medical_record.id])
        response = self.client.get(medical_record_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify audit log was created
        self.assertEqual(MedicalHistoryAudit.objects.count(), initial_count + 1)
        log = MedicalHistoryAudit.objects.latest('timestamp')
        self.assertEqual(log.user, self.admin_user)
        self.assertEqual(log.action, "Viewed")
        self.assertEqual(log.model_name, "MedicalRecord")
        
        # Admin adds an allergy
        allergies_url = reverse('allergy-list')
        allergy_data = {
            'medical_record': self.medical_record.id,
            'allergen': 'Sulfa',
            'reaction': 'Hives',
            'severity': 'Mild',
            'diagnosed_date': timezone.now().date().isoformat()
        }
        
        response = self.client.post(allergies_url, allergy_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify audit log was created for admin adding allergy
        self.assertEqual(MedicalHistoryAudit.objects.count(), initial_count + 2)
        log = MedicalHistoryAudit.objects.latest('timestamp')
        self.assertEqual(log.user, self.admin_user)
        self.assertEqual(log.action, "Created")
        self.assertEqual(log.model_name, "Allergy")
    
    def test_audit_trail_accuracy(self):
        """Test that audit trails accurately reflect actual operations"""
        self.client.force_authenticate(user=self.provider)
        
        # Add multiple allergies
        allergies_url = reverse('allergy-list')
        allergens = ['Penicillin', 'Aspirin', 'Latex']
        
        for allergen in allergens:
            allergy_data = {
                'medical_record': self.medical_record.id,
                'allergen': allergen,
                'reaction': 'Various',
                'severity': 'Moderate'
            }
            response = self.client.post(allergies_url, allergy_data, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify audit logs match the allergies created
        create_logs = MedicalHistoryAudit.objects.filter(
            action="Created",
            model_name="Allergy",
            user=self.provider
        )
        
        self.assertEqual(create_logs.count(), 3)
        
        # Get all allergies to compare with audit logs
        allergies = Allergy.objects.filter(medical_record=self.medical_record)
        
        # Each allergy should have a corresponding audit log
        for allergy in allergies:
            log_exists = create_logs.filter(record_id=allergy.id).exists()
            self.assertTrue(log_exists, f"No audit log found for allergen {allergy.allergen}")
        
        # Now delete all allergies
        for allergy in allergies:
            allergy_url = reverse('allergy-detail', args=[allergy.id])
            response = self.client.delete(allergy_url)
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify delete logs match the allergies deleted
        delete_logs = MedicalHistoryAudit.objects.filter(
            action="Deleted",
            model_name="Allergy",
            user=self.provider
        )
        
        self.assertEqual(delete_logs.count(), 3)
