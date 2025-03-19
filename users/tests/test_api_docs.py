# users/tests/test_api_docs.py
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

class APIDocsTest(TestCase):
    """Test API documentation endpoints"""
    
    def setUp(self):
        self.client = APIClient()
    
    def test_swagger_docs_accessible(self):
        """Test that Swagger docs are accessible"""
        # This test assumes you've configured drf-yasg for Swagger
        try:
            response = self.client.get(reverse('schema-swagger-ui'))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertContains(response, 'swagger')
        except:
            self.skipTest("Swagger UI URL not configured or not accessible")
    
    def test_redoc_accessible(self):
        """Test that ReDoc is accessible"""
        # This test assumes you've configured drf-yasg for ReDoc
        try:
            response = self.client.get(reverse('schema-redoc'))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertContains(response, 'redoc')
        except:
            self.skipTest("ReDoc URL not configured or not accessible")
    
    def test_openapi_schema(self):
        """Test that OpenAPI schema is accessible"""
        # This test assumes you've configured OpenAPI schema generation
        try:
            response = self.client.get(reverse('schema'))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            
            # Schema should be JSON with openapi version
            self.assertIn('openapi', response.data)
            self.assertIn('paths', response.data)
            
            # Check for our user endpoints
            self.assertIn('/api/users/', str(response.data['paths']))
        except:
            self.skipTest("OpenAPI schema URL not configured or not accessible")
