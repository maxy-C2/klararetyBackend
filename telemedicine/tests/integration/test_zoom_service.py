# telemedicine/tests/test_zoom_service.py
from django.test import TestCase
from django.utils import timezone
from django.test.utils import override_settings
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import jwt
import json
import time
import requests

from telemedicine.services.zoom_service import ZoomService

@override_settings(ZOOM_API_KEY='test_api_key', ZOOM_API_SECRET='test_api_secret')
class ZoomServiceTests(TestCase):
    def setUp(self):
        # Sample data for testing
        self.now = timezone.now()
        self.provider_email = 'provider@example.com'
        self.topic = 'Test Medical Consultation'
        self.duration_minutes = 60
        self.meeting_id = '123456789'
        
        # Mock response data
        self.mock_meeting_response = {
            'id': self.meeting_id,
            'topic': self.topic,
            'start_time': self.now.strftime('%Y-%m-%dT%H:%M:%S'),
            'duration': self.duration_minutes,
            'timezone': 'UTC',
            'password': 'test_password',
            'join_url': f'https://zoom.us/j/{self.meeting_id}',
            'start_url': f'https://zoom.us/s/{self.meeting_id}?zak=test_token'
        }
        
        # Create service instance
        self.zoom_service = ZoomService()
        
        # Expected base URL
        self.base_url = 'https://api.zoom.us/v2'
    
    def test_init(self):
        """Test initialization of ZoomService"""
        self.assertEqual(self.zoom_service.api_key, 'test_api_key')
        self.assertEqual(self.zoom_service.api_secret, 'test_api_secret')
        self.assertEqual(self.zoom_service.base_url, 'https://api.zoom.us/v2')
    
    def test_generate_token(self):
        """Test JWT token generation"""
        # Freeze time to make token predictable
        current_time = int(time.time())
        with patch('time.time', return_value=current_time):
            token = self.zoom_service.generate_token()
            
            # Decode and verify the token
            decoded = jwt.decode(token, 'test_api_secret', algorithms=['HS256'])
            self.assertEqual(decoded['iss'], 'test_api_key')
            self.assertEqual(decoded['exp'], current_time + 3600)  # Expires in 1 hour
    
    @patch('requests.post')
    def test_create_meeting(self, mock_post):
        """Test creating a Zoom meeting"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = self.mock_meeting_response
        mock_post.return_value = mock_response
        
        # Call the method under test
        result = self.zoom_service.create_meeting(
            topic=self.topic,
            start_time=self.now,
            duration_minutes=self.duration_minutes,
            provider_email=self.provider_email
        )
        
        # Verify the API call
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        
        # Check the URL
        expected_url = f'{self.base_url}/users/{self.provider_email}/meetings'
        self.assertEqual(args[0], expected_url)
        
        # Check authorization header
        self.assertIn('Authorization', kwargs['headers'])
        self.assertTrue(kwargs['headers']['Authorization'].startswith('Bearer '))
        
        # Check JSON data
        json_data = kwargs['json']
        self.assertEqual(json_data['topic'], self.topic)
        self.assertEqual(json_data['start_time'], self.now.strftime('%Y-%m-%dT%H:%M:%S'))
        self.assertEqual(json_data['duration'], self.duration_minutes)
        self.assertEqual(json_data['timezone'], 'UTC')
        self.assertEqual(json_data['schedule_for'], self.provider_email)
        
        # Check security settings (important for HIPAA)
        settings = json_data['settings']
        self.assertTrue(settings['waiting_room'])
        self.assertTrue(settings['meeting_authentication'])
        self.assertEqual(settings['encryption_type'], 'enhanced')
        
        # Verify result matches mock response
        self.assertEqual(result, self.mock_meeting_response)
    
    @patch('requests.post')
    def test_create_meeting_with_string_time(self, mock_post):
        """Test creating a meeting with a string time format"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = self.mock_meeting_response
        mock_post.return_value = mock_response
        
        # String time format
        time_str = '2023-01-15T14:30:00'
        
        # Call the method under test
        result = self.zoom_service.create_meeting(
            topic=self.topic,
            start_time=time_str,
            duration_minutes=self.duration_minutes,
            provider_email=self.provider_email
        )
        
        # Verify the API call passes the string as-is
        json_data = mock_post.call_args[1]['json']
        self.assertEqual(json_data['start_time'], time_str)
    
    @patch('requests.post')
    def test_create_meeting_failure(self, mock_post):
        """Test handling errors when creating a meeting"""
        # Setup mock response for an error
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = '{"code": 3000, "message": "Invalid request parameters"}'
        mock_post.return_value = mock_response
        
        # Call the method and expect an exception
        with self.assertRaises(Exception) as context:
            self.zoom_service.create_meeting(
                topic=self.topic,
                start_time=self.now,
                duration_minutes=self.duration_minutes,
                provider_email=self.provider_email
            )
        
        # Verify the exception contains the error message
        self.assertIn('Failed to create Zoom meeting', str(context.exception))
        self.assertIn('Invalid request parameters', str(context.exception))
    
    @patch('requests.patch')
    def test_update_meeting(self, mock_patch):
        """Test updating a Zoom meeting"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_patch.return_value = mock_response
        
        # New values for update
        new_topic = 'Updated Medical Consultation'
        new_time = self.now + timedelta(days=1)
        new_duration = 90
        
        # Call the method under test
        result = self.zoom_service.update_meeting(
            meeting_id=self.meeting_id,
            topic=new_topic,
            start_time=new_time,
            duration_minutes=new_duration
        )
        
        # Verify the API call
        mock_patch.assert_called_once()
        args, kwargs = mock_patch.call_args
        
        # Check the URL
        expected_url = f'{self.base_url}/meetings/{self.meeting_id}'
        self.assertEqual(args[0], expected_url)
        
        # Check JSON data
        json_data = kwargs['json']
        self.assertEqual(json_data['topic'], new_topic)
        self.assertEqual(json_data['start_time'], new_time.strftime('%Y-%m-%dT%H:%M:%S'))
        self.assertEqual(json_data['duration'], new_duration)
        
        # Verify result
        self.assertTrue(result)
    
    @patch('requests.patch')
    def test_update_meeting_partial(self, mock_patch):
        """Test updating only some fields of a meeting"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_patch.return_value = mock_response
        
        # Call the method with only topic
        result = self.zoom_service.update_meeting(
            meeting_id=self.meeting_id,
            topic='Just Update Topic'
        )
        
        # Verify the API call only includes topic
        json_data = mock_patch.call_args[1]['json']
        self.assertEqual(json_data, {'topic': 'Just Update Topic'})
        self.assertNotIn('start_time', json_data)
        self.assertNotIn('duration', json_data)
    
    @patch('requests.patch')
    def test_update_meeting_failure(self, mock_patch):
        """Test handling errors when updating a meeting"""
        # Setup mock response for an error
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = '{"code": 3001, "message": "Meeting not found"}'
        mock_patch.return_value = mock_response
        
        # Call the method and expect an exception
        with self.assertRaises(Exception) as context:
            self.zoom_service.update_meeting(
                meeting_id=self.meeting_id,
                topic='Updated Topic'
            )
        
        # Verify the exception contains the error message
        self.assertIn('Failed to update Zoom meeting', str(context.exception))
        self.assertIn('Meeting not found', str(context.exception))
    
    @patch('requests.delete')
    def test_delete_meeting(self, mock_delete):
        """Test deleting a Zoom meeting"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_delete.return_value = mock_response
        
        # Call the method under test
        result = self.zoom_service.delete_meeting(meeting_id=self.meeting_id)
        
        # Verify the API call
        mock_delete.assert_called_once()
        args, kwargs = mock_delete.call_args
        
        # Check the URL
        expected_url = f'{self.base_url}/meetings/{self.meeting_id}'
        self.assertEqual(args[0], expected_url)
        
        # Verify result
        self.assertTrue(result)
    
    @patch('requests.delete')
    def test_delete_meeting_failure(self, mock_delete):
        """Test handling errors when deleting a meeting"""
        # Setup mock response for an error
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = '{"code": 3002, "message": "Cannot delete this meeting"}'
        mock_delete.return_value = mock_response
        
        # Call the method and expect an exception
        with self.assertRaises(Exception) as context:
            self.zoom_service.delete_meeting(meeting_id=self.meeting_id)
        
        # Verify the exception contains the error message
        self.assertIn('Failed to delete Zoom meeting', str(context.exception))
        self.assertIn('Cannot delete this meeting', str(context.exception))
    
    @patch('requests.get')
    def test_get_meeting(self, mock_get):
        """Test getting meeting details"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_meeting_response
        mock_get.return_value = mock_response
        
        # Call the method under test
        result = self.zoom_service.get_meeting(meeting_id=self.meeting_id)
        
        # Verify the API call
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        
        # Check the URL
        expected_url = f'{self.base_url}/meetings/{self.meeting_id}'
        self.assertEqual(args[0], expected_url)
        
        # Verify result matches mock response
        self.assertEqual(result, self.mock_meeting_response)
    
    @patch('requests.get')
    def test_get_meeting_failure(self, mock_get):
        """Test handling errors when getting meeting details"""
        # Setup mock response for an error
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = '{"code": 3001, "message": "Meeting not found"}'
        mock_get.return_value = mock_response
        
        # Call the method and expect an exception
        with self.assertRaises(Exception) as context:
            self.zoom_service.get_meeting(meeting_id=self.meeting_id)
        
        # Verify the exception contains the error message
        self.assertIn('Failed to get Zoom meeting', str(context.exception))
        self.assertIn('Meeting not found', str(context.exception))
    
    def test_generate_password(self):
        """Test password generation for meetings"""
        # Generate passwords
        password1 = self.zoom_service._generate_password()
        password2 = self.zoom_service._generate_password()
        
        # Check the length (default is 10)
        self.assertEqual(len(password1), 10)
        
        # Check that passwords are different (random)
        self.assertNotEqual(password1, password2)
        
        # Check with custom length
        custom_length = 15
        password3 = self.zoom_service._generate_password(length=custom_length)
        self.assertEqual(len(password3), custom_length)
        
        # Check character composition (should contain various character types)
        def has_letters(s): return any(c.isalpha() for c in s)
        def has_digits(s): return any(c.isdigit() for c in s)
        def has_special(s): return any(c in '!@#$%^&*()' for c in s)
        
        # Generate a longer password to increase chances of all character types
        password = self.zoom_service._generate_password(length=30)
        self.assertTrue(has_letters(password), "Password should contain letters")
        self.assertTrue(has_digits(password), "Password should contain digits")
    
    @patch('requests.post')
    def test_zoom_error_handling_and_retry(self, mock_post):
        """Test error handling and retry logic for Zoom API calls"""
        # First call fails with a 500 error
        first_response = MagicMock()
        first_response.status_code = 500
        first_response.text = '{"code": 5000, "message": "Server error"}'
        
        # Second call succeeds
        second_response = MagicMock()
        second_response.status_code = 201
        second_response.json.return_value = self.mock_meeting_response
        
        # Mock post to return the error first, then success
        mock_post.side_effect = [first_response, second_response]
        
        # Configure the service with retry
        zoom_service = ZoomService(max_retries=2, retry_delay=0.1)
        
        # Call the method under test
        result = zoom_service.create_meeting(
            topic=self.topic,
            start_time=self.now,
            duration_minutes=self.duration_minutes,
            provider_email=self.provider_email
        )
        
        # Verify post was called twice
        self.assertEqual(mock_post.call_count, 2)
        
        # Verify result matches mock response
        self.assertEqual(result, self.mock_meeting_response)
