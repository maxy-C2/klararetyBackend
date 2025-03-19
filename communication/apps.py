# communication/apps.py
from django.apps import AppConfig

class CommunicationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'communication'
    
    def ready(self):
        # Import signals when app is ready
        import communication.signals
