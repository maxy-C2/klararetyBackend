# telemedicine/tests/unit/test_email_service.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest.mock import patch, MagicMock
from datetime import timedelta

from telemedicine.models import Appointment, Consultation
from telemedicine.services.email_service import EmailService

User = get_user_model()

class EmailServiceTests(TestCase):
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
        
        # Create a test consultation
        self.consultation = Consultation.objects.create(
            appointment=self.appointment,
            notes='Initial consultation',
            zoom_meeting_id='123456789',
            zoom_meeting_password='password123',
            zoom_join_url='https://zoom.us/j/123456789',
            zoom_start_url='https://zoom.us/s/123456789'
        )
    
    @patch('telemedicine.services.email_service.send_mail')
    def test_send_appointment_confirmation(self, mock_send_mail):
        """Test sending appointment confirmation email"""
        # Configure the mock
        mock_send_mail.return_value = 1
        
        # Call the method under test
        result = EmailService.send_appointment_confirmation(self.appointment)
        
        # Verify the result
        self.assertTrue(result)
        
        # Verify send_mail was called with correct parameters
        mock_send_mail.assert_called_once()
        args, kwargs = mock_send_mail.call_args
        
        # Check email subject and recipients
        self.assertIn('Appointment Confirmation', kwargs['subject'])
        self.assertEqual(kwargs['recipient_list'], [self.patient.email])
        
        # Check email content
        self.assertIn(self.patient.first_name, kwargs['message'])
        self.assertIn(self.provider.get_full_name(), kwargs['message'])
        self.assertIn('appointment has been scheduled', kwargs['message'])
    
    @patch('telemedicine.services.email_service.send_mail')
    def test_send_appointment_update_cancelled(self, mock_send_mail):
        """Test sending appointment cancellation email"""
        # Configure the mock
        mock_send_mail.return_value = 1
        
        # Update appointment status to cancelled
        self.appointment.status = 'cancelled'
        self.appointment.save()
        
        # Call the method under test
        result = EmailService.send_appointment_update(self.appointment, 'cancelled')
        
        # Verify the result
        self.assertTrue(result)
        
        # Verify send_mail was called with correct parameters
        mock_send_mail.assert_called_once()
        args, kwargs = mock_send_mail.call_args
        
        # Check email subject and recipients
        self.assertIn('Appointment Cancelled', kwargs['subject'])
        self.assertEqual(kwargs['recipient_list'], [self.patient.email])
        
        # Check email content
        self.assertIn(self.patient.first_name, kwargs['message'])
        self.assertIn('appointment has been cancelled', kwargs['message'])
    
    @patch('telemedicine.services.email_service.send_mail')
    def test_send_appointment_update_rescheduled(self, mock_send_mail):
        """Test sending appointment rescheduled email"""
        # Configure the mock
        mock_send_mail.return_value = 1
        
        # Update appointment status to rescheduled
        self.appointment.status = 'rescheduled'
        self.appointment.save()
        
        # Call the method under test
        result = EmailService.send_appointment_update(self.appointment, 'rescheduled')
        
        # Verify the result
        self.assertTrue(result)
        
        # Verify send_mail was called with correct parameters
        mock_send_mail.assert_called_once()
        args, kwargs = mock_send_mail.call_args
        
        # Check email subject and recipients
        self.assertIn('Appointment Rescheduled', kwargs['subject'])
        self.assertEqual(kwargs['recipient_list'], [self.patient.email])
        
        # Check email content
        self.assertIn(self.patient.first_name, kwargs['message'])
        self.assertIn('appointment has been rescheduled', kwargs['message'])
    
    @patch('telemedicine.services.email_service.send_mail')
    def test_send_appointment_reminder(self, mock_send_mail):
        """Test sending appointment reminder email"""
        # Configure the mock
        mock_send_mail.return_value = 1
        
        # Call the method under test
        result = EmailService.send_appointment_reminder(self.appointment)
        
        # Verify the result
        self.assertTrue(result)
        
        # Verify send_mail was called with correct parameters
        mock_send_mail.assert_called_once()
        args, kwargs = mock_send_mail.call_args
        
        # Check email subject and recipients
        self.assertIn('Appointment Reminder', kwargs['subject'])
        self.assertEqual(kwargs['recipient_list'], [self.patient.email])
        
        # Check email content
        self.assertIn(self.patient.first_name, kwargs['message'])
        self.assertIn('reminder about your upcoming appointment', kwargs['message'])
    
    @patch('telemedicine.services.email_service.send_mail')
    def test_send_email_with_template(self, mock_send_mail):
        """Test sending email with custom template"""
        # Configure the mock
        mock_send_mail.return_value = 1
        
        # Call the method under test with custom template
        template_data = {
            'patient_name': self.patient.first_name,
            'appointment_date': self.appointment.scheduled_time.strftime('%Y-%m-%d'),
            'appointment_time': self.appointment.scheduled_time.strftime('%H:%M'),
            'provider_name': self.provider.get_full_name(),
        }
        
        result = EmailService.send_email_with_template(
            subject='Custom Email Subject',
            template_name='custom_template.html',
            recipient_email=self.patient.email,
            template_data=template_data
        )
        
        # Verify the result
        self.assertTrue(result)
        
        # Verify send_mail was called with correct parameters
        mock_send_mail.assert_called_once()
        args, kwargs = mock_send_mail.call_args
        
        # Check email subject and recipients
        self.assertEqual(kwargs['subject'], 'Custom Email Subject')
        self.assertEqual(kwargs['recipient_list'], [self.patient.email])
    
    @patch('telemedicine.services.email_service.send_mail')
    def test_handle_email_sending_failure(self, mock_send_mail):
        """Test handling email sending failure"""
        # Configure the mock to simulate failure
        mock_send_mail.side_effect = Exception('SMTP server error')
        
        # Call the method under test
        result = EmailService.send_appointment_confirmation(self.appointment)
        
        # Verify the result indicates failure
        self.assertFalse(result)
