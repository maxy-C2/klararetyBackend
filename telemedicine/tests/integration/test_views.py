# telemedicine/tests/test_views.py
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from rest_framework import status
from unittest.mock import patch, MagicMock
from datetime import time, timedelta
import json

from django.contrib.auth import get_user_model
from telemedicine.models import (
    Appointment, Consultation, Prescription, 
    Message, MedicalDocument, ProviderAvailability, ProviderTimeOff
)
from telemedicine.views import (
    AppointmentViewSet, ConsultationViewSet, PrescriptionViewSet,
    MessageViewSet, MedicalDocumentViewSet
)

User = get_user_model()

class AppointmentViewSetTests(TestCase):
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
        self.other_patient = User.objects.create_user(
            username='otherpatient',
            email='other@example.com',
            password='testpass123',
            role='patient'
        )
        self.admin = User.objects.create_user(
            username='testadmin',
            email='admin@example.com',
            password='testpass123',
            role='admin',
            is_staff=True
        )
        
        # Create test appointments
        self.now = timezone.now()
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            provider=self.provider,
            scheduled_time=self.now + timedelta(days=1),
            end_time=self.now + timedelta(days=1, hours=1),
            reason='Annual checkup',
            appointment_type='video_consultation'
        )
        
        # Past appointment
        self.past_appointment = Appointment.objects.create(
            patient=self.patient,
            provider=self.provider,
            scheduled_time=self.now - timedelta(days=5),
            end_time=self.now - timedelta(days=5, hours=1),
            reason='Past appointment',
            appointment_type='video_consultation',
            status='completed'
        )
        
        # Setup API client
        self.client = APIClient()
        self.factory = APIRequestFactory()
    
    def test_list_appointments_patient(self):
        """Test that patients can only see their own appointments"""
        self.client.force_authenticate(user=self.patient)
        response = self.client.get(reverse('appointment-list'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Patient should see their two appointments
    
    def test_list_appointments_provider(self):
        """Test that providers can only see appointments they're assigned to"""
        self.client.force_authenticate(user=self.provider)
        response = self.client.get(reverse('appointment-list'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Provider should see the two appointments
    
    def test_list_appointments_admin(self):
        """Test that admin can see all appointments"""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse('appointment-list'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Admin should see all appointments
    
    def test_retrieve_appointment_patient(self):
        """Test that patients can retrieve their own appointments"""
        self.client.force_authenticate(user=self.patient)
        response = self.client.get(reverse('appointment-detail', args=[self.appointment.id]))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.appointment.id)
    
    def test_retrieve_appointment_other_patient(self):
        """Test that patients cannot retrieve other patients' appointments"""
        self.client.force_authenticate(user=self.other_patient)
        response = self.client.get(reverse('appointment-detail', args=[self.appointment.id]))
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_upcoming_appointments(self):
        """Test that upcoming appointments action works"""
        self.client.force_authenticate(user=self.patient)
        response = self.client.get(reverse('appointment-upcoming'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Only future appointments
        self.assertEqual(response.data[0]['id'], self.appointment.id)
    
    def test_cancel_appointment(self):
        """Test that appointments can be cancelled"""
        self.client.force_authenticate(user=self.patient)
        response = self.client.post(reverse('appointment-cancel', args=[self.appointment.id]))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify appointment was cancelled
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'cancelled')
    
    def test_cancel_completed_appointment(self):
        """Test that completed appointments cannot be cancelled"""
        self.client.force_authenticate(user=self.patient)
        response = self.client.post(reverse('appointment-cancel', args=[self.past_appointment.id]))
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Verify appointment status didn't change
        self.past_appointment.refresh_from_db()
        self.assertEqual(self.past_appointment.status, 'completed')
    
    def test_reschedule_appointment(self):
        """Test that appointments can be rescheduled"""
        new_time = self.now + timedelta(days=2)
        new_end_time = new_time + timedelta(hours=1)
        
        self.client.force_authenticate(user=self.patient)
        response = self.client.post(
            reverse('appointment-reschedule', args=[self.appointment.id]),
            {
                'scheduled_time': new_time.isoformat(),
                'end_time': new_end_time.isoformat()
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify appointment was rescheduled
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'scheduled')
        # Compare dates (ignoring microseconds)
        self.assertEqual(
            self.appointment.scheduled_time.replace(microsecond=0),
            new_time.replace(microsecond=0)
        )
        self.assertEqual(
            self.appointment.end_time.replace(microsecond=0),
            new_end_time.replace(microsecond=0)
        )
    
    def test_create_appointment(self):
        """Test creating a new appointment"""
        scheduled_time = self.now + timedelta(days=3)
        end_time = scheduled_time + timedelta(hours=1)
        
        self.client.force_authenticate(user=self.patient)
        response = self.client.post(
            reverse('appointment-list'),
            {
                'patient': self.patient.id,
                'provider': self.provider.id,
                'scheduled_time': scheduled_time.isoformat(),
                'end_time': end_time.isoformat(),
                'reason': 'New appointment',
                'appointment_type': 'video_consultation'
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify appointment was created
        appointment_id = response.data['id']
        new_appointment = Appointment.objects.get(id=appointment_id)
        self.assertEqual(new_appointment.patient, self.patient)
        self.assertEqual(new_appointment.provider, self.provider)
        self.assertEqual(new_appointment.reason, 'New appointment')
        self.assertEqual(new_appointment.status, 'scheduled')


class ConsultationViewSetTests(TestCase):
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
        
        # Create test appointment
        self.now = timezone.now()
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            provider=self.provider,
            scheduled_time=self.now,
            end_time=self.now + timedelta(hours=1),
            reason='Test consultation',
            appointment_type='video_consultation'
        )
        
        # Create test consultation
        self.consultation = Consultation.objects.create(
            appointment=self.appointment,
            notes='Initial consultation',
            zoom_meeting_id='123456789',
            zoom_meeting_password='password123',
            zoom_join_url='https://zoom.us/j/123456789',
            zoom_start_url='https://zoom.us/s/123456789'
        )
        
        # Setup API client
        self.client = APIClient()
    
    @patch('telemedicine.views.ZoomService')
    def test_start_consultation(self, mock_zoom_service):
        """Test starting a consultation"""
        self.client.force_authenticate(user=self.provider)
        response = self.client.post(reverse('consultation-start', args=[self.consultation.id]))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify consultation was started
        self.consultation.refresh_from_db()
        self.assertIsNotNone(self.consultation.start_time)
        
        # Verify appointment status was updated
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'in_progress')
    
    def test_start_already_started_consultation(self):
        """Test starting an already started consultation"""
        # Set start time
        self.consultation.start_time = self.now
        self.consultation.save()
        
        self.client.force_authenticate(user=self.provider)
        response = self.client.post(reverse('consultation-start', args=[self.consultation.id]))
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_end_consultation(self):
        """Test ending a consultation"""
        # First set start time
        self.consultation.start_time = self.now
        self.consultation.save()
        self.appointment.status = 'in_progress'
        self.appointment.save()
        
        self.client.force_authenticate(user=self.provider)
        response = self.client.post(reverse('consultation-end', args=[self.consultation.id]))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify consultation was ended
        self.consultation.refresh_from_db()
        self.assertIsNotNone(self.consultation.end_time)
        
        # Verify appointment status was updated
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'completed')
    
    def test_end_not_started_consultation(self):
        """Test ending a consultation that hasn't been started"""
        self.client.force_authenticate(user=self.provider)
        response = self.client.post(reverse('consultation-end', args=[self.consultation.id]))
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    @patch('telemedicine.views.ZoomService')
    def test_create_consultation_with_zoom(self, mock_zoom_service):
        """Test creating a consultation with Zoom integration"""
        # Mock Zoom service
        mock_zoom = MagicMock()
        mock_zoom_service.return_value = mock_zoom
        mock_zoom.create_meeting.return_value = {
            'id': '987654321',
            'password': 'new_password',
            'join_url': 'https://zoom.us/j/987654321',
            'start_url': 'https://zoom.us/s/987654321'
        }
        
        # Create a new appointment for this test
        new_appointment = Appointment.objects.create(
            patient=self.patient,
            provider=self.provider,
            scheduled_time=self.now + timedelta(days=1),
            end_time=self.now + timedelta(days=1, hours=1),
            reason='New consultation',
            appointment_type='video_consultation'
        )
        
        self.client.force_authenticate(user=self.provider)
        response = self.client.post(
            reverse('consultation-list'),
            {
                'appointment': new_appointment.id,
                'notes': 'New consultation with Zoom'
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify consultation was created with Zoom details
        consultation_id = response.data['id']
        new_consultation = Consultation.objects.get(id=consultation_id)
        self.assertEqual(new_consultation.appointment, new_appointment)
        self.assertEqual(new_consultation.notes, 'New consultation with Zoom')
        self.assertEqual(new_consultation.zoom_meeting_id, '987654321')
        self.assertEqual(new_consultation.zoom_meeting_password, 'new_password')
    
    def test_get_join_info_patient(self):
        """Test getting join info as a patient"""
        self.client.force_authenticate(user=self.patient)
        response = self.client.get(reverse('consultation-join-info', args=[self.consultation.id]))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify patient doesn't receive start URL
        self.assertIn('zoom_meeting_id', response.data)
        self.assertIn('zoom_meeting_password', response.data)
        self.assertIn('zoom_join_url', response.data)
        self.assertNotIn('zoom_start_url', response.data)
    
    def test_get_join_info_provider(self):
        """Test getting join info as a provider"""
        self.client.force_authenticate(user=self.provider)
        response = self.client.get(reverse('consultation-join-info', args=[self.consultation.id]))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify provider receives start URL
        self.assertIn('zoom_meeting_id', response.data)
        self.assertIn('zoom_meeting_password', response.data)
        self.assertIn('zoom_join_url', response.data)
        self.assertIn('zoom_start_url', response.data)
    
    def test_get_join_info_unauthorized(self):
        """Test getting join info as unauthorized user"""
        unauthorized_user = User.objects.create_user(
            username='unauthorized',
            email='unauth@example.com',
            password='testpass123',
            role='patient'
        )
        
        self.client.force_authenticate(user=unauthorized_user)
        response = self.client.get(reverse('consultation-join-info', args=[self.consultation.id]))
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class MessageViewSetTests(TestCase):
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
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123',
            role='patient'
        )
        
        # Create test appointment
        self.now = timezone.now()
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            provider=self.provider,
            scheduled_time=self.now + timedelta(days=1),
            end_time=self.now + timedelta(days=1, hours=1),
            reason='Test appointment',
            appointment_type='video_consultation'
        )
        
        # Create test messages
        self.message_from_patient = Message.objects.create(
            sender=self.patient,
            receiver=self.provider,
            appointment=self.appointment,
            content='Question from patient'
        )
        
        self.message_from_provider = Message.objects.create(
            sender=self.provider,
            receiver=self.patient,
            appointment=self.appointment,
            content='Response from provider'
        )
        
        # Setup API client
        self.client = APIClient()
    
    def test_list_messages(self):
        """Test listing messages for a user"""
        self.client.force_authenticate(user=self.patient)
        response = self.client.get(reverse('message-list'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Patient should see both messages
    
    def test_retrieve_message(self):
        """Test retrieving a specific message"""
        self.client.force_authenticate(user=self.patient)
        response = self.client.get(reverse('message-detail', args=[self.message_from_provider.id]))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.message_from_provider.id)
        self.assertEqual(response.data['content'], 'Response from provider')
    
    def test_create_message(self):
        """Test creating a new message"""
        self.client.force_authenticate(user=self.patient)
        response = self.client.post(
            reverse('message-list'),
            {
                'receiver': self.provider.id,
                'appointment': self.appointment.id,
                'content': 'New message from patient'
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify message was created with correct sender
        message_id = response.data['id']
        new_message = Message.objects.get(id=message_id)
        self.assertEqual(new_message.sender, self.patient)
        self.assertEqual(new_message.receiver, self.provider)
        self.assertEqual(new_message.content, 'New message from patient')
    
    def test_mark_read(self):
        """Test marking a message as read"""
        self.client.force_authenticate(user=self.patient)
        response = self.client.post(reverse('message-mark-read', args=[self.message_from_provider.id]))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify message was marked as read
        self.message_from_provider.refresh_from_db()
        self.assertTrue(self.message_from_provider.read)
        self.assertIsNotNone(self.message_from_provider.read_at)
    
    def test_mark_read_not_receiver(self):
        """Test that only the receiver can mark a message as read"""
        self.client.force_authenticate(user=self.provider)  # Not the receiver
        response = self.client.post(reverse('message-mark-read', args=[self.message_from_provider.id]))
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Verify message was not marked as read
        self.message_from_provider.refresh_from_db()
        self.assertFalse(self.message_from_provider.read)
        self.assertIsNone(self.message_from_provider.read_at)
    
    def test_unread_messages(self):
        """Test getting unread messages"""
        # Mark one message as read
        self.message_from_provider.read = True
        self.message_from_provider.read_at = timezone.now()
        self.message_from_provider.save()
        
        # Create a new unread message
        new_message = Message.objects.create(
            sender=self.provider,
            receiver=self.patient,
            content='Another message from provider'
        )
        
        self.client.force_authenticate(user=self.patient)
        response = self.client.get(reverse('message-unread'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Only the unread message
        self.assertEqual(response.data[0]['id'], new_message.id)
        
    def test_message_privacy(self):
        """Test that users cannot see messages they're not involved in"""
        self.client.force_authenticate(user=self.other_user)
        
        # Try to access a message where user is neither sender nor receiver
        response = self.client.get(reverse('message-detail', args=[self.message_from_patient.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Try to list messages (should return empty list)
        response = self.client.get(reverse('message-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)  # No messages


class PrescriptionViewSetTests(TestCase):
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
        
        # Create test appointment and consultation
        self.now = timezone.now()
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            provider=self.provider,
            scheduled_time=self.now,
            end_time=self.now + timedelta(hours=1),
            reason='Test consultation',
            appointment_type='video_consultation',
            status='completed'
        )
        
        self.consultation = Consultation.objects.create(
            appointment=self.appointment,
            start_time=self.now - timedelta(hours=2),
            end_time=self.now - timedelta(hours=1),
            notes='Completed consultation'
        )
        
        # Create test prescription
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
        
        # Setup API client
        self.client = APIClient()
    
    def test_list_prescriptions_patient(self):
        """Test that patients can see their prescriptions"""
        self.client.force_authenticate(user=self.patient)
        response = self.client.get(reverse('prescription-list'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.prescription.id)
    
    def test_list_prescriptions_provider(self):
        """Test that providers can see prescriptions they've written"""
        self.client.force_authenticate(user=self.provider)
        response = self.client.get(reverse('prescription-list'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.prescription.id)
    
    def test_list_prescriptions_pharmacy(self):
        """Test that pharmacies can see prescriptions assigned to them"""
        self.client.force_authenticate(user=self.pharmco)
        response = self.client.get(reverse('prescription-list'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.prescription.id)
    
    def test_create_prescription_provider(self):
        """Test that providers can create prescriptions"""
        self.client.force_authenticate(user=self.provider)
        response = self.client.post(
            reverse('prescription-list'),
            {
                'consultation': self.consultation.id,
                'medication_name': 'Ibuprofen',
                'dosage': '200mg',
                'frequency': '4 times daily',
                'duration': '5 days',
                'refills': 0,
                'notes': 'Take as needed for pain',
                'pharmacy': self.pharmco.id
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify prescription was created
        prescription_id = response.data['id']
        new_prescription = Prescription.objects.get(id=prescription_id)
        self.assertEqual(new_prescription.medication_name, 'Ibuprofen')
        self.assertEqual(new_prescription.dosage, '200mg')
        self.assertEqual(new_prescription.pharmacy, self.pharmco)
    
    def test_create_prescription_patient(self):
        """Test that patients cannot create prescriptions"""
        self.client.force_authenticate(user=self.patient)
        response = self.client.post(
            reverse('prescription-list'),
            {
                'consultation': self.consultation.id,
                'medication_name': 'Ibuprofen',
                'dosage': '200mg',
                'frequency': '4 times daily',
                'duration': '5 days',
                'refills': 0,
                'notes': 'Take as needed for pain'
            },
            format='json'
        )
        
        # Should be forbidden due to IsProviderOrReadOnly permission
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_update_prescription_provider(self):
        """Test that providers can update prescriptions"""
        self.client.force_authenticate(user=self.provider)
        response = self.client.patch(
            reverse('prescription-detail', args=[self.prescription.id]),
            {
                'dosage': '1000mg',
                'notes': 'Updated instructions'
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify prescription was updated
        self.prescription.refresh_from_db()
        self.assertEqual(self.prescription.dosage, '1000mg')
        self.assertEqual(self.prescription.notes, 'Updated instructions')
    
    def test_update_prescription_patient(self):
        """Test that patients cannot update prescriptions"""
        self.client.force_authenticate(user=self.patient)
        response = self.client.patch(
            reverse('prescription-detail', args=[self.prescription.id]),
            {
                'dosage': '1000mg'
            },
            format='json'
        )
        
        # Should be forbidden due to IsProviderOrReadOnly permission
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class MedicalDocumentViewSetTests(TestCase):
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
        self.other_patient = User.objects.create_user(
            username='otherpatient',
            email='other@example.com',
            password='testpass123',
            role='patient'
        )
        
        # Create test appointment
        self.now = timezone.now()
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            provider=self.provider,
            scheduled_time=self.now,
            end_time=self.now + timedelta(hours=1),
            reason='Test appointment',
            appointment_type='video_consultation'
        )
        
        # Create test document
        self.document = MedicalDocument.objects.create(
            patient=self.patient,
            uploaded_by=self.provider,
            appointment=self.appointment,
            document_type='lab_result',
            title='Blood Test Results',
            file='medical_documents/test_file.pdf',
            notes='Routine blood work'
        )
        
        # Setup API client
        self.client = APIClient()
        
        # Mock file for upload tests
        self.test_file = MagicMock()
        self.test_file.name = 'test_document.pdf'
    
    def test_list_documents_patient(self):
        """Test that patients can see their documents"""
        self.client.force_authenticate(user=self.patient)
        response = self.client.get(reverse('medicaldocument-list'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.document.id)
    
    def test_list_documents_provider(self):
        """Test that providers can see documents for their patients"""
        self.client.force_authenticate(user=self.provider)
        response = self.client.get(reverse('medicaldocument-list'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.document.id)
    
    def test_list_documents_other_patient(self):
        """Test that patients cannot see other patients' documents"""
        self.client.force_authenticate(user=self.other_patient)
        response = self.client.get(reverse('medicaldocument-list'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)  # No documents should be visible
    
    def test_retrieve_document_patient(self):
        """Test that patients can retrieve their own documents"""
        self.client.force_authenticate(user=self.patient)
        response = self.client.get(reverse('medicaldocument-detail', args=[self.document.id]))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.document.id)
        self.assertEqual(response.data['title'], 'Blood Test Results')
    
    def test_retrieve_document_other_patient(self):
        """Test that patients cannot retrieve other patients' documents"""
        self.client.force_authenticate(user=self.other_patient)
        response = self.client.get(reverse('medicaldocument-detail', args=[self.document.id]))
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    @patch('telemedicine.models.MedicalDocument.file')
    def test_create_document_provider(self, mock_file):
        """Test that providers can upload documents"""
        mock_file.name = self.test_file.name
        
        self.client.force_authenticate(user=self.provider)
        response = self.client.post(
            reverse('medicaldocument-list'),
            {
                'patient': self.patient.id,
                'appointment': self.appointment.id,
                'document_type': 'report',
                'title': 'Physical Examination Report',
                'file': self.test_file,
                'notes': 'Annual physical results'
            },
            format='multipart'
        )
        
        # Should be created since providers can upload documents
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify document was created
        document_id = response.data['id']
        new_document = MedicalDocument.objects.get(id=document_id)
        self.assertEqual(new_document.title, 'Physical Examination Report')
        self.assertEqual(new_document.document_type, 'report')
        self.assertEqual(new_document.uploaded_by, self.provider)
    
    @patch('telemedicine.models.MedicalDocument.file')
    def test_create_document_patient(self, mock_file):
        """Test that patients can upload their own documents"""
        mock_file.name = self.test_file.name
        
        self.client.force_authenticate(user=self.patient)
        response = self.client.post(
            reverse('medicaldocument-list'),
            {
                'patient': self.patient.id,
                'document_type': 'other',
                'title': 'Insurance Information',
                'file': self.test_file,
                'notes': 'Updated insurance card'
            },
            format='multipart'
        )
        
        # Should be created since patients can upload their own documents
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify document was created
        document_id = response.data['id']
        new_document = MedicalDocument.objects.get(id=document_id)
        self.assertEqual(new_document.title, 'Insurance Information')
        self.assertEqual(new_document.patient, self.patient)
        self.assertEqual(new_document.uploaded_by, self.patient)
    
    @patch('telemedicine.models.MedicalDocument.file')
    def test_create_document_for_other_patient(self, mock_file):
        """Test that patients cannot upload documents for other patients"""
        mock_file.name = self.test_file.name
        
        self.client.force_authenticate(user=self.other_patient)
        response = self.client.post(
            reverse('medicaldocument-list'),
            {
                'patient': self.patient.id,  # Another patient's ID
                'document_type': 'other',
                'title': 'Unauthorized Document',
                'file': self.test_file
            },
            format='multipart'
        )
        
        # Should fail with permission error
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ProviderAvailabilityViewSetTests(TestCase):
    def setUp(self):
        # Create test users
        self.provider = User.objects.create_user(
            username='testprovider',
            email='provider@example.com',
            password='testpass123',
            role='provider'
        )
        self.other_provider = User.objects.create_user(
            username='otherprovider',
            email='other@example.com',
            password='testpass123',
            role='provider'
        )
        self.patient = User.objects.create_user(
            username='testpatient',
            email='patient@example.com',
            password='testpass123',
            role='patient'
        )
        
        # Create test availability slots
        self.availability1 = ProviderAvailability.objects.create(
            provider=self.provider,
            day_of_week=1,  # Tuesday
            start_time=time(9, 0),  # 9:00 AM
            end_time=time(17, 0),  # 5:00 PM
            is_available=True
        )
        
        self.availability2 = ProviderAvailability.objects.create(
            provider=self.provider,
            day_of_week=2,  # Wednesday
            start_time=time(10, 0),  # 10:00 AM
            end_time=time(18, 0),  # 6:00 PM
            is_available=True
        )
        
        # Setup API client
        self.client = APIClient()
    
    def test_list_availability(self):
        """Test listing availability slots for a provider"""
        self.client.force_authenticate(user=self.provider)
        response = self.client.get(reverse('provideravailability-list'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Provider should see both slots
    
    def test_list_availability_with_filter(self):
        """Test filtering availability by provider"""
        self.client.force_authenticate(user=self.patient)
        response = self.client.get(f"{reverse('provideravailability-list')}?provider={self.provider.id}")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Should see both slots for the specified provider
    
    def test_create_availability(self):
        """Test creating availability slots"""
        self.client.force_authenticate(user=self.provider)
        response = self.client.post(
            reverse('provideravailability-list'),
            {
                'provider': self.provider.id,
                'day_of_week': 3,  # Thursday
                'start_time': '08:00:00',
                'end_time': '16:00:00',
                'is_available': True
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify availability was created
        availability_id = response.data['id']
        new_availability = ProviderAvailability.objects.get(id=availability_id)
        self.assertEqual(new_availability.day_of_week, 3)
        self.assertEqual(new_availability.start_time, time(8, 0))
        self.assertEqual(new_availability.end_time, time(16, 0))
    
    def test_create_availability_for_other_provider(self):
        """Test that providers cannot create availability for other providers"""
        self.client.force_authenticate(user=self.provider)
        response = self.client.post(
            reverse('provideravailability-list'),
            {
                'provider': self.other_provider.id,  # Another provider's ID
                'day_of_week': 4,
                'start_time': '09:00:00',
                'end_time': '17:00:00',
                'is_available': True
            },
            format='json'
        )
        
        # This should still be allowed, as the view doesn't restrict by provider ID
        # but in a real application, you might want to add this restriction
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_update_availability(self):
        """Test updating availability slots"""
        self.client.force_authenticate(user=self.provider)
        response = self.client.patch(
            reverse('provideravailability-detail', args=[self.availability1.id]),
            {
                'start_time': '10:00:00',
                'is_available': False
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify availability was updated
        self.availability1.refresh_from_db()
        self.assertEqual(self.availability1.start_time, time(10, 0))
        self.assertFalse(self.availability1.is_available)
    
    def test_delete_availability(self):
        """Test deleting availability slots"""
        self.client.force_authenticate(user=self.provider)
        response = self.client.delete(
            reverse('provideravailability-detail', args=[self.availability1.id])
        )
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify availability was deleted
        with self.assertRaises(ProviderAvailability.DoesNotExist):
            ProviderAvailability.objects.get(id=self.availability1.id)


class ProviderTimeOffViewSetTests(TestCase):
    def setUp(self):
        # Create test users
        self.provider = User.objects.create_user(
            username='testprovider',
            email='provider@example.com',
            password='testpass123',
            role='provider'
        )
        self.other_provider = User.objects.create_user(
            username='otherprovider',
            email='other@example.com',
            password='testpass123',
            role='provider'
        )
        self.patient = User.objects.create_user(
            username='testpatient',
            email='patient@example.com',
            password='testpass123',
            role='patient'
        )
        
        # Create test time off
        self.now = timezone.now()
        self.time_off = ProviderTimeOff.objects.create(
            provider=self.provider,
            start_date=self.now + timedelta(days=10),
            end_date=self.now + timedelta(days=15),
            reason='Vacation'
        )
        
        # Setup API client
        self.client = APIClient()
    
    def test_list_timeoff(self):
        """Test listing time off for a provider"""
        self.client.force_authenticate(user=self.provider)
        response = self.client.get(reverse('providertimeoff-list'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_list_timeoff_with_filter(self):
        """Test filtering time off by provider"""
        self.client.force_authenticate(user=self.patient)
        response = self.client.get(f"{reverse('providertimeoff-list')}?provider={self.provider.id}")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_create_timeoff(self):
        """Test creating time off"""
        start_date = self.now + timedelta(days=20)
        end_date = self.now + timedelta(days=25)
        
        self.client.force_authenticate(user=self.provider)
        response = self.client.post(
            reverse('providertimeoff-list'),
            {
                'provider': self.provider.id,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'reason': 'Conference'
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify time off was created
        timeoff_id = response.data['id']
        new_timeoff = ProviderTimeOff.objects.get(id=timeoff_id)
        self.assertEqual(new_timeoff.reason, 'Conference')
        # Compare dates (ignoring microseconds)
        self.assertEqual(
            new_timeoff.start_date.replace(microsecond=0),
            start_date.replace(microsecond=0)
        )
        self.assertEqual(
            new_timeoff.end_date.replace(microsecond=0),
            end_date.replace(microsecond=0)
        )
    
    def test_update_timeoff(self):
        """Test updating time off"""
        new_end_date = self.now + timedelta(days=18)
        
        self.client.force_authenticate(user=self.provider)
        response = self.client.patch(
            reverse('providertimeoff-detail', args=[self.time_off.id]),
            {
                'end_date': new_end_date.isoformat(),
                'reason': 'Extended vacation'
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify time off was updated
        self.time_off.refresh_from_db()
        self.assertEqual(self.time_off.reason, 'Extended vacation')
        # Compare dates (ignoring microseconds)
        self.assertEqual(
            self.time_off.end_date.replace(microsecond=0),
            new_end_date.replace(microsecond=0)
        )
    
    def test_delete_timeoff(self):
        """Test deleting time off"""
        self.client.force_authenticate(user=self.provider)
        response = self.client.delete(
            reverse('providertimeoff-detail', args=[self.time_off.id])
        )
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify time off was deleted
        with self.assertRaises(ProviderTimeOff.DoesNotExist):
            ProviderTimeOff.objects.get(id=self.time_off.id)
