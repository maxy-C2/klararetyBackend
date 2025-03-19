# healthcare/tests/conftest.py
import os
import pytest
from django.conf import settings
from django.core.management import call_command

def pytest_addoption(parser):
    parser.addoption(
        "--run-integration", action="store_true", default=False, help="Run integration tests"
    )

def pytest_configure(config):
    """
    Configure pytest - set up test media files directory
    """
    # Create a test media directory for uploaded files if it doesn't exist
    test_media_root = os.path.join(settings.BASE_DIR, 'test_media')
    if not os.path.exists(test_media_root):
        os.makedirs(test_media_root)
    
    # Override media root for tests
    settings.MEDIA_ROOT = test_media_root

def pytest_collection_modifyitems(config, items):
    """
    Skip integration tests unless explicitly requested
    """
    if not config.getoption("--run-integration"):
        skip_integration = pytest.mark.skip(reason="Integration tests only run with --run-integration")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)

@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Load test fixtures for all tests
    """
    with django_db_blocker.unblock():
        # Load the fixtures
        call_command('loaddata', 'tests/fixtures/users.json')
        call_command('loaddata', 'tests/fixtures/medical_records.json')

@pytest.fixture
def admin_user(django_user_model):
    """Return the admin user"""
    return django_user_model.objects.get(username='admin')

@pytest.fixture
def provider_user(django_user_model):
    """Return a provider user"""
    return django_user_model.objects.get(username='drsmith')

@pytest.fixture
def provider2_user(django_user_model):
    """Return another provider user"""
    return django_user_model.objects.get(username='drjones')

@pytest.fixture
def patient_user(django_user_model):
    """Return a patient user"""
    return django_user_model.objects.get(username='patient1')

@pytest.fixture
def patient2_user(django_user_model):
    """Return another patient user"""
    return django_user_model.objects.get(username='patient2')

@pytest.fixture
def patient_record(db):
    """Return a patient's medical record"""
    from healthcare.models import MedicalRecord
    return MedicalRecord.objects.get(patient__username='patient1')

@pytest.fixture
def patient2_record(db):
    """Return another patient's medical record"""
    from healthcare.models import MedicalRecord
    return MedicalRecord.objects.get(patient__username='patient2')

@pytest.fixture
def api_client():
    """Return an API client"""
    from rest_framework.test import APIClient
    return APIClient()

@pytest.fixture
def admin_api_client(api_client, admin_user):
    """Return an API client authenticated as admin"""
    api_client.force_authenticate(user=admin_user)
    return api_client

@pytest.fixture
def provider_api_client(api_client, provider_user):
    """Return an API client authenticated as provider"""
    api_client.force_authenticate(user=provider_user)
    return api_client

@pytest.fixture
def patient_api_client(api_client, patient_user):
    """Return an API client authenticated as patient"""
    api_client.force_authenticate(user=patient_user)
    return api_client
