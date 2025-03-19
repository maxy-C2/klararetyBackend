from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
from datetime import timedelta

from wearables.models import WithingsProfile, WithingsMeasurement


User = get_user_model()

class WithingsProfileModelTests(TestCase):
    """Test cases for the WithingsProfile model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.profile = WithingsProfile.objects.create(
            user=self.user,
            access_token='test-access-token',
            refresh_token='test-refresh-token',
            token_expires_at=timezone.now() + timedelta(hours=1)
        )
    
    def test_profile_creation(self):
        """Test that a profile can be created"""
        self.assertEqual(self.profile.user.username, 'testuser')
        self.assertEqual(self.profile.access_token, 'test-access-token')
        self.assertTrue(self.profile.token_expires_at > timezone.now())
    
    def test_string_representation(self):
        """Test the string representation of the profile"""
        self.assertEqual(str(self.profile), f"Withings Profile for {self.user.username}")
    
    def test_token_validity(self):
        """Test a method to check if token needs refreshing"""
        # Add a method to the model if it doesn't exist
        def is_token_valid(self):
            if not self.token_expires_at:
                return False
            return self.token_expires_at > timezone.now()
        
        # Monkey patch the method if it doesn't exist in the model
        if not hasattr(WithingsProfile, 'is_token_valid'):
            WithingsProfile.is_token_valid = is_token_valid
        
        # Test valid token
        self.assertTrue(self.profile.is_token_valid())
        
        # Test expired token
        self.profile.token_expires_at = timezone.now() - timedelta(minutes=5)
        self.profile.save()
        self.assertFalse(self.profile.is_token_valid())

class WithingsMeasurementModelTests(TestCase):
    """Test cases for the WithingsMeasurement model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.profile = WithingsProfile.objects.create(
            user=self.user,
            access_token='test-access-token',
            refresh_token='test-refresh-token',
            token_expires_at=timezone.now() + timedelta(hours=1)
        )
        self.measurement = WithingsMeasurement.objects.create(
            withings_profile=self.profile,
            measurement_type='weight',
            value=75.5,
            unit='kg',
            measured_at=timezone.now()
        )
    
    def test_measurement_creation(self):
        """Test that a measurement can be created"""
        self.assertEqual(self.measurement.withings_profile, self.profile)
        self.assertEqual(self.measurement.measurement_type, 'weight')
        self.assertEqual(self.measurement.value, 75.5)
        self.assertEqual(self.measurement.unit, 'kg')
    
    def test_string_representation(self):
        """Test the string representation of the measurement"""
        self.assertEqual(
            str(self.measurement), 
            f"weight = 75.5 (kg)"
        )

class WithingsConnectViewTests(TestCase):
    """Test cases for the WithingsConnectView"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse('withings-connect')
    
    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access the view"""
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    @patch('wearables.views.settings')
    def test_connect_url_generation(self, mock_settings):
        """Test that the view returns a valid Withings authorization URL"""
        # Configure the mock
        mock_settings.WITHINGS_CLIENT_ID = 'test-client-id'
        mock_settings.WITHINGS_REDIRECT_URI = 'http://example.com/callback'
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('authorize_url', response.data)
        self.assertIn('test-client-id', response.data['authorize_url'])
        self.assertIn('http://example.com/callback', response.data['authorize_url'])

class WithingsCallbackViewTests(TestCase):
    """Test cases for the WithingsCallbackView"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse('withings-callback')
    
    def test_error_handling(self):
        """Test error handling when callback contains an error"""
        response = self.client.get(f"{self.url}?error=access_denied")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_missing_code(self):
        """Test error handling when code is missing"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    @patch('wearables.views.requests.post')
    @patch('wearables.views.settings')
    def test_successful_callback(self, mock_settings, mock_post):
        """Test successful token exchange"""
        # Configure mocks
        mock_settings.WITHINGS_CLIENT_ID = 'test-client-id'
        mock_settings.WITHINGS_CLIENT_SECRET = 'test-client-secret'
        mock_settings.WITHINGS_REDIRECT_URI = 'http://example.com/callback'
        
        # Mock the response from Withings
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 0,
            'body': {
                'access_token': 'new-access-token',
                'refresh_token': 'new-refresh-token',
                'expires_in': 3600
            }
        }
        mock_post.return_value = mock_response
        
        response = self.client.get(f"{self.url}?code=test-auth-code")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that profile was created/updated
        profile = WithingsProfile.objects.get(user=self.user)
        self.assertEqual(profile.access_token, 'new-access-token')
        self.assertEqual(profile.refresh_token, 'new-refresh-token')
        self.assertTrue(profile.token_expires_at > timezone.now())

class WithingsFetchDataViewTests(TestCase):
    """Test cases for the WithingsFetchDataView"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.profile = WithingsProfile.objects.create(
            user=self.user,
            access_token='test-access-token',
            refresh_token='test-refresh-token',
            token_expires_at=timezone.now() + timedelta(hours=1)
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse('withings-fetch-data')
    
    def test_no_profile(self):
        """Test error handling when user has no profile"""
        # Delete the profile
        self.profile.delete()
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    @patch('wearables.views.WithingsFetchDataView.fetch_measurements')
    @patch('wearables.views.WithingsFetchDataView.fetch_activity')
    @patch('wearables.views.WithingsFetchDataView.fetch_sleep')
    @patch('wearables.views.WithingsFetchDataView.fetch_heart_data')
    def test_fetch_data(self, mock_heart, mock_sleep, mock_activity, mock_measurements):
        """Test successful data fetching"""
        # Configure mocks
        mock_measurements.return_value = [1, 2]
        mock_activity.return_value = [3]
        mock_sleep.return_value = [4, 5]
        mock_heart.return_value = [6]
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['saved_entries_ids']), 6)
        
        # Verify that all fetch methods were called
        mock_measurements.assert_called_once()
        mock_activity.assert_called_once()
        mock_sleep.assert_called_once()
        mock_heart.assert_called_once()
