# healthcare/tests/test_models/test_lab_test.py
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from healthcare.models import MedicalRecord, LabTest, LabResult

User = get_user_model()

class LabTestModelTest(TestCase):
    """Test suite for the LabTest and LabResult models"""
    
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
        
        # Create lab tests
        self.lab_test_with_results = LabTest.objects.create(
            medical_record=self.medical_record,
            name='Complete Blood Count',
            test_date=timezone.now().date() - timezone.timedelta(days=10),
            ordered_by=self.provider,
            results_available=True,
            results_date=timezone.now().date() - timezone.timedelta(days=8)
        )
        
        self.lab_test_without_results = LabTest.objects.create(
            medical_record=self.medical_record,
            name='Lipid Panel',
            test_date=timezone.now().date() - timezone.timedelta(days=5),
            ordered_by=self.provider,
            results_available=False
        )
        
        # Create lab results
        self.normal_result = LabResult.objects.create(
            lab_test=self.lab_test_with_results,
            test_component='Hemoglobin',
            value='14.5',
            unit='g/dL',
            reference_range='13.5-17.5',
            is_abnormal=False
        )
        
        self.abnormal_result = LabResult.objects.create(
            lab_test=self.lab_test_with_results,
            test_component='White Blood Cell Count',
            value='11.5',
            unit='K/µL',
            reference_range='4.5-11.0',
            is_abnormal=True,
            notes='Slightly elevated'
        )
    
    def test_lab_test_creation(self):
        """Test that lab tests were created correctly"""
        self.assertEqual(self.lab_test_with_results.medical_record, self.medical_record)
        self.assertEqual(self.lab_test_with_results.name, 'Complete Blood Count')
        self.assertTrue(self.lab_test_with_results.results_available)
        self.assertIsNotNone(self.lab_test_with_results.results_date)
        
        self.assertEqual(self.lab_test_without_results.name, 'Lipid Panel')
        self.assertFalse(self.lab_test_without_results.results_available)
        self.assertIsNone(self.lab_test_without_results.results_date)
    
    def test_lab_result_creation(self):
        """Test that lab results were created correctly"""
        self.assertEqual(self.normal_result.lab_test, self.lab_test_with_results)
        self.assertEqual(self.normal_result.test_component, 'Hemoglobin')
        self.assertEqual(self.normal_result.value, '14.5')
        self.assertEqual(self.normal_result.unit, 'g/dL')
        self.assertFalse(self.normal_result.is_abnormal)
        
        self.assertEqual(self.abnormal_result.test_component, 'White Blood Cell Count')
        self.assertTrue(self.abnormal_result.is_abnormal)
        self.assertEqual(self.abnormal_result.notes, 'Slightly elevated')
    
    def test_string_representation(self):
        """Test the string representation of lab tests and results"""
        expected_lab_test = f"Complete Blood Count - Test Patient ({self.lab_test_with_results.test_date})"
        expected_normal_result = "Hemoglobin: 14.5 g/dL"
        expected_abnormal_result = "White Blood Cell Count: 11.5 K/µL"
        
        self.assertEqual(str(self.lab_test_with_results), expected_lab_test)
        self.assertEqual(str(self.normal_result), expected_normal_result)
        self.assertEqual(str(self.abnormal_result), expected_abnormal_result)
    
    def test_get_abnormal_results(self):
        """Test retrieving abnormal results"""
        abnormal_results = self.lab_test_with_results.get_abnormal_results()
        self.assertEqual(abnormal_results.count(), 1)
        self.assertEqual(abnormal_results.first(), self.abnormal_result)
