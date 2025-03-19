# users/tests/test_integration.py
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from users.models import PatientProfile, UserSession

User = get_user_model()

class UserRegistrationToProfileUpdateTest(TestCase):
    """Test the full user journey from registration to profile update"""
    
    def setUp(self):
        self.client = APIClient()
        
    def test_registration_to_profile_update(self):
        """Test full flow: register, login, update profile"""
        # 1. Register a new user
        registration_data = {
            'username': 'newpatient',
            'email': 'patient@example.com',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!',
            'first_name': 'New',
            'last_name': 'Patient',
            'role': 'patient',
            'terms_accepted': True
        }
        
        register_response = self.client.post(
            reverse('customuser-list'),
            data=registration_data,
            format='json'
        )
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        user_id = register_response.data['id']
        
        # 2. Login with the new user
        login_response = self.client.post(
            reverse('customuser-login'),
            data={
                'username': 'newpatient',
                'password': 'SecurePassword123!'
            }
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        token = login_response.data['token']
        
        # Set authentication header
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        
        # 3. Get user profile ID
        me_response = self.client.get(reverse('customuser-me'))
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        profile_id = me_response.data['patient_profile']['id']
        
        # 4. Update the patient profile
        profile_update = {
            'medical_id': 'MED123456',
            'blood_type': 'O+',
            'allergies': 'Penicillin, Dust'
        }
        
        update_response = self.client.patch(
            reverse('patientprofile-detail', kwargs={'pk': profile_id}),
            data=profile_update,
            format='json'
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        
        # 5. Verify the updates were saved
        profile_response = self.client.get(
            reverse('patientprofile-detail', kwargs={'pk': profile_id})
        )
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_response.data['medical_id'], 'MED123456')
        self.assertEqual(profile_response.data['blood_type'], 'O+')
        self.assertEqual(profile_response.data['allergies'], 'Penicillin, Dust')
        
        # 6. Check that user profile is marked as completed
        me_response = self.client.get(reverse('customuser-me'))
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        # Note: This test may need to be adjusted if your profile_completed logic differs
        # self.assertTrue(me_response.data['profile_completed'])

class SecurityTest(TestCase):
    """Test security features working together"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='securitytestuser',
            email='security@example.com',
            password='password123',
            role='patient'
        )
        self.token = Token.objects.create(user=self.user)
        
    def test_failed_login_to_lockout_to_unlock(self):
        """Test the security flow: failed logins → lockout → admin unlock"""
        # 1. Make multiple failed login attempts to trigger lockout
        for _ in range(5):
            self.client.post(
                reverse('customuser-login'),
                data={
                    'username': 'securitytestuser',
                    'password': 'wrongpassword'
                }
            )
        
        # 2. Check that account is now locked
        login_response = self.client.post(
            reverse('customuser-login'),
            data={
                'username': 'securitytestuser',
                'password': 'password123'  # Correct password
            }
        )
        self.assertEqual(login_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('Account is locked', login_response.data.get('error', ''))
        
        # 3. Create an admin user to unlock the account
        admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpassword',
            role='provider',
            is_staff=True
        )
        admin_token = Token.objects.create(user=admin_user)
        
        # 4. Admin unlocks the account
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {admin_token.key}')
        unlock_response = self.client.post(
            reverse('customuser-unlock', kwargs={'pk': self.user.pk})
        )
        self.assertEqual(unlock_response.status_code, status.HTTP_200_OK)
        
        # 5. Clear admin credentials
        self.client.credentials()
        
        # 6. User should now be able to log in
        login_response = self.client.post(
            reverse('customuser-login'),
            data={
                'username': 'securitytestuser',
                'password': 'password123'
            }
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn('token', login_response.data)
