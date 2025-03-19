# healthcare/tests/test_models/test_condition.py
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from healthcare.models import MedicalRecord, Condition

User = get_user_model()

class ConditionModelTest(TestCase):
    """Test suite for the Condition model"""
    
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
        
        # Create conditions
        self.active_condition = Condition.objects.create(
            medical_record=self.medical_record,
            name='Active Condition',
            icd10_code='J45.909',
            diagnosis_date=timezone.now().date() - timezone.timedelta(days=90),
            active=True,
            diagnosed_by=self.provider,
            notes='Test active condition'
        )
        
        self.resolved_condition = Condition.objects.create(
            medical_record=self.medical_record,
            name='Resolved Condition',
            icd10_code='J00',
            diagnosis_date=timezone.now().date() - timezone.timedelta(days=120),
            resolved_date=timezone.now().date() - timezone.timedelta(days=90),
            active=False,
            diagnosed_by=self.provider,
            notes='Test resolved condition'
        )
    
    def test_condition_creation(self):
        """Test that conditions were created correctly"""
        self.assertEqual(self.active_condition.medical_record, self.medical_record)
        self.assertEqual(self.active_condition.name, 'Active Condition')
        self.assertEqual(self.active_condition.icd10_code, 'J45.909')
        self.assertTrue(self.active_condition.active)
        self.assertIsNone(self.active_condition.resolved_date)
        
        self.assertEqual(self.resolved_condition.name, 'Resolved Condition')
        self.assertEqual(self.resolved_condition.icd10_code, 'J00')
        self.assertFalse(self.resolved_condition.active)
        self.assertIsNotNone(self.resolved_condition.resolved_date)
    
    def test_string_representation(self):
        """Test the string representation of conditions"""
        expected_active = "Active Condition - Test Patient"
        expected_resolved = "Resolved Condition - Test Patient"
        
        self.assertEqual(str(self.active_condition), expected_active)
        self.assertEqual(str(self.resolved_condition), expected_resolved)
    
    def test_condition_status(self):
        """Test the active/inactive status filtering"""
        # Get active conditions
        active_conditions = Condition.objects.filter(active=True)
        resolved_conditions = Condition.objects.filter(active=False)
        
        self.assertEqual(active_conditions.count(), 1)
        self.assertEqual(resolved_conditions.count(), 1)
        
        self.assertIn(self.active_condition, active_conditions)
        self.assertIn(self.resolved_condition, resolved_conditions)
        
        # Test the helper method in MedicalRecord
        active_from_record = self.medical_record.get_active_conditions()
        self.assertEqual(active_from_record.count(), 1)
        self.assertEqual(active_from_record.first(), self.active_condition)
    
    def test_condition_with_provider(self):
        """Test the provider relationship"""
        self.assertEqual(self.active_condition.diagnosed_by, self.provider)
        
        # Verify reverse relationship
        provider_diagnoses = self.provider.diagnoses.all()
        self.assertEqual(provider_diagnoses.count(), 2)
        self.assertIn(self.active_condition, provider_diagnoses)
        self.assertIn(self.resolved_condition, provider_diagnoses)
