# users/tests/test_auth.py
import json
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
import pyotp
from users.models import UserSession

User = get_user_model()

class AuthenticationTest(TestCase):
    """Test cases for authentication endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create a standard user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123',
            role='patient'
        )
        
        # Create a user with 2FA enabled
        self.user_2fa = User.objects.create_user(
            username='user2fa',
            email='user2fa@example.com',
            password='password123',
            role='provider'
        )
        
        # Set up 2FA
        self.user_2fa.two_factor_enabled = True
        self.user_2fa.two_factor_secret = pyotp.random_base32()
        self.user_2fa.save()
    
    def test_login_success(self):
        """Test successful login"""
        # Make login request
        response = self.client.post(
            reverse('customuser-login'),
            data={
                'username': 'testuser',
                'password': 'password123'
            }
        )
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertFalse(response.data['requires_2fa'])
        
        # Check token is valid
        token = response.data['token']
        token_obj = Token.objects.get(key=token)
        self.assertEqual(token_obj.user, self.user)
    
    def test_login_failure(self):
        """Test failed login"""
        # Make login request with wrong password
        response = self.client.post(
            reverse('customuser-login'),
            data={
                'username': 'testuser',
                'password': 'wrongpassword'
            }
        )
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Check failed attempts were incremented
        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_attempts, 1)

    def test_login_account_lockout(self):
        """Test account lockout after too many failed attempts"""
        # Set the user close to the threshold
        self.user.failed_login_attempts = 4
        self.user.save()
        
        # Make a failed login request
        response = self.client.post(
            reverse('customuser-login'),
            data={
                'username': 'testuser',
                'password': 'wrongpassword'
            }
        )
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Check user is now locked
        self.user.refresh_from_db()
        self.assertTrue(self.user.account_locked)
        
        # Try to log in with correct password while locked
        response = self.client.post(
            reverse('customuser-login'),
            data={
                'username': 'testuser',
                'password': 'password123'
            }
        )
        
        # Check response still indicates locked account
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('Account is locked', response.data.get('error', ''))
    
    def test_login_with_2fa(self):
        """Test login for user with 2FA enabled"""
        # Make login request
        response = self.client.post(
            reverse('customuser-login'),
            data={
                'username': 'user2fa',
                'password': 'password123'
            }
        )
        
        # Check response indicates 2FA is required
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['requires_2fa'])
        self.assertIn('user_id', response.data)
        self.assertEqual(response.data['user_id'], self.user_2fa.id)
        
        # Token should not be provided yet
        self.assertNotIn('token', response.data)
    
    def test_verify_2fa(self):
        """Test 2FA verification"""
        # Generate a valid TOTP token
        totp = pyotp.TOTP(self.user_2fa.two_factor_secret)
        valid_token = totp.now()
        
        # Make verification request
        response = self.client.post(
            reverse('customuser-verify-2fa'),
            data={
                'user_id': self.user_2fa.id,
                'token': valid_token
            }
        )
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        
        # Check token is valid
        token = response.data['token']
        token_obj = Token.objects.get(key=token)
        self.assertEqual(token_obj.user, self.user_2fa)
    
    def test_verify_2fa_invalid_token(self):
        """Test 2FA verification with invalid token"""
        # Make verification request with invalid token
        response = self.client.post(
            reverse('customuser-verify-2fa'),
            data={
                'user_id': self.user_2fa.id,
                'token': '123456'  # Invalid token
            }
        )
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('Invalid 2FA token', response.data.get('error', ''))
    
    def test_logout(self):
        """Test logging out"""
        # First login
        login_response = self.client.post(
            reverse('customuser-login'),
            data={
                'username': 'testuser',
                'password': 'password123'
            }
        )
        token = login_response.data['token']
        
        # Authenticate
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        
        # Make logout request
        response = self.client.post(reverse('customuser-logout'))
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check token was deleted
        with self.assertRaises(Token.DoesNotExist):
            Token.objects.get(key=token)
        
        # Check the session was updated
        session = UserSession.objects.filter(user=self.user).first()
        self.assertIsNotNone(session)
        self.assertIsNotNone(session.logout_time)


class TwoFactorSetupTest(TestCase):
    """Test cases for two-factor authentication setup"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create a user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123',
            role='patient'
        )
        
        # Generate token
        self.token = Token.objects.create(user=self.user)
        
        # Authenticate
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
    
    def test_setup_2fa(self):
        """Test setting up 2FA"""
        # Request 2FA setup
        response = self.client.post(reverse('customuser-setup-2fa'))
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('secret', response.data)
        self.assertIn('qr_code', response.data)
        self.assertFalse(response.data['setup_complete'])
        
        # Check user has secret in database
        self.user.refresh_from_db()
        self.assertEqual(self.user.two_factor_secret, response.data['secret'])
        self.assertFalse(self.user.two_factor_enabled)  # Not enabled yet
    
    def test_verify_2fa_setup(self):
        """Test verifying 2FA setup"""
        # First set up 2FA
        setup_response = self.client.post(reverse('customuser-setup-2fa'))
        secret = setup_response.data['secret']
        
        # Generate a valid token
        totp = pyotp.TOTP(secret)
        valid_token = totp.now()
        
        # Verify 2FA setup
        response = self.client.post(
            reverse('customuser-verify-2fa-setup'),
            data={'token': valid_token}
        )
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['setup_complete'])
        
        # Check 2FA is enabled in database
        self.user.refresh_from_db()
        self.assertTrue(self.user.two_factor_enabled)
    
    def test_verify_2fa_setup_invalid_token(self):
        """Test verifying 2FA setup with invalid token"""
        # First set up 2FA
        self.client.post(reverse('customuser-setup-2fa'))
        
        # Verify with invalid token
        response = self.client.post(
            reverse('customuser-verify-2fa-setup'),
            data={'token': '123456'}  # Invalid token
        )
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Check 2FA is still not enabled
        self.user.refresh_from_db()
        self.assertFalse(self.user.two_factor_enabled)
    
    def test_disable_2fa(self):
        """Test disabling 2FA"""
        # First enable 2FA
        self.user.two_factor_enabled = True
        self.user.two_factor_secret = pyotp.random_base32()
        self.user.save()
        
        # Disable 2FA
        response = self.client.post(
            reverse('customuser-disable-2fa'),
            data={'password': 'password123'}
        )
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check 2FA is disabled in database
        self.user.refresh_from_db()
        self.assertFalse(self.user.two_factor_enabled)
    
    def test_disable_2fa_wrong_password(self):
        """Test disabling 2FA with wrong password"""
        # First enable 2FA
        self.user.two_factor_enabled = True
        self.user.two_factor_secret = pyotp.random_base32()
        self.user.save()
        
        # Try to disable 2FA with wrong password
        response = self.client.post(
            reverse('customuser-disable-2fa'),
            data={'password': 'wrongpassword'}
        )
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Check 2FA is still enabled
        self.user.refresh_from_db()
        self.assertTrue(self.user.two_factor_enabled)


