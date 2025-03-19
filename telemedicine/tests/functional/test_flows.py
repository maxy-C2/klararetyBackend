# telemedicine/tests/functional/test_flows.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from datetime import timedelta
from unittest.mock import patch, MagicMock

from telemedicine.models import (
    Appointment, Consultation, Prescription, Message, ProviderAvailability
)
from telemedicine.services.zoom_service import ZoomService

User = get_user_model()

class AppointmentToConsultationFlowTest(TestCase):
    """Test the complete flow from appointment creation to consultation completion"""
    
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
        
        # Create provider availability
        self.now = timezone.now()
        today_weekday = self.now.weekday()
        tomorrow = self.now + timedelta(days=1) 
        tomorrow_weekday = tomorrow.weekday()
        
        ProviderAvailability.objects.create(
            provider=self.provider,
            day_of_week=tomorrow_weekday,
            start_time=tomorrow.time().replace(hour=9, minute=0, second=0, microsecond=0),
            end_time=tomorrow.time().replace(hour=17, minute=0, second=0, microsecond=0),
            is_available=True
        )
        
        # Setup API client
        self.client = APIClient()
    
    @patch('telemedicine.services.zoom_service.ZoomService')
    @patch('telemedicine.services.email_service.EmailService')
    def test_complete_appointment_consultation_flow(self, mock_email_service, mock_zoom_service):
        """Test complete flow from scheduling to completion"""
        # Mock Zoom service
        mock_zoom_instance = mock_zoom_service.return_value
        mock_zoom_instance.create_meeting.return_value = {
            'id': '123456789',
            'password': 'test_password',
            'join_url': 'https://zoom.us/j/123456789',
            'start_url': 'https://zoom.us/s/123456789'
        }
        
        # Mock Email service
        mock_email_service.send_appointment_confirmation.return_value = True
        mock_email_service.send_appointment_update.return_value = True
        
        # 1. Schedule an appointment
        self.client.force_authenticate(user=self.patient)
        scheduled_time = self.now + timedelta(days=1)
        scheduled_time = scheduled_time.replace(hour=10, minute=0, second=0, microsecond=0)
        end_time = scheduled_time + timedelta(hours=1)
        
        appointment_data = {
            'patient': self.patient.id,
            'provider': self.provider.id,
            'scheduled_time': scheduled_time.isoformat(),
            'end_time': end_time.isoformat(),
            'reason': 'Test appointment',
            'appointment_type': 'video_consultation'
        }
        
        response = self.client.post('/api/v1/telemedicine/appointments/', appointment_data, format='json')
        self.assertEqual(response.status_code, 201)
        
        appointment_id = response.data['id']
        appointment = Appointment.objects.get(id=appointment_id)
        
        # 2. Verify consultation was created automatically
        self.assertTrue(hasattr(appointment, 'consultation'))
        consultation = appointment.consultation
        self.assertEqual(consultation.zoom_meeting_id, '123456789')
        
        # 3. Send message from patient to provider
        message_data = {
            'receiver': self.provider.id,
            'appointment': appointment.id,
            'content': 'I have a question about the appointment'
        }
        
        message_response = self.client.post('/api/v1/telemedicine/messages/', message_data, format='json')
        self.assertEqual(message_response.status_code, 201)
        
        # 4. Provider responds to the message
        self.client.force_authenticate(user=self.provider)
        reply_data = {
            'receiver': self.patient.id,
            'appointment': appointment.id,
            'content': 'What questions do you have?'
        }
        
        reply_response = self.client.post('/api/v1/telemedicine/messages/', reply_data, format='json')
        self.assertEqual(reply_response.status_code, 201)
        
        # 5. Start the consultation as provider
        start_response = self.client.post(f'/api/v1/telemedicine/consultations/{consultation.id}/start/')
        self.assertEqual(start_response.status_code, 200)
        
        # Verify appointment status changed
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, 'in_progress')
        
        # 6. Create a prescription
        prescription_data = {
            'consultation': consultation.id,
            'medication_name': 'Test Medication',
            'dosage': '10mg',
            'frequency': 'Once daily',
            'duration': '7 days',
            'refills': 0,
            'notes': 'Take with food'
        }
        
        prescription_response = self.client.post('/api/v1/telemedicine/prescriptions/', prescription_data, format='json')
        self.assertEqual(prescription_response.status_code, 201)
        
        # 7. End the consultation
        end_response = self.client.post(f'/api/v1/telemedicine/consultations/{consultation.id}/end/')
        self.assertEqual(end_response.status_code, 200)
        
        # 8. Verify final states
        appointment.refresh_from_db()
        consultation.refresh_from_db()
        
        self.assertEqual(appointment.status, 'completed')
        self.assertIsNotNone(consultation.start_time)
        self.assertIsNotNone(consultation.end_time)
        self.assertIsNotNone(consultation.duration)
        
        # 9. Patient can view the prescription
        self.client.force_authenticate(user=self.patient)
        prescription_list_response = self.client.get('/api/v1/telemedicine/prescriptions/')
        self.assertEqual(prescription_list_response.status_code, 200)
        self.assertEqual(len(prescription_list_response.data), 1)
        self.assertEqual(prescription_list_response.data[0]['medication_name'], 'Test Medication')


