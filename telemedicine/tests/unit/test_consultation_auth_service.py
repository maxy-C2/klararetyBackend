# telemedicine/tests/unit/test_consultation_auth_service.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest.mock import patch, MagicMock
from datetime import timedelta
import re

from telemedicine.models import Appointment, Consultation
from telemedicine.services.consultation_auth_service import ConsultationAuthService

User = get_user_model()

class ConsultationAuthServiceTests(TestCase):
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
            scheduled_time=self.now + timedelta(minutes=30),
            end_time=self.now + timedelta(minutes=90),
            reason='Test consultation',
            appointment_type='video_consultation'
        )
        
        # Create a test consultation
        self.consultation = Consultation.objects.create(
            appointment=self.appointment,
            zoom_meeting_id='123456789',
            zoom_meeting_password='password123',
            zoom_join_url='https://zoom.us/j/123456789',
            zoom_start_url='https://zoom.us/s/123456789'
        )
    
    @patch('telemedicine.services.consultation_auth_service.send_mail')
    def test_send_access_code(self, mock_send_mail):
        """Test sending access code via email"""
        # Configure the mock
        mock_send_mail.return_value = 1
        
        # Call the method under test
        result = ConsultationAuthService.send_access_code(self.consultation)
        
        # Verify the result
        self.assertTrue(result)
        
        # Verify the consultation has an access code set
        self.consultation.refresh_from_db()
        self.assertIsNotNone(self.consultation.access_code)
        self.assertIsNotNone(self.consultation.access_code_expires)
        
        # Verify the access code format (6 digits)
        self.assertTrue(re.match(r'^\d{6}$', self.consultation.access_code))
        
        # Verify that expiration time is set correctly (10 minutes in the future)
        expected_expiry = timezone.now() + timedelta(minutes=10)
        self.assertAlmostEqual(
            self.consultation.access_code_expires.timestamp(),
            expected_expiry.timestamp(),
            delta=10  # Allow a 10-second difference for test execution time
        )
        
        # Verify send_mail was called with correct parameters
        mock_send_mail.assert_called_once()
        args, kwargs = mock_send_mail.call_args
        
        # Check email subject, content, and recipients
        self.assertIn('Access Code', kwargs['subject'])
        self.assertIn(self.consultation.access_code, kwargs['message'])
        self.assertEqual(kwargs['recipient_list'], [self.patient.email])
    
    def test_verify_access_code_valid(self):
        """Test verifying a valid access code"""
        # Set up a valid access code
        self.consultation.access_code = '123456'
        self.consultation.access_code_expires = timezone.now() + timedelta(minutes=5)
        self.consultation.save()
        
        # Call the method under test
        result = ConsultationAuthService.verify_access_code(self.consultation, '123456')
        
        # Verify the result
        self.assertTrue(result)
    
    def test_verify_access_code_invalid(self):
        """Test verifying an invalid access code"""
        # Set up a valid access code
        self.consultation.access_code = '123456'
        self.consultation.access_code_expires = timezone.now() + timedelta(minutes=5)
        self.consultation.save()
        
        # Call the method under test with wrong code
        result = ConsultationAuthService.verify_access_code(self.consultation, '654321')
        
        # Verify the result
        self.assertFalse(result)
    
    def test_verify_access_code_expired(self):
        """Test verifying an expired access code"""
        # Set up an expired access code
        self.consultation.access_code = '123456'
        self.consultation.access_code_expires = timezone.now() - timedelta(minutes=5)
        self.consultation.save()
        
        # Call the method under test
        result = ConsultationAuthService.verify_access_code(self.consultation, '123456')
        
        # Verify the result
        self.assertFalse(result)
    
    def test_verify_access_code_no_code(self):
        """Test verifying when no access code is set"""
        # Ensure no access code is set
        self.consultation.access_code = None
        self.consultation.access_code_expires = None
        self.consultation.save()
        
        # Call the method under test
        result = ConsultationAuthService.verify_access_code(self.consultation, '123456')
        
        # Verify the result
        self.assertFalse(result)
    
    @patch('telemedicine.services.consultation_auth_service.send_mail')
    def test_send_access_code_error_handling(self, mock_send_mail):
        """Test error handling when sending access code"""
        # Configure the mock to simulate failure
        mock_send_mail.side_effect = Exception('SMTP server error')
        
        # Call the method under test
        result = ConsultationAuthService.send_access_code(self.consultation)
        
        # Verify the result indicates failure
        self.assertFalse(result)
    
    def test_generate_access_code(self):
        """Test generating unique access codes"""
        # Generate multiple codes and verify uniqueness
        codes = [ConsultationAuthService._generate_access_code() for _ in range(100)]
        
        # Verify all codes are 6 digits
        for code in codes:
            self.assertTrue(re.match(r'^\d{6}$', code))
        
        # Verify uniqueness (with high probability)
        self.assertTrue(len(set(codes)) > 90)  # Allow some small chance of collision
