# healthcare/tests/test_models/test_medical_record.py
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from healthcare.models import MedicalRecord, Medication, Condition, Allergy, VitalSign, LabTest

User = get_user_model()

class MedicalRecordModelTest(TestCase):
    """Test suite for the MedicalRecord model"""
    
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
            date_of_birth=timezone.now().date() - timezone.timedelta(days=365*30),  # 30 years old
            gender='Male',
            primary_physician=self.provider,
            blood_type='O+',
            height=175.5,
            weight=70.5
        )
        
        # Create related records for testing methods
        self.medication1 = Medication.objects.create(
            medical_record=self.medical_record,
            name='Test Medication 1',
            dosage='10mg',
            frequency='daily',
            start_date=timezone.now().date() - timezone.timedelta(days=30),
            active=True,
            prescribed_by=self.provider
        )
        
        self.medication2 = Medication.objects.create(
            medical_record=self.medical_record,
            name='Test Medication 2',
            dosage='20mg',
            frequency='twice daily',
            start_date=timezone.now().date() - timezone.timedelta(days=60),
            end_date=timezone.now().date() - timezone.timedelta(days=30),
            active=False,
            prescribed_by=self.provider
        )
        
        self.condition1 = Condition.objects.create(
            medical_record=self.medical_record,
            name='Test Condition 1',
            diagnosis_date=timezone.now().date() - timezone.timedelta(days=90),
            active=True,
            diagnosed_by=self.provider
        )
        
        self.condition2 = Condition.objects.create(
            medical_record=self.medical_record,
            name='Test Condition 2',
            diagnosis_date=timezone.now().date() - timezone.timedelta(days=120),
            resolved_date=timezone.now().date() - timezone.timedelta(days=60),
            active=False,
            diagnosed_by=self.provider
        )
        
        self.allergy = Allergy.objects.create(
            medical_record=self.medical_record,
            allergen='Test Allergen',
            reaction='Test Reaction',
            severity='Moderate',
            diagnosed_date=timezone.now().date() - timezone.timedelta(days=45)
        )
        
        self.vital_sign = VitalSign.objects.create(
            medical_record=self.medical_record,
            date_recorded=timezone.now() - timezone.timedelta(days=5),
            temperature=37.0,
            heart_rate=72,
            blood_pressure_systolic=120,
            blood_pressure_diastolic=80,
            respiratory_rate=16,
            oxygen_saturation=98,
            recorded_by=self.provider
        )
    
    def test_medical_record_creation(self):
        """Test that the medical record was created correctly"""
        self.assertEqual(self.medical_record.patient, self.patient)
        self.assertEqual(self.medical_record.medical_record_number, 'AB12345678')
        self.assertEqual(self.medical_record.primary_physician, self.provider)
        self.assertEqual(self.medical_record.gender, 'Male')
        self.assertEqual(self.medical_record.blood_type, 'O+')
        self.assertEqual(self.medical_record.height, 175.5)
        self.assertEqual(self.medical_record.weight, 70.5)
    
    def test_string_representation(self):
        """Test the string representation of the medical record"""
        expected_string = f"Medical Record: Test Patient (AB12345678)"
        self.assertEqual(str(self.medical_record), expected_string)
    
    def test_get_active_medications(self):
        """Test retrieving active medications"""
        active_meds = self.medical_record.get_active_medications()
        self.assertEqual(active_meds.count(), 1)
        self.assertEqual(active_meds.first(), self.medication1)
    
    def test_get_active_conditions(self):
        """Test retrieving active conditions"""
        active_conditions = self.medical_record.get_active_conditions()
        self.assertEqual(active_conditions.count(), 1)
        self.assertEqual(active_conditions.first(), self.condition1)
    
    def test_get_allergies(self):
        """Test retrieving allergies"""
        allergies = self.medical_record.get_allergies()
        self.assertEqual(allergies.count(), 1)
        self.assertEqual(allergies.first(), self.allergy)
    
    def test_get_latest_vitals(self):
        """Test retrieving the latest vital signs"""
        latest_vitals = self.medical_record.get_latest_vitals()
        self.assertEqual(latest_vitals, self.vital_sign)
    
    def test_calculate_age(self):
        """Test calculating the patient's age"""
        # Since we set the date of birth to 30 years ago, the age should be 30
        self.assertEqual(self.medical_record.calculate_age(), 30)
