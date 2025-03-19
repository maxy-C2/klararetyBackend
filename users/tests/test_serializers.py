# users/tests/test_serializers.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError
from users.models import (
    PatientProfile, ProviderProfile, PharmcoProfile, InsurerProfile, UserSession
)
from users.serializers import (
    CustomUserSerializer, UserDetailSerializer, UserRegistrationSerializer,
    PatientProfileSerializer, ProviderProfileSerializer,
    PharmcoProfileSerializer, InsurerProfileSerializer,
    PasswordChangeSerializer
)

User = get_user_model()

class CustomUserSerializerTest(TestCase):
    """Test cases for the CustomUserSerializer"""
    
    def setUp(self):
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'securepassword123',
            'first_name': 'Test',
            'last_name': 'User',
            'role': 'patient',
            'phone_number': '555-123-4567',
            'date_of_birth': '1990-01-01'
        }
        self.user = User.objects.create_user(**self.user_data)
        self.serializer = CustomUserSerializer(instance=self.user)
    
    def test_contains_expected_fields(self):
        """Test the serializer contains the expected fields"""
        data = self.serializer.data
        expected_fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'role', 'role_display', 'phone_number', 'date_of_birth',
            'date_joined', 'last_login', 'two_factor_enabled',
            'profile_completed'
        ]
        self.assertEqual(set(data.keys()), set(expected_fields))
    
    def test_role_display_field(self):
        """Test the role_display field works correctly"""
        data = self.serializer.data
        self.assertEqual(data['role'], 'patient')
        self.assertEqual(data['role_display'], 'Patient')


class UserDetailSerializerTest(TestCase):
    """Test cases for the UserDetailSerializer"""
    
    def setUp(self):
        # Create a patient user
        self.patient_user = User.objects.create_user(
            username='patient',
            email='patient@example.com',
            password='password123',
            role='patient'
        )
        
        # Fill out patient profile
        patient_profile = PatientProfile.objects.get(user=self.patient_user)
        patient_profile.medical_id = "MED12345"
        patient_profile.blood_type = "A+"
        patient_profile.save()
        
        self.serializer = UserDetailSerializer(instance=self.patient_user)
    
    def test_includes_profile_data(self):
        """Test that profile data is included in the serialized output"""
        data = self.serializer.data
        
        # Check for patient profile
        self.assertIn('patient_profile', data)
        self.assertEqual(data['patient_profile']['medical_id'], 'MED12345')
        self.assertEqual(data['patient_profile']['blood_type'], 'A+')
        
        # Other profiles should be present but null
        self.assertIn('provider_profile', data)
        self.assertIsNone(data['provider_profile'])
        self.assertIn('pharmco_profile', data)
        self.assertIsNone(data['pharmco_profile'])
        self.assertIn('insurer_profile', data)
        self.assertIsNone(data['insurer_profile'])
    
    def test_includes_recent_sessions(self):
        """Test that recent user sessions are included"""
        # Create a few sessions
        UserSession.objects.create(
            user=self.patient_user,
            session_key='session1',
            ip_address='192.168.1.1',
            user_agent='Test Browser 1.0'
        )
        UserSession.objects.create(
            user=self.patient_user,
            session_key='session2',
            ip_address='192.168.1.2',
            user_agent='Test Browser 2.0'
        )
        
        # Get fresh serialized data
        serializer = UserDetailSerializer(instance=self.patient_user)
        data = serializer.data
        
        # Check for sessions
        self.assertIn('recent_sessions', data)
        self.assertEqual(len(data['recent_sessions']), 2)
        self.assertEqual(data['recent_sessions'][0]['ip_address'], '192.168.1.2')  # Most recent first
        self.assertEqual(data['recent_sessions'][1]['ip_address'], '192.168.1.1')


