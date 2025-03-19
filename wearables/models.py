from django.db import models
from django.conf import settings
from django.utils import timezone

class WithingsProfile(models.Model):
    """
    Stores Withings OAuth tokens and other integration details for each user.
    
    This model maintains the connection between a Klararety user and their
    Withings account, storing necessary OAuth credentials and timestamps.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='withings_profile',
        help_text="The user this Withings profile belongs to"
    )
    access_token = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        help_text="OAuth access token for Withings API"
    )
    refresh_token = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        help_text="OAuth refresh token for renewing access"
    )
    token_expires_at = models.DateTimeField(
        blank=True, 
        null=True,
        help_text="Timestamp when the access token expires"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this profile was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this profile was last updated"
    )

    def __str__(self):
        return f"Withings Profile for {self.user.username}"
    
    def is_connected(self):
        """
        Determines if this profile has a valid connection to Withings.
        
        Returns:
            bool: True if profile has valid credentials, False otherwise
        """
        if not self.access_token or not self.refresh_token:
            return False
        if not self.token_expires_at:
            return False
        return self.token_expires_at > timezone.now()
    
    class Meta:
        verbose_name = "Withings Profile"
        verbose_name_plural = "Withings Profiles"


class WithingsMeasurement(models.Model):
    """
    Stores health measurements from Withings devices.
    
    This model stores various health metrics such as heart rate, steps,
    weight, and other data collected from Withings devices.
    """
    withings_profile = models.ForeignKey(
        WithingsProfile,
        on_delete=models.CASCADE,
        related_name='measurements',
        help_text="The Withings profile this measurement belongs to"
    )
    measurement_type = models.CharField(
        max_length=50,
        help_text="Type of measurement (e.g. 'heart_rate', 'steps', 'weight')"
    )
    value = models.FloatField(
        help_text="The numerical value of the measurement"
    )
    unit = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text="Unit of measurement (e.g. 'bpm', 'steps', 'kg')"
    )
    measured_at = models.DateTimeField(
        default=timezone.now,
        help_text="When this measurement was taken by the device"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this record was created in our system"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this record was last updated"
    )

    def __str__(self):
        return f"{self.measurement_type} = {self.value} ({self.unit})"
    
    class Meta:
        verbose_name = "Withings Measurement"
        verbose_name_plural = "Withings Measurements"
        indexes = [
            models.Index(fields=['withings_profile', 'measurement_type']),
            models.Index(fields=['measured_at']),
        ]
        ordering = ['-measured_at']
