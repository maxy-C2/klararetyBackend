# telemedicine/tests/test_middleware.py
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.http import HttpResponse
import json
import logging
from unittest.mock import patch, MagicMock

from telemedicine.middleware import HIPAAComplianceMiddleware

User = get_user_model()

class HIPAAComplianceMiddlewareTests(TestCase):
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
        
        # Setup request factory
        self.factory = RequestFactory()
        
        # Setup middleware
        self.get_response_mock = MagicMock(return_value=HttpResponse(status=200))
        self.middleware = HIPAAComplianceMiddleware(self.get_response_mock)
    
    @patch('telemedicine.middleware.logger')
    def test_middleware_logs_patient_data_access(self, mock_logger):
        """Test that middleware logs access to patient data"""
        # Create a request
        request = self.factory.get('/api/v1/telemedicine/patient-profiles/123/')
        request.user = self.provider
        request.META = {
            'REMOTE_ADDR': '127.0.0.1',
            'HTTP_USER_AGENT': 'test-agent'
        }
        
        # Process the request through middleware
        response = self.middleware(request)
        
        # Check that the logger was called with patient data
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args[0][0]
        
        # Verify log contains expected information
        self.assertIn('HIPAA_ACCESS', log_call)
        self.assertIn('patient_id', log_call)
        
        # Extract JSON data from the log
        log_data = json.loads(log_call.replace('HIPAA_ACCESS: ', ''))
        self.assertEqual(log_data['user_id'], self.provider.id)
        self.assertEqual(log_data['username'], 'testprovider')
        self.assertEqual(log_data['patient_id'], '123')
    
    @patch('telemedicine.middleware.logger')
    def test_middleware_logs_appointments_access(self, mock_logger):
        """Test that middleware logs access to appointments"""
        # Create a request
        request = self.factory.get('/api/v1/telemedicine/appointments/456/')
        request.user = self.provider
        request.META = {
            'REMOTE_ADDR': '127.0.0.1',
            'HTTP_USER_AGENT': 'test-agent'
        }
        
        # Process the request through middleware
        response = self.middleware(request)
        
        # Check that the logger was called
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args[0][0]
        
        # Verify log contains expected information
        self.assertIn('HIPAA_ACCESS', log_call)
        
        # Extract JSON data from the log
        log_data = json.loads(log_call.replace('HIPAA_ACCESS: ', ''))
        self.assertEqual(log_data['path'], '/api/v1/telemedicine/appointments/456/')
    
    @patch('telemedicine.middleware.logger')
    def test_middleware_does_not_log_non_patient_data(self, mock_logger):
        """Test that middleware doesn't log access to non-patient data"""
        # Create a request to a non-patient data endpoint
        request = self.factory.get('/api/v1/telemedicine/availability/')
        request.user = self.provider
        request.META = {
            'REMOTE_ADDR': '127.0.0.1',
            'HTTP_USER_AGENT': 'test-agent'
        }
        
        # Process the request through middleware
        response = self.middleware(request)
        
        # Check that the logger was not called
        mock_logger.info.assert_not_called()
    
    @patch('telemedicine.middleware.logger')
    def test_middleware_does_not_log_unauthenticated_requests(self, mock_logger):
        """Test that middleware doesn't log unauthenticated requests"""
        # Create a request
        request = self.factory.get('/api/v1/telemedicine/patient-profiles/123/')
        request.user = MagicMock(is_authenticated=False)
        request.META = {
            'REMOTE_ADDR': '127.0.0.1',
            'HTTP_USER_AGENT': 'test-agent'
        }
        
        # Process the request through middleware
        response = self.middleware(request)
        
        # Check that the logger was not called
        mock_logger.info.assert_not_called()
    
    @patch('telemedicine.middleware.logger')
    def test_middleware_does_not_log_unsuccessful_requests(self, mock_logger):
        """Test that middleware doesn't log unsuccessful requests"""
        # Create a request
        request = self.factory.get('/api/v1/telemedicine/patient-profiles/123/')
        request.user = self.provider
        request.META = {
            'REMOTE_ADDR': '127.0.0.1',
            'HTTP_USER_AGENT': 'test-agent'
        }
        
        # Mock get_response to return a 404 response
        self.middleware.get_response = MagicMock(return_value=HttpResponse(status=404))
        
        # Process the request through middleware
        response = self.middleware(request)
        
        # Check that the logger was not called
        mock_logger.info.assert_not_called()