class UserRegistrationSerializerTest(TestCase):
    """Test cases for the UserRegistrationSerializer"""
    
    def setUp(self):
        self.valid_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!',
            'first_name': 'New',
            'last_name': 'User',
            'role': 'patient',
            'terms_accepted': True
        }
    
    def test_validate_valid_data(self):
        """Test validation with valid data"""
        serializer = UserRegistrationSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
    
    def test_validate_password_mismatch(self):
        """Test validation with mismatched passwords"""
        data = self.valid_data.copy()
        data['password_confirm'] = 'DifferentPassword456!'
        
        serializer = UserRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password_confirm', serializer.errors)
    
    def test_validate_terms_not_accepted(self):
        """Test validation when terms are not accepted"""
        data = self.valid_data.copy()
        data['terms_accepted'] = False
        
        serializer = UserRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('terms_accepted', serializer.errors)
    
    def test_create_user(self):
        """Test creating a user from valid data"""
        serializer = UserRegistrationSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        
        user = serializer.save()
        
        # Check user was created properly
        self.assertEqual(user.username, self.valid_data['username'])
        self.assertEqual(user.email, self.valid_data['email'])
        self.assertEqual(user.first_name, self.valid_data['first_name'])
        self.assertEqual(user.last_name, self.valid_data['last_name'])
        self.assertEqual(user.role, self.valid_data['role'])
        self.assertTrue(user.terms_accepted)
        self.assertIsNotNone(user.terms_accepted_date)
        
        # Check password was set correctly
        self.assertTrue(user.check_password(self.valid_data['password']))
        
        # Check profile was created
        self.assertTrue(hasattr(user, 'patient_profile'))
        self.assertIsNotNone(user.patient_profile)
    
    def test_create_different_roles(self):
        """Test creating users with different roles creates appropriate profiles"""
        for role in ['patient', 'provider', 'pharmco', 'insurer']:
            data = self.valid_data.copy()
            data['username'] = f'test{role}'
            data['email'] = f'{role}@example.com'
            data['role'] = role
            
            serializer = UserRegistrationSerializer(data=data)
            self.assertTrue(serializer.is_valid())
            
            user = serializer.save()
            
            # Check the correct profile was created
            profile_attr = f'{role}_profile'
            self.assertTrue(hasattr(user, profile_attr))
            self.assertIsNotNone(getattr(user, profile_attr))


class ProfileSerializersTest(TestCase):
    """Test cases for the profile serializers"""
    
    def setUp(self):
        # Create users with different roles
        self.patient_user = User.objects.create_user(
            username='patient',
            email='patient@example.com',
            password='password123',
            role='patient'
        )
        
        # Get profiles
        self.patient_profile = PatientProfile.objects.get(user=self.patient_user)
    
    def test_patient_profile_serializer(self):
        """Test the PatientProfileSerializer"""
        # Set up some profile data
        self.patient_profile.medical_id = "MED12345"
        self.patient_profile.blood_type = "AB-"
        self.patient_profile.allergies = "Penicillin"
        self.patient_profile.save()
        
        serializer = PatientProfileSerializer(instance=self.patient_profile)
        data = serializer.data
        
        self.assertEqual(data['medical_id'], "MED12345")
        self.assertEqual(data['blood_type'], "AB-")
        self.assertEqual(data['allergies'], "Penicillin")


class PasswordChangeSerializerTest(TestCase):
    """Test cases for the PasswordChangeSerializer"""
    
    def setUp(self):
        self.valid_data = {
            'current_password': 'currentPassword123',
            'new_password': 'newSecurePassword456!',
            'confirm_password': 'newSecurePassword456!'
        }
    
    def test_validate_valid_data(self):
        """Test validation with valid data"""
        serializer = PasswordChangeSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
    
    def test_validate_password_mismatch(self):
        """Test validation with mismatched passwords"""
        data = self.valid_data.copy()
        data['confirm_password'] = 'differentPassword789!'
        
        serializer = PasswordChangeSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('confirm_password', serializer.errors)
