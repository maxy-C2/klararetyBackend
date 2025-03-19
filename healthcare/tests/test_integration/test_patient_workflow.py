# healthcare/tests/test_integration/test_patient_workflow.py
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from healthcare.models import (
    MedicalRecord, Allergy, Medication, Condition, VitalSign, LabTest, LabResult, MedicalNote
)
import json

User = get_user_model()

class PatientWorkflowIntegrationTest(TestCase):
    """
    Integration test for a complete patient workflow scenario.
    Tests the interaction between different parts of the healthcare system
    for a typical patient journey.
    """
    
    def setUp(self):
        """Set up test data and API client"""
        # Create test users with different roles
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
        
        # Setup API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.provider)
    
    def test_complete_patient_workflow(self):
        """Test a complete patient workflow from registration to treatment"""
        
        # 1. Verify a medical record was created for the patient (via signal)
        medical_records = MedicalRecord.objects.filter(patient=self.patient)
        self.assertEqual(medical_records.count(), 1)
        
        medical_record = medical_records.first()
        medical_record_id = medical_record.id
        
        # 2. Update the medical record with additional information
        medical_record_detail_url = reverse('medicalrecord-detail', args=[medical_record_id])
        update_data = {
            'blood_type': 'O+',
            'height': 180.0,
            'weight': 75.0
        }
        
        response = self.client.patch(medical_record_detail_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 3. Add allergies for the patient
        allergies_url = reverse('allergy-list')
        allergy_data = {
            'medical_record': medical_record_id,
            'allergen': 'Penicillin',
            'reaction': 'Skin rash, difficulty breathing',
            'severity': 'Severe',
            'diagnosed_date': timezone.now().date().isoformat()
        }
        
        response = self.client.post(allergies_url, allergy_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 4. Record vital signs
        vitals_url = reverse('vitalsign-list')
        vitals_data = {
            'medical_record': medical_record_id,
            'date_recorded': timezone.now().isoformat(),
            'temperature': 37.2,
            'heart_rate': 75,
            'blood_pressure_systolic': 120,
            'blood_pressure_diastolic': 80,
            'respiratory_rate': 18,
            'oxygen_saturation': 98
        }
        
        response = self.client.post(vitals_url, vitals_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 5. Diagnose a condition
        conditions_url = reverse('condition-list')
        condition_data = {
            'medical_record': medical_record_id,
            'name': 'Hypertension',
            'icd10_code': 'I10',
            'diagnosis_date': timezone.now().date().isoformat(),
            'active': True,
            'diagnosed_by': self.provider.id,
            'notes': 'Patient has elevated blood pressure, recommend lifestyle modifications'
        }
        
        response = self.client.post(conditions_url, condition_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        condition_id = response.data['id']
        
        # 6. Order lab tests
        lab_tests_url = reverse('labtest-list')
        lab_test_data = {
            'medical_record': medical_record_id,
            'name': 'Comprehensive Metabolic Panel',
            'test_date': timezone.now().date().isoformat(),
            'ordered_by': self.provider.id
        }
        
        response = self.client.post(lab_tests_url, lab_test_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        lab_test_id = response.data['id']
        
        # 7. Add lab results
        lab_results_url = reverse('labresult-list')
        lab_results = [
            {
                'lab_test': lab_test_id,
                'test_component': 'Glucose',
                'value': '95',
                'unit': 'mg/dL',
                'reference_range': '70-99',
                'is_abnormal': False
            },
            {
                'lab_test': lab_test_id,
                'test_component': 'Potassium',
                'value': '4.2',
                'unit': 'mmol/L',
                'reference_range': '3.5-5.0',
                'is_abnormal': False
            },
            {
                'lab_test': lab_test_id,
                'test_component': 'Creatinine',
                'value': '1.3',
                'unit': 'mg/dL',
                'reference_range': '0.7-1.2',
                'is_abnormal': True,
                'notes': 'Slightly elevated, monitor'
            }
        ]
        
        for result_data in lab_results:
            response = self.client.post(lab_results_url, result_data, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Update lab test to indicate results are available
        lab_test_detail_url = reverse('labtest-detail', args=[lab_test_id])
        lab_test_update = {
            'results_available': True,
            'results_date': timezone.now().date().isoformat()
        }
        response = self.client.patch(lab_test_detail_url, lab_test_update, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 8. Prescribe medication
        medications_url = reverse('medication-list')
        medication_data = {
            'medical_record': medical_record_id,
            'name': 'Lisinopril',
            'dosage': '10mg',
            'frequency': 'Once daily',
            'start_date': timezone.now().date().isoformat(),
            'prescribed_by': self.provider.id,
            'active': True,
            'reason': 'For blood pressure management'
        }
        
        response = self.client.post(medications_url, medication_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        medication_id = response.data['id']
        
        # 9. Create a SOAP note for the visit
        notes_url = reverse('medicalnote-list')
        note_data = {
            'medical_record': medical_record_id,
            'note_type': 'soap',
            'provider': self.provider.id,
            'subjective': 'Patient reports occasional headaches and dizziness in the morning.',
            'objective': 'BP: 120/80, HR: 75, Temp: 37.2C, O2: 98%. Physical exam is normal.',
            'assessment': 'Hypertension, well-controlled on current medication.',
            'plan': 'Continue Lisinopril 10mg daily. Follow up in 3 months. Lifestyle modifications discussed.'
        }
        
        response = self.client.post(notes_url, note_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 10. Get patient summary to verify all data
        summary_url = reverse('medicalrecord-summary', args=[medical_record_id])
        response = self.client.get(summary_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        summary = response.data
        self.assertEqual(summary['patient'], 'Test Patient')
        self.assertEqual(len(summary['allergies']), 1)
        self.assertEqual(summary['allergies'][0]['allergen'], 'Penicillin')
        self.assertEqual(len(summary['current_conditions']), 1)
        self.assertEqual(summary['current_conditions'][0]['name'], 'Hypertension')
        self.assertEqual(len(summary['current_medications']), 1)
        self.assertEqual(summary['current_medications'][0]['name'], 'Lisinopril')
        
        # Verify lab test results
        self.assertEqual(len(summary['recent_labs']), 1)
        lab_test = summary['recent_labs'][0]
        self.assertEqual(lab_test['name'], 'Comprehensive Metabolic Panel')
        self.assertEqual(len(lab_test['results']), 3)  # Should have 3 results
        
        # Verify vital signs
        self.assertIsNotNone(summary['recent_vitals'])
        vitals = summary['recent_vitals']
        self.assertEqual(float(vitals['temperature']), 37.2)
        self.assertEqual(int(vitals['heart_rate']), 75)
        
        # 11. Test from patient's perspective - switch to patient user
        self.client.force_authenticate(user=self.patient)
        
        # Patient should be able to view their medical record
        response = self.client.get(medical_record_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Patient should see their allergies
        response = self.client.get(allergies_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        
        # Patient should see their medications
        response = self.client.get(medications_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        
        # But patient should not be able to add/modify medications
        new_med_data = {
            'medical_record': medical_record_id,
            'name': 'Self-prescribed',
            'dosage': '5mg',
            'frequency': 'As needed',
            'start_date': timezone.now().date().isoformat(),
            'active': True
        }
        response = self.client.post(medications_url, new_med_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Patient should be able to get summary
        response = self.client.get(summary_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
