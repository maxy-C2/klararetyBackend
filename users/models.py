# users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class CustomUser(AbstractUser):
    """
    Extended User model with role-based authentication and security features
    """
    ROLE_CHOICES = [
        ('patient', 'Patient'),
        ('provider', 'Provider'),
        ('pharmco', 'Pharmacy'),
        ('insurer', 'Insurer'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='patient')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    
    # Two-factor authentication fields
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=32, blank=True, null=True)
    
    # Security fields
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    last_password_change = models.DateTimeField(blank=True, null=True)
    account_locked = models.BooleanField(default=False)
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(blank=True, null=True)
    
    # Profile completion flag
    profile_completed = models.BooleanField(default=False)
    
    # Terms and privacy policy agreement
    terms_accepted = models.BooleanField(default=False)
    terms_accepted_date = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def lock_account(self, duration_minutes=30):
        """Lock the account for the specified duration"""
        self.account_locked = True
        self.locked_until = timezone.now() + timezone.timedelta(minutes=duration_minutes)
        self.save(update_fields=['account_locked', 'locked_until'])
    
    def unlock_account(self):
        """Unlock the account"""
        self.account_locked = False
        self.failed_login_attempts = 0
        self.locked_until = None
        self.save(update_fields=['account_locked', 'failed_login_attempts', 'locked_until'])
    
    def increment_failed_login(self):
        """Increment failed login attempts and lock if threshold reached"""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:  # Lock after 5 failed attempts
            self.lock_account()
        else:
            self.save(update_fields=['failed_login_attempts'])
    
    def reset_failed_login(self):
        """Reset failed login attempts after successful login"""
        self.failed_login_attempts = 0
        self.save(update_fields=['failed_login_attempts'])
    
    def record_login(self, ip_address):
        """Record successful login with IP address"""
        self.last_login = timezone.now()
        self.last_login_ip = ip_address
        self.reset_failed_login()
    
    def accept_terms(self):
        """Record acceptance of terms and conditions"""
        self.terms_accepted = True
        self.terms_accepted_date = timezone.now()
        self.save(update_fields=['terms_accepted', 'terms_accepted_date'])
    
    def change_password(self, new_password):
        """Change user password and record timestamp"""
        self.set_password(new_password)
        self.last_password_change = timezone.now()
        self.save(update_fields=['password', 'last_password_change'])
    
    def requires_password_change(self, days=90):
        """Check if password change is required based on age"""
        if not self.last_password_change:
            return True
        
        max_age = timezone.timedelta(days=days)
        return timezone.now() - self.last_password_change > max_age


class PatientProfile(models.Model):
    """Extended profile information for patient users"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='patient_profile')
    medical_id = models.CharField(max_length=50, blank=True, null=True)
    emergency_contact_name = models.CharField(max_length=255, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True, null=True)
    emergency_contact_relationship = models.CharField(max_length=50, blank=True, null=True)
    blood_type = models.CharField(max_length=10, blank=True, null=True)
    allergies = models.TextField(blank=True, null=True)
    medical_conditions = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Patient Profile: {self.user.username}"


class ProviderProfile(models.Model):
    """Extended profile information for healthcare provider users"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='provider_profile')
    license_number = models.CharField(max_length=50, blank=True, null=True)
    specialty = models.CharField(max_length=100, blank=True, null=True)
    practice_name = models.CharField(max_length=255, blank=True, null=True)
    practice_address = models.TextField(blank=True, null=True)
    years_of_experience = models.PositiveSmallIntegerField(default=0)
    npi_number = models.CharField(max_length=50, blank=True, null=True)  # National Provider Identifier
    
    def __str__(self):
        return f"Provider Profile: {self.user.username}"


class PharmcoProfile(models.Model):
    """Extended profile information for pharmacy users"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='pharmco_profile')
    pharmacy_name = models.CharField(max_length=255, blank=True, null=True)
    pharmacy_address = models.TextField(blank=True, null=True)
    pharmacy_license = models.CharField(max_length=50, blank=True, null=True)
    pharmacy_hours = models.TextField(blank=True, null=True)
    does_delivery = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Pharmacy Profile: {self.user.username}"


class InsurerProfile(models.Model):
    """Extended profile information for insurance provider users"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='insurer_profile')
    company_name = models.CharField(max_length=255, blank=True, null=True)
    company_address = models.TextField(blank=True, null=True)
    support_phone = models.CharField(max_length=15, blank=True, null=True)
    policy_prefix = models.CharField(max_length=10, blank=True, null=True)
    
    def __str__(self):
        return f"Insurer Profile: {self.user.username}"


class UserSession(models.Model):
    """Tracks user login sessions for security and audit purposes"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    location = models.CharField(max_length=255, blank=True, null=True)  # Optional geolocation
    login_time = models.DateTimeField(auto_now_add=True)
    logout_time = models.DateTimeField(blank=True, null=True)
    was_forced_logout = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-login_time']
    
    def __str__(self):
        return f"Session: {self.user.username} - {self.login_time}"
