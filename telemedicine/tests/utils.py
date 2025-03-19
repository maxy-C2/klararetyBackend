# telemedicine/tests/utils.py
"""
Utility functions and helper classes for telemedicine tests.

This module provides common utilities that can be used across different tests
to simplify test setup, assertions, and cleanup.
"""
import json
from datetime import time, datetime, timedelta
from django.utils import timezone
from unittest.mock import MagicMock

class MockResponse:
    """Mock response object for testing API calls"""
    
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code
        self.text = json.dumps(json_data)
    
    def json(self):
        return self.json_data

def get_auth_header(token):
    """Get authorization header for API requests"""
    return {'HTTP_AUTHORIZATION': f'Bearer {token}'}

def create_mock_zoom_meeting():
    """Create mock Zoom meeting data for testing"""
    return {
        'id': '123456789',
        'password': 'password123',
        'join_url': 'https://zoom.us/j/123456789',
        'start_url': 'https://zoom.us/s/123456789',
        'topic': 'Test Medical Consultation',
        'duration': 60,
        'timezone': 'UTC',
    }

def create_future_datetime(days_future=1, hour=10, minute=0):
    """Create a datetime in the future"""
    future = timezone.now() + timedelta(days=days_future)
    return timezone.make_aware(
        datetime.combine(
            future.date(),
            time(hour, minute)
        )
    )

def create_test_file(filename='test.pdf', content='Test content'):
    """Create a test file for document uploads"""
    from django.core.files.uploadedfile import SimpleUploadedFile
    return SimpleUploadedFile(
        name=filename,
        content=content.encode('utf-8'),
        content_type='application/pdf'
    )

def create_mock_email_service():
    """Create a mocked email service for testing"""
    mock_service = MagicMock()
    mock_service.send_appointment_confirmation.return_value = True
    mock_service.send_appointment_update.return_value = True
    mock_service.send_appointment_reminder.return_value = True
    mock_service.send_email_with_template.return_value = True
    return mock_service

def assert_appointment_status(test_case, appointment_id, expected_status):
    """Assert that an appointment has the expected status"""
    from telemedicine.models import Appointment
    appointment = Appointment.objects.get(id=appointment_id)
    test_case.assertEqual(appointment.status, expected_status)

def assert_zoom_meeting_created(test_case, mock_zoom):
    """Assert that a Zoom meeting was created with proper parameters"""
    mock_zoom.return_value.create_meeting.assert_called_once()
    call_args = mock_zoom.return_value.create_meeting.call_args[1]
    test_case.assertIn('topic', call_args)
    test_case.assertIn('start_time', call_args)
    test_case.assertIn('duration_minutes', call_args)
    test_case.assertIn('provider_email', call_args)

def assert_user_can_access(test_case, client, url, user):
    """Assert that a user can access a specific URL"""
    client.force_authenticate(user=user)
    response = client.get(url)
    test_case.assertEqual(response.status_code, 200)

def assert_user_cannot_access(test_case, client, url, user):
    """Assert that a user cannot access a specific URL"""
    client.force_authenticate(user=user)
    response = client.get(url)
    test_case.assertIn(response.status_code, [401, 403, 404])
