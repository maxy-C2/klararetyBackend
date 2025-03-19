# healthcare/apps.py
from django.apps import AppConfig
import logging


class HealthcareConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'healthcare'
    verbose_name = 'Electronic Health Records'
    
    def ready(self):
        """
        Initialize application components:
        1. Register signals
        2. Set up model methods
        3. Configure audit logging
        """
        import healthcare.signals
        # Set up logging
        logger = logging.getLogger('healthcare')
        logger.setLevel(logging.INFO)
