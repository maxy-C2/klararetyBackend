# telemedicine/tests/unit/test_reminder_service.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest.mock import patch, MagicMock
from datetime import timedelta

from telemedicine.models import Appointment
from telemedicine.services.reminder_service import AppointmentReminderService
from telemedicine.services.email_service import EmailService

User = get_user_model()

class AppointmentReminderServiceTests(TestCase):
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
        
        # Current time
        self.now = timezone.now()
        
        # Create appointments with different reminder statuses
        # 1. Upcoming appointment that needs a reminder (tomorrow)
        self.appointment_due = Appointment.objects.create(
            patient=self.patient,
            provider=self.provider,
            scheduled_time=self.now + timedelta(days=1),
            end_time=self.now + timedelta(days=1, hours=1),
            reason='Due for reminder',
            appointment_type='video_consultation',
            send_reminder=True,
            reminder_sent=False
        )
        
        # 2. Upcoming appointment that already got a reminder
        self.appointment_reminded = Appointment.objects.create(
            patient=self.patient,
            provider=self.provider,
            scheduled_time=self.now + timedelta(days=2),
            end_time=self.now + timedelta(days=2, hours=1),
            reason='Already reminded',
            appointment_type='video_consultation',
            send_reminder=True,
            reminder_sent=True
        )
        
        # 3. Upcoming appointment with reminders disabled
        self.appointment_no_reminder = Appointment.objects.create(
            patient=self.patient,
            provider=self.provider,
            scheduled_time=self.now + timedelta(days=3),
            end_time=self.now + timedelta(days=3, hours=1),
            reason='No reminder needed',
            appointment_type='video_consultation',
            send_reminder=False,
            reminder_sent=False
        )
        
        # 4. Past appointment (should be ignored)
        self.appointment_past = Appointment.objects.create(
            patient=self.patient,
            provider=self.provider,
            scheduled_time=self.now - timedelta(days=1),
            end_time=self.now - timedelta(days=1, hours=1),
            reason='Past appointment',
            appointment_type='video_consultation',
            send_reminder=True,
            reminder_sent=False
        )
        
        # Initialize the reminder service
        self.reminder_service = AppointmentReminderService()
    
    def test_get_upcoming_reminders(self):
        """Test getting appointments that need reminders"""
        # Call the method under test
        reminders = self.reminder_service.get_upcoming_reminders()
        
        # Verify correct appointments are included
        self.assertEqual(reminders.count(), 1)
        self.assertEqual(reminders.first().id, self.appointment_due.id)
        
        # Verify excluded appointments
        for appointment in reminders:
            self.assertNotEqual(appointment.id, self.appointment_reminded.id)
            self.assertNotEqual(appointment.id, self.appointment_no_reminder.id)
            self.assertNotEqual(appointment.id, self.appointment_past.id)
    
    @patch.object(EmailService, 'send_appointment_reminder')
    def test_send_reminder(self, mock_send_reminder):
        """Test sending a reminder for an appointment"""
        # Configure the mock
        mock_send_reminder.return_value = True
        
        # Call the method under test
        result = self.reminder_service.send_reminder(self.appointment_due)
        
        # Verify the result
        self.assertTrue(result)
        
        # Verify EmailService was called
        mock_send_reminder.assert_called_once_with(self.appointment_due)
        
        # Verify appointment was updated
        self.appointment_due.refresh_from_db()
        self.assertTrue(self.appointment_due.reminder_sent)
    
    @patch.object(EmailService, 'send_appointment_reminder')
    def test_send_reminder_failure(self, mock_send_reminder):
        """Test handling email sending failure"""
        # Configure the mock to simulate failure
        mock_send_reminder.return_value = False
        
        # Call the method under test
        result = self.reminder_service.send_reminder(self.appointment_due)
        
        # Verify the result
        self.assertFalse(result)
        
        # Verify EmailService was called
        mock_send_reminder.assert_called_once_with(self.appointment_due)
        
        # Verify appointment was not updated
        self.appointment_due.refresh_from_db()
        self.assertFalse(self.appointment_due.reminder_sent)
    
    @patch.object(EmailService, 'send_appointment_reminder')
    def test_process_reminders(self, mock_send_reminder):
        """Test processing all reminders at once"""
        # Configure the mock
        mock_send_reminder.return_value = True
        
        # Call the method under test
        self.reminder_service.process_reminders()
        
        # Verify EmailService was called exactly once
        mock_send_reminder.assert_called_once_with(self.appointment_due)
        
        # Verify appointment was updated
        self.appointment_due.refresh_from_db()
        self.assertTrue(self.appointment_due.reminder_sent)
        
        # Other appointments should remain unchanged
        self.appointment_reminded.refresh_from_db()
        self.assertTrue(self.appointment_reminded.reminder_sent)  # Already reminded
        
        self.appointment_no_reminder.refresh_from_db()
        self.assertFalse(self.appointment_no_reminder.reminder_sent)  # No reminder enabled
        
        self.appointment_past.refresh_from_db()
        self.assertFalse(self.appointment_past.reminder_sent)  # Past appointment
    
    def test_reminders_with_custom_timeframe(self):
        """Test getting reminders with a custom timeframe"""
        # Create a custom reminder service with different reminder time
        custom_service = AppointmentReminderService(reminder_hours=48)  # 2 days ahead
        
        # Call the method under test
        reminders = custom_service.get_upcoming_reminders()
        
        # Now the appointment 2 days ahead should be due for reminder (ignoring the reminder_sent flag)
        self.assertEqual(reminders.count(), 1)
        self.assertEqual(reminders.first().id, self.appointment_reminded.id)