class PatientRescheduleFlowTest(TestCase):
    """Test the flow of a patient rescheduling an appointment"""
    
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
        
        # Create provider availability for multiple days
        self.now = timezone.now()
        for i in range(7):  # For the whole week
            ProviderAvailability.objects.create(
                provider=self.provider,
                day_of_week=i,
                start_time=self.now.time().replace(hour=9, minute=0, second=0, microsecond=0),
                end_time=self.now.time().replace(hour=17, minute=0, second=0, microsecond=0),
                is_available=True
            )
        
        # Setup API client
        self.client = APIClient()
        
        # Create an initial appointment
        self.client.force_authenticate(user=self.patient)
        scheduled_time = self.now + timedelta(days=1)
        scheduled_time = scheduled_time.replace(hour=10, minute=0, second=0, microsecond=0)
        end_time = scheduled_time + timedelta(hours=1)
        
        appointment_data = {
            'patient': self.patient.id,
            'provider': self.provider.id,
            'scheduled_time': scheduled_time.isoformat(),
            'end_time': end_time.isoformat(),
            'reason': 'Initial appointment',
            'appointment_type': 'video_consultation'
        }
        
        with patch('telemedicine.services.email_service.EmailService') as mock_email:
            mock_email.send_appointment_confirmation.return_value = True
            response = self.client.post('/api/v1/telemedicine/appointments/', appointment_data, format='json')
        
        self.appointment_id = response.data['id']
        self.appointment = Appointment.objects.get(id=self.appointment_id)
    
    @patch('telemedicine.services.email_service.EmailService')
    def test_reschedule_appointment_flow(self, mock_email_service):
        """Test the complete flow of rescheduling an appointment"""
        mock_email_service.send_appointment_update.return_value = True
        
        # 1. Check available slots for rescheduling
        new_date = (self.now + timedelta(days=3)).date()
        slot_response = self.client.get(
            f'/api/v1/telemedicine/appointments/available_slots/?provider={self.provider.id}&date={new_date.isoformat()}'
        )
        self.assertEqual(slot_response.status_code, 200)
        self.assertTrue(len(slot_response.data) > 0)
        
        # 2. Reschedule the appointment
        new_slot = slot_response.data[0]
        new_scheduled_time = timezone.make_aware(
            timezone.datetime.combine(new_date, timezone.datetime.strptime(new_slot['start'], '%H:%M').time())
        )
        new_end_time = timezone.make_aware(
            timezone.datetime.combine(new_date, timezone.datetime.strptime(new_slot['end'], '%H:%M').time())
        )
        
        reschedule_data = {
            'scheduled_time': new_scheduled_time.isoformat(),
            'end_time': new_end_time.isoformat(),
        }
        
        reschedule_response = self.client.post(
            f'/api/v1/telemedicine/appointments/{self.appointment_id}/reschedule/', 
            reschedule_data, 
            format='json'
        )
        self.assertEqual(reschedule_response.status_code, 200)
        
        # 3. Verify the appointment was rescheduled
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'rescheduled')
        
        # Convert datetime objects to strings with the same precision for comparison
        appointment_time_str = self.appointment.scheduled_time.isoformat()
        new_time_str = new_scheduled_time.isoformat()
        
        self.assertEqual(appointment_time_str, new_time_str)
        
        # 4. Verify consultation is updated accordingly
        consultation = self.appointment.consultation
        
        with patch('telemedicine.services.zoom_service.ZoomService') as mock_zoom:
            mock_zoom_instance = mock_zoom.return_value
            mock_zoom_instance.get_meeting.return_value = {
                'id': consultation.zoom_meeting_id,
                'start_time': new_scheduled_time.isoformat(),
                'duration': 60,
                'topic': 'Updated Meeting'
            }
            
            # Get consultation details
            response = self.client.get(f'/api/v1/telemedicine/consultations/{consultation.id}/')
            self.assertEqual(response.status_code, 200)
            
        # 5. Cancel the appointment
        cancel_response = self.client.post(f'/api/v1/telemedicine/appointments/{self.appointment_id}/cancel/')
        self.assertEqual(cancel_response.status_code, 200)
        
        # 6. Verify cancellation
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'cancelled')


