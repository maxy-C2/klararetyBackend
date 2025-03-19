# healthcare/tests/test_services/test_document_service.py
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.core.files.storage import default_storage
from healthcare.services.document_service import DocumentService
import os
import shutil

class DocumentServiceTest(TestCase):
    """Test suite for the DocumentService"""
    
    def setUp(self):
        """Set up test data"""
        # Create a test file
        self.test_content = b'Test document content'
        self.test_file = SimpleUploadedFile(
            "test_document.txt",
            self.test_content
        )
        
        # Create a test directory for files
        self.test_dir = os.path.join(settings.MEDIA_ROOT, 'test_documents')
        if not os.path.exists(self.test_dir):
            os.makedirs(self.test_dir)
        
        # Define paths for testing
        self.test_path = 'test_documents/test_doc.txt'
    
    def tearDown(self):
        """Clean up after tests"""
        # Remove test files
        if default_storage.exists(self.test_path):
            default_storage.delete(self.test_path)
        
        # Remove test directory
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_store_document(self):
        """Test storing a document"""
        # Store the test file
        path = DocumentService.store_document(self.test_file, self.test_path)
        
        # Verify the file was stored
        self.assertTrue(default_storage.exists(path))
        
        # Verify the content
        with default_storage.open(path, 'rb') as f:
            content = f.read()
            self.assertEqual(content, self.test_content)
    
    def test_get_document_url(self):
        """Test getting the URL for a document"""
        # First store a document
        path = DocumentService.store_document(self.test_file, self.test_path)
        
        # Get the URL
        url = DocumentService.get_document_url(path)
        
        # Verify the URL format - it should include the path
        self.assertIn(path, url)
    
    def test_delete_document(self):
        """Test deleting a document"""
        # First store a document
        path = DocumentService.store_document(self.test_file, self.test_path)
        
        # Verify it exists
        self.assertTrue(default_storage.exists(path))
        
        # Delete the document
        result = DocumentService.delete_document(path)
        
        # Verify deletion was successful
        self.assertTrue(result)
        self.assertFalse(default_storage.exists(path))
    
    def test_delete_nonexistent_document(self):
        """Test deleting a document that doesn't exist"""
        # Try to delete a non-existent document
        result = DocumentService.delete_document('nonexistent/path.txt')
        
        # Should return False but not raise an exception
        self.assertFalse(result)
