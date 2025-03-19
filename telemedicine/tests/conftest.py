# telemedicine/tests/conftest.py
"""
Fixtures for telemedicine application tests.

This module provides common fixtures that can be reused across different tests
to reduce duplication and improve maintainability.
"""
import pytest
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from telemedicine.models import (
    Appointment, Consultation, Prescription,
    Message, ProviderAvailability, ProviderTimeOff
)

User = get_user_model()

# ================= User fixtures =================

@pytest.fixture
def patient_user():
    """Create and return a test patient user"""
    return User.objects.create_user(
        username='testpatient',
        email='patient@example.com',
        password='testpass123',
        role='patient',
        first_name='Test',
        last_name='Patient'
    )

@pytest.fixture
def provider_user():
    """Create and return a test provider user"""
    return User.objects.create_user(
        username='testprovider',
        email='provider@example.com',
        password='testpass123',
        role='provider',
        first_name='Test',
        last_name='Provider'
    )

@pytest.fixture
def admin_user():
    """Create and return a test admin user"""
    return User.objects.create_user(
        username='testadmin',
        email='admin@example.com',
        password='testpass123',
        role='admin',
        is_staff=True,
        first_name='Test',
        last_name='Admin'
    )

@pytest.fixture
def pharmco_user():
    """Create and return a test pharmacy company user"""
    return User.objects.create_user(
        username='testpharmco',
        email='pharmacy@example.com',
        password='testpass123',
        role='pharmco',
        first_name='Test',
        last_name='Pharmacy'
    )

# ================= API Client fixtures =================

@pytest.fixture
def api_client():
    """Return an unauthenticated API client"""
    return APIClient()

@pytest.fixture
def patient_client(api_client, patient_user):
    """Return an API client authenticated as a patient"""
    api_client.force_authenticate(user=patient_user)
    return api_client

@pytest.fixture
def provider_client(api_client, provider_user):
    """Return an API client authenticated as a provider"""
    api_client.force_authenticate(user=provider_user)
    return api_client

@pytest.fixture
def admin_client(api_client, admin_user):
    """Return an API client authenticated as an admin"""
    api_client.force_authenticate(user=admin_user)
    return api_client

# ================= Model fixtures =================

@pytest.fixture
def future_time():
    """Return a datetime in the future (tomorrow at 10 AM)"""
    tomorrow = timezone.now() + timedelta(days=1)
    return tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

@pytest.fixture
def appointment(patient_user, provider_user, future_time):
    """Create and return a test appointment"""
    return Appointment.objects.create(
        patient=patient_user,
        provider=provider_user,
        scheduled_time=future_time,
        end_time=future_time + timedelta(hours=1),
        reason='Test appointment',
        appointment_type='video_consultation'
    )

@pytest.fixture
def consultation(appointment):
    """Create and return a test consultation"""
    return Consultation.objects.create(
        appointment=appointment,
        notes='Initial consultation',
        zoom_meeting_id='123456789',
        zoom_meeting_password='password123',
        zoom_join_url='https://zoom.us/j/123456789',
        zoom_start_url='https://zoom.us/s/123456789'
    )

@pytest.fixture
def prescription(consultation, pharmco_user):
    """Create and return a test prescription"""
    return Prescription.objects.create(
        consultation=consultation,
        medication_name='Test Medication',
        dosage='10mg',
        frequency='Once daily',
        duration='7 days',
        refills=0,
        notes='Take with food',
        pharmacy=pharmco_user
    )

@pytest.fixture
def message(patient_user, provider_user, appointment):
    """Create and return a test message"""
    return Message.objects.create(
        sender=patient_user,
        receiver=provider_user,
        appointment=appointment,
        content='Test message content'
    )

@pytest.fixture
def provider_availability(provider_user):
    """Create and return test provider availability for weekdays"""
    availability_slots = []
    
    # Create availability for weekdays (0=Monday to 4=Friday)
    for day in range(5):
        availability = ProviderAvailability.objects.create(
            provider=provider_user,
            day_of_week=day,
            start_time='09:00:00',
            end_time='17:00:00',
            is_available=True
        )
        availability_slots.append(availability)
    
    return availability_slots

@pytest.fixture
def provider_timeoff(provider_user, future_time):
    """Create and return test provider time off"""
    start_date = future_time + timedelta(days=7)  # One week from future_time
    end_date = start_date + timedelta(days=3)     # Three days off
    
    return ProviderTimeOff.objects.create(
        provider=provider_user,
        start_date=start_date,
        end_date=end_date,
        reason='Vacation'
    )
