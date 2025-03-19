# users/tests/test_models.py
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from users.models import (
    PatientProfile, ProviderProfile, PharmcoProfile, 
    InsurerProfile, UserSession
)

User = get_user_model()

class CustomUserModelTest(TestCase):
    """Test cases for the CustomUser model"""
    
    def setUp(self):
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'securepassword123',
            'first_name': 'Test',
            'last_name': 'User',
            'role': 'patient'
        }
        self.user = User.objects.create_user(**self.user_data)
    
    def test_user_creation(self):
        """Test user creation with basic fields"""
        self.assertEqual(self.user.username, self.user_data['username'])
        self.assertEqual(self.user.email, self.user_data['email'])
        self.assertEqual(self.user.first_name, self.user_data['first_name'])
        self.assertEqual(self.user.last_name, self.user_data['last_name'])
        self.assertEqual(self.user.role, self.user_data['role'])
        self.assertFalse(self.user.two_factor_enabled)
        self.assertFalse(self.user.account_locked)
        self.assertEqual(self.user.failed_login_attempts, 0)
    
    def test_user_str_method(self):
        """Test the string representation of a user"""
        expected_str = f"{self.user.username} (Patient)"
        self.assertEqual(str(self.user), expected_str)
    
    def test_lock_account(self):
        """Test locking a user account"""
        self.user.lock_account(duration_minutes=15)
        self.assertTrue(self.user.account_locked)
        self.assertIsNotNone(self.user.locked_until)
        # Check that the lock is set for approximately 15 minutes in the future
        lock_duration = self.user.locked_until - timezone.now()
        self.assertGreater(lock_duration.total_seconds(), 14*60)  # At least 14 minutes
        self.assertLess(lock_duration.total_seconds(), 16*60)     # At most 16 minutes
    
    def test_unlock_account(self):
        """Test unlocking a user account"""
        # First lock the account
        self.user.lock_account()
        self.assertTrue(self.user.account_locked)
        
        # Then unlock it
        self.user.unlock_account()
        self.assertFalse(self.user.account_locked)
        self.assertEqual(self.user.failed_login_attempts, 0)
        self.assertIsNone(self.user.locked_until)
    
    def test_increment_failed_login(self):
        """Test incrementing failed login attempts"""
        self.assertEqual(self.user.failed_login_attempts, 0)
        
        # Increment a few times below the threshold
        for i in range(1, 5):
            self.user.increment_failed_login()
            self.assertEqual(self.user.failed_login_attempts, i)
            self.assertFalse(self.user.account_locked)
        
        # The 5th attempt should lock the account
        self.user.increment_failed_login()
        self.assertEqual(self.user.failed_login_attempts, 5)
        self.assertTrue(self.user.account_locked)
    
    def test_reset_failed_login(self):
        """Test resetting failed login attempts"""
        # Set some failed attempts
        self.user.failed_login_attempts = 3
        self.user.save()
        
        # Reset them
        self.user.reset_failed_login()
        self.assertEqual(self.user.failed_login_attempts, 0)
    
    def test_record_login(self):
        """Test recording a login"""
        test_ip = '192.168.1.1'
        self.user.record_login(test_ip)
        
        # Check the fields were updated
        self.assertEqual(self.user.last_login_ip, test_ip)
        self.assertIsNotNone(self.user.last_login)
        self.assertEqual(self.user.failed_login_attempts, 0)
    
    def test_accept_terms(self):
        """Test accepting terms and conditions"""
        self.assertFalse(self.user.terms_accepted)
        self.assertIsNone(self.user.terms_accepted_date)
        
        self.user.accept_terms()
        
        self.assertTrue(self.user.terms_accepted)
        self.assertIsNotNone(self.user.terms_accepted_date)
    
    def test_change_password(self):
        """Test changing password"""
        new_password = 'newSecurePassword456'
        old_password_hash = self.user.password
        
        self.user.change_password(new_password)
        
        # Check password was changed
        self.assertNotEqual(self.user.password, old_password_hash)
        self.assertTrue(self.user.check_password(new_password))
        self.assertIsNotNone(self.user.last_password_change)
    
    def test_requires_password_change(self):
        """Test password change requirement based on age"""
        # New user without a password change date should require change
        self.assertTrue(self.user.requires_password_change())
        
        # Set a recent password change
        self.user.last_password_change = timezone.now()
        self.user.save()
        self.assertFalse(self.user.requires_password_change(days=90))
        
        # Set an old password change (95 days ago)
        self.user.last_password_change = timezone.now() - timezone.timedelta(days=95)
        self.user.save()
        self.assertTrue(self.user.requires_password_change(days=90))


