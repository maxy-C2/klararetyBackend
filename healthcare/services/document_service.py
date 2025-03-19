# healthcare/services/document_service.py
import os
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class DocumentService:
    """Service for handling medical document operations"""
    
    @staticmethod
    def store_document(file, path):
        """
        Store a document securely with proper path structure
        
        Args:
            file: The file object to store
            path: The relative path to store the file under
            
        Returns:
            str: The path where the file was stored
        """
        try:
            # Make sure the path exists
            full_path = os.path.join(settings.MEDIA_ROOT, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Store the file
            filename = default_storage.save(path, ContentFile(file.read()))
            return filename
        except Exception as e:
            logger.error(f"Error storing document: {str(e)}")
            raise
    
    @staticmethod
    def get_document_url(path):
        """
        Get the URL for a document
        
        Args:
            path: The stored path of the document
            
        Returns:
            str: The URL to access the document
        """
        return default_storage.url(path)
    
    @staticmethod
    def delete_document(path):
        """
        Delete a document
        
        Args:
            path: The stored path of the document
            
        Returns:
            bool: True if deletion was successful
        """
        try:
            default_storage.delete(path)
            return True
        except Exception as e:
            logger.error(f"Error deleting document: {str(e)}")
            return False
