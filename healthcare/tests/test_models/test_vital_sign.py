# healthcare/tests/test_models/test_vital_sign.py
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from healthcare.models import MedicalRecord, VitalSign

User = get_user_model()

class VitalSignModelTest(TestCase):
    """Test suite for the VitalSign model"""
    
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
        
        # Create vital signs at different times
        self.recent_vitals = VitalSign.objects.create(
            medical_record=self.medical_record,
            date_recorded=timezone.now() - timezone.timedelta(hours=2),
            temperature=37.0,
            heart_rate=72,
            blood_pressure_systolic=120,
            blood_pressure_diastolic=80,
            respiratory_rate=16,
            oxygen_saturation=98,
            recorded_by=self.provider
        )
        
        self.older_vitals = VitalSign.objects.create(
            medical_record=self.medical_record,
            date_recorded=timezone.now() - timezone.timedelta(days=2),
            temperature=37.2,
            heart_rate=75,
            blood_pressure_systolic=125,
            blood_pressure_diastolic=85,
            respiratory_rate=18,
            oxygen_saturation=97,
            recorded_by=self.provider
        )
        
        self.oldest_vitals = VitalSign.objects.create(
            medical_record=self.medical_record,
            date_recorded=timezone.now() - timezone.timedelta(days=30),
            temperature=37.5,
            heart_rate=80,
            blood_pressure_systolic=130,
            blood_pressure_diastolic=90,
            respiratory_rate=20,
            oxygen_saturation=96,
            recorded_by=self.provider
        )
    
    def test_vital_sign_creation(self):
        """Test that vital signs were created correctly"""
        self.assertEqual(self.recent_vitals.medical_record, self.medical_record)
        self.assertEqual(self.recent_vitals.temperature, 37.0)
        self.assertEqual(self.recent_vitals.heart_rate, 72)
        self.assertEqual(self.recent_vitals.blood_pressure_systolic, 120)
        self.assertEqual(self.recent_vitals.blood_pressure_diastolic, 80)
        self.assertEqual(self.recent_vitals.respiratory_rate, 16)
        self.assertEqual(self.recent_vitals.oxygen_saturation, 98)
        self.assertEqual(self.recent_vitals.recorded_by, self.provider)
    
    def test_string_representation(self):
        """Test the string representation of vital signs"""
        expected = f"Vitals for Test Patient ({self.recent_vitals.date_recorded})"
        self.assertEqual(str(self.recent_vitals), expected)
    
    def test_get_latest_vitals(self):
        """Test retrieving the most recent vital signs"""
        latest_vitals = self.medical_record.get_latest_vitals()
        self.assertEqual(latest_vitals, self.recent_vitals)
        
        # Verify it's not returning the older readings
        self.assertNotEqual(latest_vitals, self.older_vitals)
        self.assertNotEqual(latest_vitals, self.oldest_vitals)
    
    def test_vital_sign_ordering(self):
        """Test that vital signs are ordered by date correctly"""
        all_vitals = VitalSign.objects.filter(medical_record=self.medical_record).order_by('-date_recorded')
        
        self.assertEqual(all_vitals.count(), 3)
        self.assertEqual(all_vitals[0], self.recent_vitals)
        self.assertEqual(all_vitals[1], self.older_vitals)
        self.assertEqual(all_vitals[2], self.oldest_vitals)
    
    def test_vital_sign_with_missing_fields(self):
        """Test vital sign with some fields missing"""
        # Create a vital sign with only some fields populated
        partial_vitals = VitalSign.objects.create(
            medical_record=self.medical_record,
            date_recorded=timezone.now(),
            temperature=36.8,
            heart_rate=70,
            # Omitting blood pressure, respiratory rate, and oxygen saturation
            recorded_by=self.provider
        )
        
        self.assertEqual(partial_vitals.temperature, 36.8)
        self.assertEqual(partial_vitals.heart_rate, 70)
        self.assertIsNone(partial_vitals.blood_pressure_systolic)
        self.assertIsNone(partial_vitals.blood_pressure_diastolic)
        self.assertIsNone(partial_vitals.respiratory_rate)
        self.assertIsNone(partial_vitals.oxygen_saturation)
        
        # Should still be retrievable as the latest vitals
        latest_vitals = self.medical_record.get_latest_vitals()
        self.assertEqual(latest_vitals, partial_vitals)
