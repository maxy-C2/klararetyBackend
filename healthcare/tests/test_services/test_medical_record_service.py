# healthcare/tests/test_services/test_medical_record_service.py
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from healthcare.models import MedicalRecord, Allergy, Medication, Condition, VitalSign
from healthcare.services.medical_record_service import MedicalRecordService
import re

User = get_user_model()

class MedicalRecordServiceTest(TestCase):
    """Test suite for the MedicalRecordService"""
    
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
        
        # Create a medical record manually to test against service-created ones
        self.existing_record = MedicalRecord.objects.create(
            patient=self.patient,
            medical_record_number='AB12345678',
            date_of_birth=timezone.now().date() - timezone.timedelta(days=365*30),
            gender='Male',
            primary_physician=self.provider
        )
        
        # Add data to the medical record
        Allergy.objects.create(
            medical_record=self.existing_record,
            allergen='Penicillin',
            reaction='Rash',
            severity='Moderate',
            diagnosed_date=timezone.now().date() - timezone.timedelta(days=365)
        )
        
        Medication.objects.create(
            medical_record=self.existing_record,
            name='Test Medication',
            dosage='10mg',
            frequency='daily',
            start_date=timezone.now().date() - timezone.timedelta(days=30),
            active=True,
            prescribed_by=self.provider
        )
        
        Condition.objects.create(
            medical_record=self.existing_record,
            name='Test Condition',
            diagnosis_date=timezone.now().date() - timezone.timedelta(days=90),
            active=True,
            diagnosed_by=self.provider
        )
        
        VitalSign.objects.create(
            medical_record=self.existing_record,
            date_recorded=timezone.now() - timezone.timedelta(hours=5),
            temperature=37.0,
            heart_rate=72,
            blood_pressure_systolic=120,
            blood_pressure_diastolic=80,
            respiratory_rate=16,
            oxygen_saturation=98,
            recorded_by=self.provider
        )
    
    def test_generate_mrn(self):
        """Test generation of a unique Medical Record Number"""
        mrn = MedicalRecordService.generate_mrn()
        
        # Check format of MRN (2 uppercase letters followed by 8 digits)
        pattern = r'^[A-Z]{2}\d{8}$'
        self.assertTrue(re.match(pattern, mrn))
        
        # Check uniqueness by generating multiple MRNs
        mrns = set()
        for _ in range(10):
            mrns.add(MedicalRecordService.generate_mrn())
        
        # All MRNs should be unique
        self.assertEqual(len(mrns), 10)
    
    def test_create_medical_record(self):
        """Test creating a new medical record"""
        # Create a new patient
        new_patient = User.objects.create_user(
            username='newpatient',
            email='new@example.com',
            password='testpass123',
            role='patient',
            first_name='New',
            last_name='Patient'
        )
        
        # Create a medical record with the service
        record = MedicalRecordService.create_medical_record(
            patient=new_patient,
            date_of_birth=timezone.now().date() - timezone.timedelta(days=365*25),
            gender='Female',
            primary_physician=self.provider
        )
        
        # Verify the record was created
        self.assertIsNotNone(record)
        self.assertEqual(record.patient, new_patient)
        self.assertEqual(record.gender, 'Female')
        self.assertEqual(record.primary_physician, self.provider)
        
        # Verify MRN format
        pattern = r'^[A-Z]{2}\d{8}$'
        self.assertTrue(re.match(pattern, record.medical_record_number))
    
    def test_transfer_primary_physician(self):
        """Test transferring a patient to a new primary physician"""
        # Create a new provider
        new_provider = User.objects.create_user(
            username='newprovider',
            email='newdoc@example.com',
            password='testpass123',
            role='provider',
            first_name='New',
            last_name='Provider'
        )
        
        # Transfer the patient to the new provider
        updated_record = MedicalRecordService.transfer_primary_physician(
            self.existing_record, new_provider
        )
        
        # Verify the transfer
        self.assertEqual(updated_record.primary_physician, new_provider)
        
        # Refresh from database and verify again
        self.existing_record.refresh_from_db()
        self.assertEqual(self.existing_record.primary_physician, new_provider)
    
    def test_get_patient_summary(self):
        """Test retrieving a patient summary"""
        summary = MedicalRecordService.get_patient_summary(self.existing_record.id)
        
        # Verify the summary structure and content
        self.assertIsNotNone(summary)
        self.assertEqual(summary['patient'], 'Test Patient')
        self.assertEqual(summary['medical_record_number'], 'AB12345678')
        self.assertEqual(summary['gender'], 'Male')
        
        # Check that related data is included
        self.assertEqual(len(summary['allergies']), 1)
        self.assertEqual(summary['allergies'][0]['allergen'], 'Penicillin')
        
        self.assertEqual(len(summary['current_medications']), 1)
        self.assertEqual(summary['current_medications'][0]['name'], 'Test Medication')
        
        self.assertEqual(len(summary['current_conditions']), 1)
        self.assertEqual(summary['current_conditions'][0]['name'], 'Test Condition')
        
        self.assertIsNotNone(summary['recent_vitals'])
        self.assertEqual(summary['recent_vitals']['temperature'], '37.0')