class ProviderTimeOffConflictTest(TestCase):
    """Test the flow when a provider sets time off that conflicts with appointments"""
    
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
        
        # Create provider availability
        self.now = timezone.now()
        for i in range(7):  # For the whole week
            ProviderAvailability.objects.create(
                provider=self.provider,
                day_of_week=i,
                start_time=self.now.time().replace(hour=9, minute=0, second=0, microsecond=0),
                end_time=self.now.time().replace(hour=17, minute=0, second=0, microsecond=0),
                is_available=True
            )
        
        # Setup API client
        self.client = APIClient()
        
        # Create multiple appointments over the next week
        self.appointments = []
        with patch('telemedicine.services.email_service.EmailService') as mock_email:
            mock_email.send_appointment_confirmation.return_value = True
            
            for i in range(1, 6):  # Create 5 appointments
                scheduled_time = self.now + timedelta(days=i)
                scheduled_time = scheduled_time.replace(hour=10, minute=0, second=0, microsecond=0)
                end_time = scheduled_time + timedelta(hours=1)
                
                appointment_data = {
                    'patient': self.patient.id,
                    'provider': self.provider.id,
                    'scheduled_time': scheduled_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'reason': f'Appointment {i}',
                    'appointment_type': 'video_consultation'
                }
                
                self.client.force_authenticate(user=self.patient)
                response = self.client.post('/api/v1/telemedicine/appointments/', appointment_data, format='json')
                self.assertEqual(response.status_code, 201)
                self.appointments.append(Appointment.objects.get(id=response.data['id']))
    
    @patch('telemedicine.services.email_service.EmailService')
    def test_provider_timeoff_conflict_resolution(self, mock_email_service):
        """Test what happens when provider sets time off that conflicts with appointments"""
        mock_email_service.send_appointment_update.return_value = True
        
        # 1. Provider sets time off for the next 3 days
        start_date = self.now + timedelta(days=1)
        end_date = self.now + timedelta(days=3)
        
        timeoff_data = {
            'provider': self.provider.id,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'reason': 'Emergency time off'
        }
        
        self.client.force_authenticate(user=self.provider)
        response = self.client.post('/api/v1/telemedicine/timeoff/', timeoff_data, format='json')
        self.assertEqual(response.status_code, 201)
        
        # 2. Check affected appointments
        affected_appointments = Appointment.objects.filter(
            provider=self.provider,
            scheduled_time__range=(start_date, end_date),
            status__in=['scheduled', 'confirmed']
        )
        self.assertEqual(affected_appointments.count(), 3)  # First 3 appointments are affected
        
        # 3. Provider cancels affected appointments
        for appointment in affected_appointments:
            cancel_response = self.client.post(f'/api/v1/telemedicine/appointments/{appointment.id}/cancel/')
            self.assertEqual(cancel_response.status_code, 200)
            
            # Verify cancellation
            appointment.refresh_from_db()
            self.assertEqual(appointment.status, 'cancelled')
            
            # Send a message to the patient explaining the cancellation
            message_data = {
                'receiver': self.patient.id,
                'appointment': appointment.id,
                'content': 'I apologize, but I need to cancel our appointment due to an emergency.'
            }
            message_response = self.client.post('/api/v1/telemedicine/messages/', message_data, format='json')
            self.assertEqual(message_response.status_code, 201)
        
        # 4. Verify unaffected appointments
        unaffected_appointments = Appointment.objects.filter(
            provider=self.provider,
            scheduled_time__gt=end_date,
            status__in=['scheduled', 'confirmed']
        )
        self.assertEqual(unaffected_appointments.count(), 2)  # Last 2 appointments are unaffected
        
        # 5. Check available slots after time off period
        post_timeoff_date = (end_date + timedelta(days=1)).date()
        slot_response = self.client.get(
            f'/api/v1/telemedicine/appointments/available_slots/?provider={self.provider.id}&date={post_timeoff_date.isoformat()}'
        )
        self.assertEqual(slot_response.status_code, 200)
        self.assertTrue(len(slot_response.data) > 0)
        
        # 6. Patient reschedules one of the cancelled appointments
        self.client.force_authenticate(user=self.patient)
        new_slot = slot_response.data[0]
        new_scheduled_time = timezone.make_aware(
            timezone.datetime.combine(post_timeoff_date, timezone.datetime.strptime(new_slot['start'], '%H:%M').time())
        )
        new_end_time = timezone.make_aware(
            timezone.datetime.combine(post_timeoff_date, timezone.datetime.strptime(new_slot['end'], '%H:%M').time())
        )
        
        cancelled_appointment = affected_appointments[0]
        reschedule_data = {
            'patient': self.patient.id,
            'provider': self.provider.id,
            'scheduled_time': new_scheduled_time.isoformat(),
            'end_time': new_end_time.isoformat(),
            'reason': 'Rescheduled appointment',
            'appointment_type': 'video_consultation',
            'parent_appointment': cancelled_appointment.id
        }
        
        with patch('telemedicine.services.email_service.EmailService') as mock_email:
            mock_email.send_appointment_confirmation.return_value = True
            response = self.client.post('/api/v1/telemedicine/appointments/', reschedule_data, format='json')
            self.assertEqual(response.status_code, 201)
        
        # 7. Verify the new appointment is created as a follow-up to the cancelled one
        new_appointment_id = response.data['id']
        new_appointment = Appointment.objects.get(id=new_appointment_id)
        self.assertEqual(new_appointment.parent_appointment.id, cancelled_appointment.id)
