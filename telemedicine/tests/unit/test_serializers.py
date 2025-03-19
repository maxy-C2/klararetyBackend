# telemedicine/tests/test_serializers.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIRequestFactory
from datetime import timedelta, time
import json

from telemedicine.models import (
    Appointment, Consultation, Prescription, 
    Message, MedicalDocument, ProviderAvailability, ProviderTimeOff
)
from telemedicine.serializers import (
    AppointmentSerializer, ConsultationSerializer, PrescriptionSerializer,
    MessageSerializer, MedicalDocumentSerializer, 
    ProviderAvailabilitySerializer, ProviderTimeOffSerializer
)

User = get_user_model()

class AppointmentSerializerTests(TestCase):
    def setUp(self):
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
        
        # Create a test appointment
        self.now = timezone.now()
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            provider=self.provider,
            scheduled_time=self.now + timedelta(days=1),
            end_time=self.now + timedelta(days=1, hours=1),
            reason='Annual checkup',
            appointment_type='video_consultation'
        )
        
        # Create request factory for context
        self.factory = APIRequestFactory()
        self.request = self.factory.get('/')
    
    def test_appointment_serialization(self):
        """Test that appointment serialization includes all fields"""
        serializer = AppointmentSerializer(self.appointment)
        data = serializer.data
        
        # Verify primary fields
        self.assertEqual(data['id'], self.appointment.id)
        self.assertEqual(data['patient'], self.patient.id)
        self.assertEqual(data['provider'], self.provider.id)
        self.assertEqual(data['status'], 'scheduled')
        self.assertEqual(data['reason'], 'Annual checkup')
        self.assertEqual(data['appointment_type'], 'video_consultation')
        
        # Verify nested fields are present
        self.assertIn('patient_details', data)
        self.assertIn('provider_details', data)
        
        # Verify nested user details
        self.assertEqual(data['patient_details']['username'], 'testpatient')
        self.assertEqual(data['patient_details']['first_name'], 'Test')
        self.assertEqual(data['patient_details']['last_name'], 'Patient')
        self.assertEqual(data['provider_details']['username'], 'testprovider')
        self.assertEqual(data['provider_details']['first_name'], 'Test')
        self.assertEqual(data['provider_details']['last_name'], 'Provider')
    
    def test_appointment_deserialization_valid_data(self):
        """Test that appointment can be deserialized with valid data"""
        # Sample data for creating an appointment
        scheduled_time = self.now + timedelta(days=2)
        end_time = scheduled_time + timedelta(hours=1)
        
        data = {
            'patient': self.patient.id,
            'provider': self.provider.id,
            'scheduled_time': scheduled_time.isoformat(),
            'end_time': end_time.isoformat(),
            'reason': 'Follow-up appointment',
            'appointment_type': 'in_person'
        }
        
        serializer = AppointmentSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        # Save the deserialized data
        appointment = serializer.save()
        
        # Verify fields were set correctly
        self.assertEqual(appointment.patient, self.patient)
        self.assertEqual(appointment.provider, self.provider)
        self.assertEqual(appointment.reason, 'Follow-up appointment')
        self.assertEqual(appointment.appointment_type, 'in_person')
        self.assertEqual(appointment.status, 'scheduled')  # Default value
    
    def test_appointment_deserialization_invalid_data(self):
        """Test serializer validation with invalid data"""
        # Missing required fields
        data = {
            'patient': self.patient.id,
            'provider': self.provider.id,
            # Missing scheduled_time
            'end_time': (self.now + timedelta(days=2, hours=1)).isoformat(),
            'reason': 'Invalid appointment'
        }
        
        serializer = AppointmentSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('scheduled_time', serializer.errors)
        
        # End time before start time
        data = {
            'patient': self.patient.id,
            'provider': self.provider.id,
            'scheduled_time': (self.now + timedelta(days=2)).isoformat(),
            'end_time': (self.now + timedelta(days=1)).isoformat(),  # Before start time
            'reason': 'Invalid appointment'
        }
        
        serializer = AppointmentSerializer(data=data)
        self.assertFalse(serializer.is_valid())
    
    def test_appointment_update(self):
        """Test updating an appointment with serializer"""
        data = {
            'reason': 'Updated reason',
            'status': 'confirmed'
        }
        
        serializer = AppointmentSerializer(self.appointment, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        # Save the updates
        updated_appointment = serializer.save()
        
        # Verify only specified fields were updated
        self.assertEqual(updated_appointment.reason, 'Updated reason')
        self.assertEqual(updated_appointment.status, 'confirmed')
        self.assertEqual(updated_appointment.patient, self.patient)  # Unchanged
        self.assertEqual(updated_appointment.provider, self.provider)  # Unchanged
        self.assertEqual(updated_appointment.appointment_type, 'video_consultation')  # Unchanged


class ConsultationSerializerTests(TestCase):
    def setUp(self):
        # Create test users
        self.patient = User.objects.create_user(
            username='testpatient',
            email='patient@example.com',
            password='testpass123',
            role='patient'
        )
        self.provider = User.objects.create_user(
            username='testprovider',
            email='provider@example.com',
            password='testpass123',
            role='provider'
        )
        
        # Create a test appointment
        self.now = timezone.now()
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            provider=self.provider,
            scheduled_time=self.now + timedelta(days=1),
            end_time=self.now + timedelta(days=1, hours=1),
            reason='Annual checkup',
            appointment_type='video_consultation'
        )
        
        # Create a test consultation
        self.consultation = Consultation.objects.create(
            appointment=self.appointment,
            notes='Patient appears healthy',
            zoom_meeting_id='123456789',
            zoom_meeting_password='password123',
            zoom_join_url='https://zoom.us/j/123456789',
            zoom_start_url='https://zoom.us/s/123456789'
        )
        
        # Create request factory for context
        self.factory = APIRequestFactory()
        self.request = self.factory.get('/')
        self.request.user = self.provider
    
    def test_consultation_serialization_for_provider(self):
        """Test that consultation serialization includes all fields for provider"""
        serializer = ConsultationSerializer(
            self.consultation, 
            context={'request': self.request}
        )
        data = serializer.data
        
        # Verify primary fields
        self.assertEqual(data['id'], self.consultation.id)
        self.assertEqual(data['appointment'], self.appointment.id)
        self.assertEqual(data['notes'], 'Patient appears healthy')
        
        # Verify Zoom info is included but limited for security
        self.assertIn('zoom_join_info', data)
        zoom_info = data['zoom_join_info']
        self.assertEqual(zoom_info['meeting_id'], '123456789')
        self.assertEqual(zoom_info['password'], 'password123')
        self.assertEqual(zoom_info['join_url'], 'https://zoom.us/j/123456789')
        # start_url should not be included in the regular serializer
        self.assertNotIn('start_url', zoom_info)
    
    def test_consultation_serialization_for_patient(self):
        """Test that consultation serialization is appropriate for patient"""
        # Set request user to patient
        self.request.user = self.patient
        
        serializer = ConsultationSerializer(
            self.consultation, 
            context={'request': self.request}
        )
        data = serializer.data
        
        # Verify Zoom info is included but limited
        self.assertIn('zoom_join_info', data)
        zoom_info = data['zoom_join_info']
        self.assertEqual(zoom_info['meeting_id'], '123456789')
        self.assertEqual(zoom_info['password'], 'password123')
        self.assertEqual(zoom_info['join_url'], 'https://zoom.us/j/123456789')
        self.assertNotIn('start_url', zoom_info)
    
    def test_consultation_serialization_without_zoom_data(self):
        """Test serialization of consultation without Zoom data"""
        # Create consultation without Zoom data
        consultation_no_zoom = Consultation.objects.create(
            appointment=self.appointment,
            notes='In-person consultation'
        )
        
        serializer = ConsultationSerializer(
            consultation_no_zoom, 
            context={'request': self.request}
        )
        data = serializer.data
        
        # Verify zoom_join_info is None
        self.assertIsNone(data['zoom_join_info'])
    
    def test_consultation_deserialization_valid_data(self):
        """Test that consultation can be deserialized with valid data"""
        # Create another appointment for this test
        another_appointment = Appointment.objects.create(
            patient=self.patient,
            provider=self.provider,
            scheduled_time=self.now + timedelta(days=3),
            end_time=self.now + timedelta(days=3, hours=1),
            reason='Another checkup',
            appointment_type='video_consultation'
        )
        
        data = {
            'appointment': another_appointment.id,
            'notes': 'New consultation notes'
        }
        
        serializer = ConsultationSerializer(
            data=data,
            context={'request': self.request}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        # Save the deserialized data
        consultation = serializer.save()
        
        # Verify fields were set correctly
        self.assertEqual(consultation.appointment, another_appointment)
        self.assertEqual(consultation.notes, 'New consultation notes')
    
    def test_consultation_deserialization_invalid_data(self):
        """Test serializer validation with invalid data"""
        # Missing required appointment field
        data = {
            'notes': 'Invalid consultation'
        }
        
        serializer = ConsultationSerializer(
            data=data,
            context={'request': self.request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('appointment', serializer.errors)
        
        # Non-existent appointment ID
        data = {
            'appointment': 9999,  # Non-existent ID
            'notes': 'Invalid consultation'
        }
        
        serializer = ConsultationSerializer(
            data=data,
            context={'request': self.request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('appointment', serializer.errors)
    
    def test_consultation_update(self):
        """Test updating a consultation with serializer"""
        # Set start and end times
        start_time = self.now
        end_time = start_time + timedelta(hours=1)
        
        data = {
            'notes': 'Updated consultation notes',
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }
        
        serializer = ConsultationSerializer(
            self.consultation, 
            data=data, 
            partial=True,
            context={'request': self.request}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        # Save the updates
        updated_consultation = serializer.save()
        
        # Verify fields were updated correctly
        self.assertEqual(updated_consultation.notes, 'Updated consultation notes')
        self.assertIsNotNone(updated_consultation.start_time)
        self.assertIsNotNone(updated_consultation.end_time)
        self.assertIsNotNone(updated_consultation.duration)  # Should be calculated automatically
        self.assertEqual(updated_consultation.duration, timedelta(hours=1))


class PrescriptionSerializerTests(TestCase):
    def setUp(self):
        # Create test users
        self.patient = User.objects.create_user(
            username='testpatient',
            email='patient@example.com',
            password='testpass123',
            role='patient'
        )
        self.provider = User.objects.create_user(
            username='testprovider',
            email='provider@example.com',
            password='testpass123',
            role='provider'
        )
        self.pharmco = User.objects.create_user(
            username='testpharmco',
            email='pharmacy@example.com',
            password='testpass123',
            role='pharmco'
        )
        
        # Create a test appointment and consultation
        self.now = timezone.now()
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            provider=self.provider,
            scheduled_time=self.now,
            end_time=self.now + timedelta(hours=1),
            reason='Treatment',
            appointment_type='video_consultation'
        )
        
        self.consultation = Consultation.objects.create(
            appointment=self.appointment,
            start_time=self.now,
            end_time=self.now + timedelta(hours=1),
            notes='Patient has a sinus infection'
        )
        
        # Create a test prescription
        self.prescription = Prescription.objects.create(
            consultation=self.consultation,
            medication_name='Amoxicillin',
            dosage='500mg',
            frequency='3 times daily',
            duration='10 days',
            refills=1,
            notes='Take with food',
            pharmacy=self.pharmco
        )
    
    def test_prescription_serialization(self):
        """Test that prescription serialization includes all fields"""
        serializer = PrescriptionSerializer(self.prescription)
        data = serializer.data
        
        # Verify all fields are included
        self.assertEqual(data['id'], self.prescription.id)
        self.assertEqual(data['consultation'], self.consultation.id)
        self.assertEqual(data['medication_name'], 'Amoxicillin')
        self.assertEqual(data['dosage'], '500mg')
        self.assertEqual(data['frequency'], '3 times daily')
        self.assertEqual(data['duration'], '10 days')
        self.assertEqual(data['refills'], 1)
        self.assertEqual(data['notes'], 'Take with food')
        self.assertEqual(data['pharmacy'], self.pharmco.id)
        self.assertIn('created_at', data)
    
    def test_prescription_deserialization_valid_data(self):
        """Test that prescription can be deserialized with valid data"""
        data = {
            'consultation': self.consultation.id,
            'medication_name': 'Ibuprofen',
            'dosage': '200mg',
            'frequency': '4 times daily',
            'duration': '5 days',
            'refills': 0,
            'notes': 'Take with food',
            'pharmacy': self.pharmco.id
        }
        
        serializer = PrescriptionSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        # Save the deserialized data
        prescription = serializer.save()
        
        # Verify fields were set correctly
        self.assertEqual(prescription.consultation, self.consultation)
        self.assertEqual(prescription.medication_name, 'Ibuprofen')
        self.assertEqual(prescription.dosage, '200mg')
        self.assertEqual(prescription.frequency, '4 times daily')
        self.assertEqual(prescription.duration, '5 days')
        self.assertEqual(prescription.refills, 0)
        self.assertEqual(prescription.notes, 'Take with food')
        self.assertEqual(prescription.pharmacy, self.pharmco)
    
    def test_prescription_deserialization_invalid_data(self):
        """Test serializer validation with invalid data"""
        # Missing required fields
        data = {
            'consultation': self.consultation.id,
            # Missing medication_name
            'dosage': '200mg',
            'frequency': '4 times daily'
        }
        
        serializer = PrescriptionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('medication_name', serializer.errors)
        
        # Invalid refills value (negative)
        data = {
            'consultation': self.consultation.id,
            'medication_name': 'Aspirin',
            'dosage': '100mg',
            'frequency': 'twice daily',
            'duration': '7 days',
            'refills': -1  # Invalid negative value
        }
        
        serializer = PrescriptionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('refills', serializer.errors)
    
    def test_prescription_update(self):
        """Test updating a prescription with serializer"""
        data = {
            'medication_name': 'Augmentin',
            'dosage': '875mg',
            'notes': 'Updated instructions'
        }
        
        serializer = PrescriptionSerializer(self.prescription, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        # Save the updates
        updated_prescription = serializer.save()
        
        # Verify only specified fields were updated
        self.assertEqual(updated_prescription.medication_name, 'Augmentin')
        self.assertEqual(updated_prescription.dosage, '875mg')
        self.assertEqual(updated_prescription.notes, 'Updated instructions')
        self.assertEqual(updated_prescription.frequency, '3 times daily')  # Unchanged
        self.assertEqual(updated_prescription.duration, '10 days')  # Unchanged
        self.assertEqual(updated_prescription.refills, 1)  # Unchanged


class MessageSerializerTests(TestCase):
    def setUp(self):
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
        
        # Create a test appointment
        self.now = timezone.now()
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            provider=self.provider,
            scheduled_time=self.now + timedelta(days=1),
            end_time=self.now + timedelta(days=1, hours=1),
            reason='Annual checkup',
            appointment_type='video_consultation'
        )
        
        # Create a test message
        self.message = Message.objects.create(
            sender=self.patient,
            receiver=self.provider,
            appointment=self.appointment,
            content='Do I need to prepare anything for the appointment?'
        )
    
    def test_message_serialization(self):
        """Test that message serialization includes all fields"""
        serializer = MessageSerializer(self.message)
        data = serializer.data
        
        # Verify primary fields
        self.assertEqual(data['id'], self.message.id)
        self.assertEqual(data['sender'], self.patient.id)
        self.assertEqual(data['receiver'], self.provider.id)
        self.assertEqual(data['appointment'], self.appointment.id)
        self.assertEqual(data['content'], 'Do I need to prepare anything for the appointment?')
        self.assertFalse(data['read'])
        self.assertIsNone(data['read_at'])
        
        # Verify nested fields are present
        self.assertIn('sender_details', data)
        self.assertIn('receiver_details', data)
        
        # Verify nested user details
        self.assertEqual(data['sender_details']['username'], 'testpatient')
        self.assertEqual(data['sender_details']['first_name'], 'Test')
        self.assertEqual(data['sender_details']['last_name'], 'Patient')
        self.assertEqual(data['receiver_details']['username'], 'testprovider')
        self.assertEqual(data['receiver_details']['first_name'], 'Test')
        self.assertEqual(data['receiver_details']['last_name'], 'Provider')
    
    def test_message_deserialization_valid_data(self):
        """Test that message can be deserialized with valid data"""
        data = {
            'sender': self.provider.id,
            'receiver': self.patient.id,
            'appointment': self.appointment.id,
            'content': 'No preparation needed, just bring your insurance card.'
        }
        
        serializer = MessageSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        # Save the deserialized data
        message = serializer.save()
        
        # Verify fields were set correctly
        self.assertEqual(message.sender, self.provider)
        self.assertEqual(message.receiver, self.patient)
        self.assertEqual(message.appointment, self.appointment)
        self.assertEqual(message.content, 'No preparation needed, just bring your insurance card.')
        self.assertFalse(message.read)
        self.assertIsNone(message.read_at)
    
    def test_message_deserialization_with_optional_fields(self):
        """Test that message can be deserialized without optional fields"""
        # Message without appointment reference
        data = {
            'sender': self.provider.id,
            'receiver': self.patient.id,
            'content': 'General message not related to any appointment.'
        }
        
        serializer = MessageSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        # Save the deserialized data
        message = serializer.save()
        
        # Verify fields were set correctly
        self.assertEqual(message.sender, self.provider)
        self.assertEqual(message.receiver, self.patient)
        self.assertIsNone(message.appointment)
        self.assertEqual(message.content, 'General message not related to any appointment.')
    
    def test_message_deserialization_invalid_data(self):
        """Test serializer validation with invalid data"""
        # Missing required content field
        data = {
            'sender': self.provider.id,
            'receiver': self.patient.id,
            'appointment': self.appointment.id
            # Missing content
        }
        
        serializer = MessageSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('content', serializer.errors)
        
        # Missing required sender/receiver
        data = {
            # Missing sender
            'receiver': self.patient.id,
            'content': 'Invalid message'
        }
        
        serializer = MessageSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('sender', serializer.errors)
    
    def test_message_update(self):
        """Test updating a message with serializer"""
        # Mark as read with timestamp
        read_time = timezone.now()
        
        data = {
            'read': True,
            'read_at': read_time.isoformat()
        }
        
        serializer = MessageSerializer(self.message, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        # Save the updates
        updated_message = serializer.save()
        
        # Verify fields were updated correctly
        self.assertTrue(updated_message.read)
        self.assertIsNotNone(updated_message.read_at)
        # Other fields should remain unchanged
        self.assertEqual(updated_message.content, 'Do I need to prepare anything for the appointment?')
        self.assertEqual(updated_message.sender, self.patient)
        self.assertEqual(updated_message.receiver, self.provider)


class MedicalDocumentSerializerTests(TestCase):
    def setUp(self):
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
        
        # Create a test appointment
        self.now = timezone.now()
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            provider=self.provider,
            scheduled_time=self.now,
            end_time=self.now + timedelta(hours=1),
            reason='Annual checkup',
            appointment_type='video_consultation'
        )
        
        # Create a test document
        self.document = MedicalDocument.objects.create(
            patient=self.patient,
            uploaded_by=self.provider,
            appointment=self.appointment,
            document_type='lab_result',
            title='Blood Test Results',
            file='medical_documents/2023/03/13/test_file.pdf',
            notes='Routine blood work'
        )
    
    def test_document_serialization(self):
        """Test that document serialization includes all fields"""
        serializer = MedicalDocumentSerializer(self.document)
        data = serializer.data
        
        # Verify primary fields
        self.assertEqual(data['id'], self.document.id)
        self.assertEqual(data['patient'], self.patient.id)
        self.assertEqual(data['uploaded_by'], self.provider.id)
        self.assertEqual(data['appointment'], self.appointment.id)
        self.assertEqual(data['document_type'], 'lab_result')
        self.assertEqual(data['title'], 'Blood Test Results')
        self.assertEqual(data['file'], 'medical_documents/2023/03/13/test_file.pdf')
        self.assertEqual(data['notes'], 'Routine blood work')
        
        # Verify nested fields are present
        self.assertIn('uploaded_by_details', data)
        
        # Verify nested user details
        self.assertEqual(data['uploaded_by_details']['username'], 'testprovider')
        self.assertEqual(data['uploaded_by_details']['first_name'], 'Test')
        self.assertEqual(data['uploaded_by_details']['last_name'], 'Provider')
    
    def test_document_deserialization_valid_data(self):
        """Test that document can be deserialized with valid data"""
        data = {
            'patient': self.patient.id,
            'appointment': self.appointment.id,
            'document_type': 'report',
            'title': 'Annual Physical Report',
            'file': 'medical_documents/2023/03/13/physical_report.pdf',
            'notes': 'Physical examination report'
        }
        
        serializer = MedicalDocumentSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        # Save the deserialized data with uploaded_by field
        document = serializer.save(uploaded_by=self.provider)
        
        # Verify fields were set correctly
        self.assertEqual(document.patient, self.patient)
        self.assertEqual(document.uploaded_by, self.provider)
        self.assertEqual(document.appointment, self.appointment)
        self.assertEqual(document.document_type, 'report')
        self.assertEqual(document.title, 'Annual Physical Report')
        self.assertEqual(document.file, 'medical_documents/2023/03/13/physical_report.pdf')
        self.assertEqual(document.notes, 'Physical examination report')
    
    def test_document_deserialization_with_optional_fields(self):
        """Test that document can be deserialized without optional fields"""
        # Document without appointment reference and notes
        data = {
            'patient': self.patient.id,
            'document_type': 'other',
            'title': 'Insurance Information',
            'file': 'medical_documents/2023/03/13/insurance.pdf'
        }
        
        serializer = MedicalDocumentSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        # Save the deserialized data with uploaded_by field
        document = serializer.save(uploaded_by=self.provider)
        
        # Verify fields were set correctly
        self.assertEqual(document.patient, self.patient)
        self.assertEqual(document.uploaded_by, self.provider)
        self.assertIsNone(document.appointment)
        self.assertEqual(document.document_type, 'other')
        self.assertEqual(document.title, 'Insurance Information')
        self.assertEqual(document.file, 'medical_documents/2023/03/13/insurance.pdf')
        self.assertIsNone(document.notes)
    
    def test_document_deserialization_invalid_data(self):
        """Test serializer validation with invalid data"""
        # Missing required fields
        data = {
            'patient': self.patient.id,
            # Missing document_type
            'title': 'Invalid Document',
            'file': 'medical_documents/2023/03/13/invalid.pdf'
        }
        
        serializer = MedicalDocumentSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('document_type', serializer.errors)
        
        # Invalid document_type
        data = {
            'patient': self.patient.id,
            'document_type': 'invalid_type',  # Not in DOCUMENT_TYPES choices
            'title': 'Invalid Document',
            'file': 'medical_documents/2023/03/13/invalid.pdf'
        }
        
        serializer = MedicalDocumentSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('document_type', serializer.errors)
    
def test_document_update(self):
        """Test updating a document with serializer"""
        data = {
            'title': 'Updated Blood Test Results',
            'notes': 'Updated notes with additional findings',
            'document_type': 'report'
        }
        
        serializer = MedicalDocumentSerializer(self.document, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        # Save the updates
        updated_document = serializer.save()
        
        # Verify fields were updated correctly
        self.assertEqual(updated_document.title, 'Updated Blood Test Results')
        self.assertEqual(updated_document.notes, 'Updated notes with additional findings')
        self.assertEqual(updated_document.document_type, 'report')
        # Other fields should remain unchanged
        self.assertEqual(updated_document.patient, self.patient)
        self.assertEqual(updated_document.uploaded_by, self.provider)
        self.assertEqual(updated_document.file, 'medical_documents/2023/03/13/test_file.pdf')


class ProviderAvailabilitySerializerTests(TestCase):
    def setUp(self):
        # Create test provider
        self.provider = User.objects.create_user(
            username='testprovider',
            email='provider@example.com',
            password='testpass123',
            role='provider'
        )
        
        # Create test availability
        self.availability = ProviderAvailability.objects.create(
            provider=self.provider,
            day_of_week=1,  # Tuesday
            start_time=time(9, 0),  # 9:00 AM
            end_time=time(17, 0),  # 5:00 PM
            is_available=True
        )
    
    def test_availability_serialization(self):
        """Test that availability serialization includes all fields"""
        serializer = ProviderAvailabilitySerializer(self.availability)
        data = serializer.data
        
        # Verify all fields are included
        self.assertEqual(data['id'], self.availability.id)
        self.assertEqual(data['provider'], self.provider.id)
        self.assertEqual(data['day_of_week'], 1)
        self.assertEqual(data['start_time'], '09:00:00')
        self.assertEqual(data['end_time'], '17:00:00')
        self.assertTrue(data['is_available'])
    
    def test_availability_deserialization_valid_data(self):
        """Test that availability can be deserialized with valid data"""
        data = {
            'provider': self.provider.id,
            'day_of_week': 2,  # Wednesday
            'start_time': '10:00:00',
            'end_time': '18:00:00',
            'is_available': True
        }
        
        serializer = ProviderAvailabilitySerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        # Save the deserialized data
        availability = serializer.save()
        
        # Verify fields were set correctly
        self.assertEqual(availability.provider, self.provider)
        self.assertEqual(availability.day_of_week, 2)
        self.assertEqual(availability.start_time, time(10, 0))
        self.assertEqual(availability.end_time, time(18, 0))
        self.assertTrue(availability.is_available)
    
    def test_availability_deserialization_invalid_data(self):
        """Test serializer validation with invalid data"""
        # Invalid day_of_week (out of range)
        data = {
            'provider': self.provider.id,
            'day_of_week': 7,  # Invalid (should be 0-6)
            'start_time': '10:00:00',
            'end_time': '18:00:00',
            'is_available': True
        }
        
        serializer = ProviderAvailabilitySerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('day_of_week', serializer.errors)
        
        # End time before start time
        data = {
            'provider': self.provider.id,
            'day_of_week': 2,
            'start_time': '18:00:00',  # Later than end_time
            'end_time': '10:00:00',
            'is_available': True
        }
        
        serializer = ProviderAvailabilitySerializer(data=data)
        self.assertFalse(serializer.is_valid())
    
    def test_availability_update(self):
        """Test updating availability with serializer"""
        data = {
            'day_of_week': 3,  # Thursday
            'is_available': False
        }
        
        serializer = ProviderAvailabilitySerializer(self.availability, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        # Save the updates
        updated_availability = serializer.save()
        
        # Verify only specified fields were updated
        self.assertEqual(updated_availability.day_of_week, 3)
        self.assertFalse(updated_availability.is_available)
        self.assertEqual(updated_availability.start_time, time(9, 0))  # Unchanged
        self.assertEqual(updated_availability.end_time, time(17, 0))  # Unchanged
        self.assertEqual(updated_availability.provider, self.provider)  # Unchanged


class ProviderTimeOffSerializerTests(TestCase):
    def setUp(self):
        # Create test provider
        self.provider = User.objects.create_user(
            username='testprovider',
            email='provider@example.com',
            password='testpass123',
            role='provider'
        )
        
        # Create test time off
        self.now = timezone.now()
        self.time_off = ProviderTimeOff.objects.create(
            provider=self.provider,
            start_date=self.now + timedelta(days=10),
            end_date=self.now + timedelta(days=15),
            reason='Vacation'
        )
    
    def test_timeoff_serialization(self):
        """Test that time off serialization includes all fields"""
        serializer = ProviderTimeOffSerializer(self.time_off)
        data = serializer.data
        
        # Verify all fields are included
        self.assertEqual(data['id'], self.time_off.id)
        self.assertEqual(data['provider'], self.provider.id)
        self.assertEqual(data['reason'], 'Vacation')
        # Check dates are serialized properly
        self.assertIn(str((self.now + timedelta(days=10)).date()), data['start_date'])
        self.assertIn(str((self.now + timedelta(days=15)).date()), data['end_date'])
    
    def test_timeoff_deserialization_valid_data(self):
        """Test that time off can be deserialized with valid data"""
        start_date = self.now + timedelta(days=20)
        end_date = self.now + timedelta(days=22)
        
        data = {
            'provider': self.provider.id,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'reason': 'Conference'
        }
        
        serializer = ProviderTimeOffSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        # Save the deserialized data
        time_off = serializer.save()
        
        # Verify fields were set correctly
        self.assertEqual(time_off.provider, self.provider)
        self.assertEqual(time_off.reason, 'Conference')
        # Compare dates (ignoring microseconds for precise comparison)
        self.assertEqual(
            time_off.start_date.replace(microsecond=0),
            start_date.replace(microsecond=0)
        )
        self.assertEqual(
            time_off.end_date.replace(microsecond=0),
            end_date.replace(microsecond=0)
        )
    
    def test_timeoff_deserialization_invalid_data(self):
        """Test serializer validation with invalid data"""
        # Missing required fields
        data = {
            'provider': self.provider.id,
            # Missing start_date
            'end_date': (self.now + timedelta(days=5)).isoformat(),
            'reason': 'Invalid time off'
        }
        
        serializer = ProviderTimeOffSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('start_date', serializer.errors)
        
        # End date before start date
        data = {
            'provider': self.provider.id,
            'start_date': (self.now + timedelta(days=5)).isoformat(),
            'end_date': (self.now + timedelta(days=3)).isoformat(),  # Before start date
            'reason': 'Invalid time off'
        }
        
        serializer = ProviderTimeOffSerializer(data=data)
        self.assertFalse(serializer.is_valid())
    
    def test_timeoff_update(self):
        """Test updating time off with serializer"""
        new_end_date = self.now + timedelta(days=18)  # Extending end date
        
        data = {
            'end_date': new_end_date.isoformat(),
            'reason': 'Extended vacation'
        }
        
        serializer = ProviderTimeOffSerializer(self.time_off, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        # Save the updates
        updated_time_off = serializer.save()
        
        # Verify only specified fields were updated
        self.assertEqual(updated_time_off.reason, 'Extended vacation')
        # Compare dates (ignoring microseconds for precise comparison)
        self.assertEqual(
            updated_time_off.end_date.replace(microsecond=0),
            new_end_date.replace(microsecond=0)
        )
        # Start date should remain unchanged
        self.assertEqual(
            updated_time_off.start_date.replace(microsecond=0),
            (self.now + timedelta(days=10)).replace(microsecond=0)
        )
        self.assertEqual(updated_time_off.provider, self.provider)  # Unchanged