class ProfileModelsTest(TestCase):
    """Test cases for the profile models"""
    
    def setUp(self):
        # Create users with different roles
        self.patient_user = User.objects.create_user(
            username='patient',
            email='patient@example.com',
            password='password123',
            role='patient'
        )
        
        self.provider_user = User.objects.create_user(
            username='provider',
            email='provider@example.com',
            password='password123',
            role='provider'
        )
        
        self.pharmco_user = User.objects.create_user(
            username='pharmco',
            email='pharmco@example.com',
            password='password123',
            role='pharmco'
        )
        
        self.insurer_user = User.objects.create_user(
            username='insurer',
            email='insurer@example.com',
            password='password123',
            role='insurer'
        )
    
    def test_patient_profile_creation(self):
        """Test patient profile is created and can be accessed"""
        # Update the profile with some data
        profile = PatientProfile.objects.get(user=self.patient_user)
        profile.medical_id = "MED12345"
        profile.blood_type = "O+"
        profile.save()
        
        # Refresh from database and check
        self.patient_user.refresh_from_db()
        self.assertEqual(self.patient_user.patient_profile.medical_id, "MED12345")
        self.assertEqual(self.patient_user.patient_profile.blood_type, "O+")
        self.assertEqual(str(profile), f"Patient Profile: {self.patient_user.username}")
    
    def test_provider_profile_creation(self):
        """Test provider profile is created and can be accessed"""
        # Update the profile with some data
        profile = ProviderProfile.objects.get(user=self.provider_user)
        profile.license_number = "LIC789"
        profile.specialty = "Cardiology"
        profile.save()
        
        # Refresh from database and check
        self.provider_user.refresh_from_db()
        self.assertEqual(self.provider_user.provider_profile.license_number, "LIC789")
        self.assertEqual(self.provider_user.provider_profile.specialty, "Cardiology")
        self.assertEqual(str(profile), f"Provider Profile: {self.provider_user.username}")
    
    def test_pharmco_profile_creation(self):
        """Test pharmacy profile is created and can be accessed"""
        # Update the profile with some data
        profile = PharmcoProfile.objects.get(user=self.pharmco_user)
        profile.pharmacy_name = "Healthcare Pharmacy"
        profile.pharmacy_license = "PL456"
        profile.does_delivery = True
        profile.save()
        
        # Refresh from database and check
        self.pharmco_user.refresh_from_db()
        self.assertEqual(self.pharmco_user.pharmco_profile.pharmacy_name, "Healthcare Pharmacy")
        self.assertEqual(self.pharmco_user.pharmco_profile.pharmacy_license, "PL456")
        self.assertTrue(self.pharmco_user.pharmco_profile.does_delivery)
        self.assertEqual(str(profile), f"Pharmacy Profile: {self.pharmco_user.username}")
    
    def test_insurer_profile_creation(self):
        """Test insurer profile is created and can be accessed"""
        # Update the profile with some data
        profile = InsurerProfile.objects.get(user=self.insurer_user)
        profile.company_name = "Health Insurance Co."
        profile.policy_prefix = "HIC"
        profile.save()
        
        # Refresh from database and check
        self.insurer_user.refresh_from_db()
        self.assertEqual(self.insurer_user.insurer_profile.company_name, "Health Insurance Co.")
        self.assertEqual(self.insurer_user.insurer_profile.policy_prefix, "HIC")
        self.assertEqual(str(profile), f"Insurer Profile: {self.insurer_user.username}")


class UserSessionTest(TestCase):
    """Test cases for the UserSession model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123',
            role='patient'
        )
        
        self.session = UserSession.objects.create(
            user=self.user,
            session_key='testkey123',
            ip_address='192.168.1.100',
            user_agent='Test Browser 1.0',
            login_time=timezone.now()
        )
    
    def test_user_session_creation(self):
        """Test session is created correctly"""
        self.assertEqual(self.session.user, self.user)
        self.assertEqual(self.session.session_key, 'testkey123')
        self.assertEqual(self.session.ip_address, '192.168.1.100')
        self.assertEqual(self.session.user_agent, 'Test Browser 1.0')
        self.assertIsNotNone(self.session.login_time)
        self.assertIsNone(self.session.logout_time)
        self.assertFalse(self.session.was_forced_logout)
    
    def test_user_session_str(self):
        """Test the string representation of a session"""
        expected_str = f"Session: {self.user.username} - {self.session.login_time}"
        self.assertEqual(str(self.session), expected_str)