class SessionsTest(TestCase):
    """Test cases for session management"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='sessiontestuser',
            email='session@example.com',
            password='password123',
            role='patient'
        )
        self.token = Token.objects.create(user=self.user)
        
    def test_concurrent_sessions(self):
        """Test that multiple sessions are tracked correctly"""
        # First login from 'browser 1'
        self.client.post(
            reverse('customuser-login'),
            data={
                'username': 'sessiontestuser',
                'password': 'password123'
            },
            HTTP_USER_AGENT='Browser 1',
            REMOTE_ADDR='192.168.1.1'
        )
        
        # Then login from 'browser 2'
        self.client.post(
            reverse('customuser-login'),
            data={
                'username': 'sessiontestuser',
                'password': 'password123'
            },
            HTTP_USER_AGENT='Browser 2',
            REMOTE_ADDR='192.168.1.2'
        )
        
        # Check both sessions are recorded
        sessions = UserSession.objects.filter(user=self.user)
        self.assertEqual(sessions.count(), 2)
        
        # Verify different IP addresses and agents
        ips = set(sessions.values_list('ip_address', flat=True))
        agents = set(sessions.values_list('user_agent', flat=True))
        self.assertEqual(len(ips), 2)
        self.assertEqual(len(agents), 2)
    
    def test_session_termination_on_password_change(self):
        """Test that all sessions except current are terminated on password change"""
        # Log in twice to create two sessions
        login_resp1 = self.client.post(
            reverse('customuser-login'),
            data={
                'username': 'sessiontestuser',
                'password': 'password123'
            }
        )
        token1 = login_resp1.data['token']
        
        # Create a second client for a separate session
        client2 = APIClient()
        login_resp2 = client2.post(
            reverse('customuser-login'),
            data={
                'username': 'sessiontestuser',
                'password': 'password123'
            }
        )
        token2 = login_resp2.data['token']
        
        # Use first session to change password
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token1}')
        self.client.post(
            reverse('customuser-change-password'),
            data={
                'current_password': 'password123',
                'new_password': 'NewPassword456!',
                'confirm_password': 'NewPassword456!'
            }
        )
        
        # Check that second token is no longer valid
        client2.credentials(HTTP_AUTHORIZATION=f'Token {token2}')
        response = client2.get(reverse('customuser-me'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # First token should also no longer work (due to reauthentication requirement)
        response = self.client.get(reverse('customuser-me'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Check that sessions are marked as forced logout
        sessions = UserSession.objects.filter(user=self.user)
        for session in sessions:
            if session.session_key != self.client.session.session_key:
                self.assertTrue(session.was_forced_logout)
                self.assertIsNotNone(session.logout_time)


class SecurityFeaturesTest(TestCase):
    """Test advanced security features"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='securityuser',
            email='security@example.com',
            password='SecurePassword123!',
            role='patient'
        )
    
    def test_password_complexity_enforcement(self):
        """Test that password complexity requirements are enforced"""
        # Try to register with weak passwords
        weak_passwords = [
            'short',           # Too short
            'lowercase123',    # No uppercase
            'UPPERCASE123',    # No lowercase
            'Nodigits!',       # No digits
            'Password'         # No special chars or digits
        ]
        
        for password in weak_passwords:
            data = {
                'username': f'user_{password}',
                'email': f'{password}@example.com',
                'password': password,
                'password_confirm': password,
                'first_name': 'Test',
                'last_name': 'User',
                'role': 'patient',
                'terms_accepted': True
            }
            
            response = self.client.post(
                reverse('customuser-list'),
                data=json.dumps(data),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('password', str(response.data))  # Check error relates to password
    
    def test_password_expiry(self):
        """Test password expiry functionality"""
        # Set last password change to 100 days ago (assuming 90-day expiry)
        self.user.last_password_change = timezone.now() - timezone.timedelta(days=100)
        self.user.save()
        
        # Check if password change is required
        self.assertTrue(self.user.requires_password_change(days=90))
        
        # Log in
        login_response = self.client.post(
            reverse('customuser-login'),
            data={
                'username': 'securityuser',
                'password': 'SecurePassword123!'
            }
        )
        
        # In a real implementation, you might check for a flag in the response
        # indicating password expiry, or you might enforce a redirect
        # This depends on how your system handles expired passwords
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
