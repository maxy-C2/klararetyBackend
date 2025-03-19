# telemedicine/tests/integration/test_appointment_methods.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory
from datetime import time, timedelta, datetime
from unittest.mock import patch, MagicMock

from telemedicine.models import (
    Appointment, ProviderAvailability, ProviderTimeOff
)
from telemedicine.views import AppointmentViewSet

User = get_user_model()

class AppointmentMethodsTests(TestCase):
    """Tests for the internal methods of AppointmentViewSet"""
    
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
        
        # Setup provider availability for multiple days
        self.now = timezone.now()
        days_of_week = [0, 1, 2, 3, 4]  # Monday through Friday
        
        for day in days_of_week:
            ProviderAvailability.objects.create(
                provider=self.provider,
                day_of_week=day,
                start_time=time(9, 0),  # 9:00 AM
                end_time=time(17, 0),  # 5:00 PM
                is_available=True
            )
        
        # Create a test appointment
        tomorrow = self.now + timedelta(days=1)
        tomorrow = timezone.make_aware(datetime.combine(tomorrow.date(), time(10, 0)))
        
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            provider=self.provider,
            scheduled_time=tomorrow,
            end_time=tomorrow + timedelta(hours=1),
            reason='Test appointment',
            appointment_type='video_consultation'
        )
        
        # Setup API client and factory
        self.client = APIClient()
        self.factory = APIRequestFactory()
        
        # Create viewset instance
        self.viewset = AppointmentViewSet()
    
    def test_check_provider_availability_within_schedule(self):
        """Test availability check when time is within provider's schedule"""
        # Time within schedule (Tuesday at 11 AM)
        tuesday = self.now + timedelta(days=(1 - self.now.weekday()) % 7)  # Next Tuesday
        tuesday = timezone.make_aware(datetime.combine(tuesday.date(), time(11, 0)))
        end_time = tuesday + timedelta(hours=1)
        
        # Call the method under test
        result = self.viewset._check_provider_availability(
            self.provider, tuesday, end_time
        )
        
        # Verify the result
        self.assertTrue(result)
    
    def test_check_provider_availability_outside_schedule(self):
        """Test availability check when time is outside provider's schedule"""
        # Time outside schedule (Tuesday at 8 AM - before start time)
        tuesday = self.now + timedelta(days=(1 - self.now.weekday()) % 7)  # Next Tuesday
        tuesday = timezone.make_aware(datetime.combine(tuesday.date(), time(8, 0)))
        end_time = tuesday + timedelta(hours=1)
        
        # Call the method under test
        result = self.viewset._check_provider_availability(
            self.provider, tuesday, end_time
        )
        
        # Verify the result
        self.assertFalse(result)
        
        # Time outside schedule (Tuesday at 5 PM - after end time)
        tuesday = timezone.make_aware(datetime.combine(tuesday.date(), time(17, 0)))
        end_time = tuesday + timedelta(hours=1)
        
        # Call the method under test
        result = self.viewset._check_provider_availability(
            self.provider, tuesday, end_time
        )
        
        # Verify the result
        self.assertFalse(result)
    
    def test_check_provider_availability_weekend(self):
        """Test availability check when time is on a weekend (no availability)"""
        # Time on Saturday (no availability)
        saturday = self.now + timedelta(days=(5 - self.now.weekday()) % 7)  # Next Saturday
        saturday = timezone.make_aware(datetime.combine(saturday.date(), time(10, 0)))
        end_time = saturday + timedelta(hours=1)
        
        # Call the method under test
        result = self.viewset._check_provider_availability(
            self.provider, saturday, end_time
        )
        
        # Verify the result
        self.assertFalse(result)
    
    def test_check_provider_availability_with_time_off(self):
        """Test availability check when provider has time off"""
        # Create time off for tomorrow
        tomorrow = self.now + timedelta(days=1)
        ProviderTimeOff.objects.create(
            provider=self.provider,
            start_date=timezone.make_aware(datetime.combine(tomorrow.date(), time(0, 0))),
            end_date=timezone.make_aware(datetime.combine(tomorrow.date(), time(23, 59))),
            reason='Day off'
        )
        
        # Time during time off
        test_time = timezone.make_aware(datetime.combine(tomorrow.date(), time(10, 0)))
        end_time = test_time + timedelta(hours=1)
        
        # Call the method under test
        result = self.viewset._check_provider_availability(
            self.provider, test_time, end_time
        )
        
        # Verify the result
        self.assertFalse(result)
    
    def test_check_provider_availability_with_existing_appointment(self):
        """Test availability check when provider has an existing appointment"""
        # Time that conflicts with existing appointment
        tomorrow = self.now + timedelta(days=1)
        test_time = timezone.make_aware(datetime.combine(tomorrow.date(), time(10, 30)))  # During existing appointment
        end_time = test_time + timedelta(hours=1)
        
        # Call the method under test
        result = self.viewset._check_provider_availability(
            self.provider, test_time, end_time
        )
        
        # Verify the result
        self.assertFalse(result)
        
        # Time that doesn't conflict
        test_time = timezone.make_aware(datetime.combine(tomorrow.date(), time(14, 0)))  # Later in the day
        end_time = test_time + timedelta(hours=1)
        
        # Call the method under test
        result = self.viewset._check_provider_availability(
            self.provider, test_time, end_time
        )
        
        # Verify the result
        self.assertTrue(result)
    
    def test_get_provider_available_slots_with_availability(self):
        """Test getting available slots when provider has availability"""
        # Next Monday (provider is available)
        monday = self.now + timedelta(days=(0 - self.now.weekday()) % 7 or 7)  # Next Monday
        monday_date = monday.date()
        
        # Call the method under test
        available_slots = self.viewset._get_provider_available_slots(
            self.provider, monday_date
        )
        
        # Verify the result
        self.assertTrue(len(available_slots) > 0)
        
        # Verify slot format
        first_slot = available_slots[0]
        self.assertIn('start', first_slot)
        self.assertIn('end', first_slot)
        
        # Verify slots are 30 minutes apart
        if len(available_slots) > 1:
            slot1_start = datetime.strptime(available_slots[0]['start'], '%H:%M').time()
            slot2_start = datetime.strptime(available_slots[1]['start'], '%H:%M').time()
            
            minutes_diff = (
                (slot2_start.hour - slot1_start.hour) * 60 +
                (slot2_start.minute - slot1_start.minute)
            )
            self.assertEqual(minutes_diff, 30)
    
    def test_get_provider_available_slots_with_time_off(self):
        """Test getting available slots when provider has time off"""
        # Create time off for next Monday
        monday = self.now + timedelta(days=(0 - self.now.weekday()) % 7 or 7)  # Next Monday
        monday_date = monday.date()
        
        ProviderTimeOff.objects.create(
            provider=self.provider,
            start_date=timezone.make_aware(datetime.combine(monday_date, time(0, 0))),
            end_date=timezone.make_aware(datetime.combine(monday_date, time(23, 59))),
            reason='Day off'
        )
        
        # Call the method under test
        available_slots = self.viewset._get_provider_available_slots(
            self.provider, monday_date
        )
        
        # Verify no slots are available
        self.assertEqual(len(available_slots), 0)
    
    def test_get_provider_available_slots_with_existing_appointments(self):
        """Test getting available slots when provider has existing appointments"""
        # Next Monday (provider is available)
        monday = self.now + timedelta(days=(0 - self.now.weekday()) % 7 or 7)  # Next Monday
        monday_date = monday.date()
        
        # Create an appointment for Monday at 10 AM
        monday_10am = timezone.make_aware(datetime.combine(monday_date, time(10, 0)))
        Appointment.objects.create(
            patient=self.patient,
            provider=self.provider,
            scheduled_time=monday_10am,
            end_time=monday_10am + timedelta(hours=1),
            reason='Monday appointment',
            appointment_type='video_consultation'
        )
        
        # Call the method under test
        available_slots = self.viewset._get_provider_available_slots(
            self.provider, monday_date
        )
        
        # Verify there are slots available
        self.assertTrue(len(available_slots) > 0)
        
        # Verify the 10:00 and 10:30 slots are not available (due to appointment)
        slot_times = [slot['start'] for slot in available_slots]
        self.assertNotIn('10:00', slot_times)
        self.assertNotIn('10:30', slot_times)
    
    def test_get_provider_available_slots_weekend(self):
        """Test getting available slots for weekend (no availability)"""
        # Next Saturday (no availability)
        saturday = self.now + timedelta(days=(5 - self.now.weekday()) % 7)  # Next Saturday
        saturday_date = saturday.date()
        
        # Call the method under test
        available_slots = self.viewset._get_provider_available_slots(
            self.provider, saturday_date
        )
        
        # Verify no slots are available
        self.assertEqual(len(available_slots), 0)
    
    def test_available_slots_api_endpoint(self):
        """Test the available slots API endpoint"""
        # Authenticate the client
        self.client.force_authenticate(user=self.patient)
        
        # Get next Monday's date
        monday = self.now + timedelta(days=(0 - self.now.weekday()) % 7 or 7)  # Next Monday
        monday_date = monday.date().isoformat()
        
        # Call the API endpoint
        response = self.client.get(
            f'/api/v1/telemedicine/appointments/available_slots/?provider={self.provider.id}&date={monday_date}'
        )
        
        # Verify the response
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.data) > 0)
    
    def test_available_slots_api_missing_params(self):
        """Test the available slots API endpoint with missing parameters"""
        # Authenticate the client
        self.client.force_authenticate(user=self.patient)
        
        # Call the API endpoint without provider
        response = self.client.get(
            f'/api/v1/telemedicine/appointments/available_slots/?date=2023-01-01'
        )
        
        # Verify the response
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)
        
        # Call the API endpoint without date
        response = self.client.get(
            f'/api/v1/telemedicine/appointments/available_slots/?provider={self.provider.id}'
        )
        
        # Verify the response
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)
    
    @patch('telemedicine.services.reminder_service.AppointmentReminderService')
    def test_send_reminders_endpoint(self, mock_reminder_service):
        """Test the send reminders API endpoint"""
        # Configure the mock
        mock_instance = mock_reminder_service.return_value
        mock_instance.get_upcoming_reminders.return_value = Appointment.objects.filter(id=self.appointment.id)
        mock_instance.send_reminder.return_value = True
        
        # Authenticate as admin
        admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass',
            is_staff=True
        )
        self.client.force_authenticate(user=admin)
        
        # Call the API endpoint
        response = self.client.post('/api/v1/telemedicine/appointments/send_reminders/')
        
        # Verify the response
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.data)
        self.assertIn('1', response.data['message'])  # 1 reminder sent
        
        # Verify the service was called
        mock_instance.get_upcoming_reminders.assert_called_once()
        mock_instance.send_reminder.assert_called_once_with(self.appointment)
    
    def test_send_reminders_permission_denied(self):
        """Test that non-admin users cannot send reminders"""
        # Authenticate as regular user
        self.client.force_authenticate(user=self.patient)
        
        # Call the API endpoint
        response = self.client.post('/api/v1/telemedicine/appointments/send_reminders/')
        
        # Verify the response
        self.assertEqual(response.status_code, 403)
        self.assertIn('error', response.data)
