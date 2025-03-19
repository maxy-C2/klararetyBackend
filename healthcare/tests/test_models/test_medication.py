# healthcare/tests/test_models/test_medication.py
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from healthcare.models import MedicalRecord, Medication

User = get_user_model()

class MedicationModelTest(TestCase):
    """Test suite for the Medication model"""
    
    def setUp(self):
        """Set up test data"""
        # Create test users
        self.patient = User.objects.create_user(
            username='testpatient',
            email='patient@example.com',
            password='testpass123',
            role='patient',
            first_name='Test',
            last_name='Patient'
        )
        
        self.provider = User.objects.create_user(
            username='testprovider',
            email='provider@example.com',
            password='testpass123',
            role='provider',
            first_name='Test',
            last_name='Provider'
        )
        
        # Create medical record
        self.medical_record = MedicalRecord.objects.create(
            patient=self.patient,
            medical_record_number='AB12345678',
            date_of_birth=timezone.now().date() - timezone.timedelta(days=365*30),
            gender='Male',
            primary_physician=self.provider
        )
        
        # Create medications
        self.medication_active = Medication.objects.create(
            medical_record=self.medical_record,
            name='Active Medication',
            dosage='10mg',
            frequency='daily',
            start_date=timezone.now().date() - timezone.timedelta(days=30),
            active=True,
            prescribed_by=self.provider,
            reason='For testing'
        )
        
        self.medication_inactive = Medication.objects.create(
            medical_record=self.medical_record,
            name='Inactive Medication',
            dosage='20mg',
            frequency='twice daily',
            start_date=timezone.now().date() - timezone.timedelta(days=60),
            end_date=timezone.now().date() - timezone.timedelta(days=30),
            active=False,
            prescribed_by=self.provider,
            reason='For testing inactive state'
        )
    
    def test_medication_creation(self):
        """Test that medications were created correctly"""
        self.assertEqual(self.medication_active.medical_record, self.medical_record)
        self.assertEqual(self.medication_active.name, 'Active Medication')
        self.assertEqual(self.medication_active.dosage, '10mg')
        self.assertEqual(self.medication_active.frequency, 'daily')
        self.assertTrue(self.medication_active.active)
        self.assertEqual(self.medication_active.prescribed_by, self.provider)
        self.assertEqual(self.medication_active.reason, 'For testing')
        
        self.assertEqual(self.medication_inactive.name, 'Inactive Medication')
        self.assertFalse(self.medication_inactive.active)
        self.assertIsNotNone(self.medication_inactive.end_date)
    
    def test_string_representation(self):
        """Test the string representation of medications"""
        expected_active = "Active Medication - Test Patient"
        expected_inactive = "Inactive Medication - Test Patient"
        
        self.assertEqual(str(self.medication_active), expected_active)
        self.assertEqual(str(self.medication_inactive), expected_inactive)
    
    def test_medication_status(self):
        """Test that medication status (active/inactive) works correctly"""
        # Get active medications
        active_meds = Medication.objects.filter(active=True)
        inactive_meds = Medication.objects.filter(active=False)
        
        self.assertEqual(active_meds.count(), 1)
        self.assertEqual(inactive_meds.count(), 1)
        self.assertIn(self.medication_active, active_meds)
        self.assertIn(self.medication_inactive, inactive_meds)
