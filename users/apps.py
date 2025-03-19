# users/apps.py
from django.apps import AppConfig

class UsersConfig(AppConfig):
    """
    Application configuration for the users app.
    
    This app handles user authentication, authorization, and profile management
    for different user roles (patients, providers, pharmacies, insurers).
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    
    def ready(self):
        """
        Import and register signal handlers when the app is ready.
        
        This ensures that the signals for automatic profile creation are
        connected when the app is initialized.
        """
        import users.signals  # noqa
