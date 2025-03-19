# users/tests/test_views.py
import json
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from users.models import PatientProfile

User = get_user_model()

class UserViewSetTest(TestCase):
    """Test cases for the UserViewSet"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create a standard user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123',
            role='patient'
        )
        
        # Create an admin user
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpassword123',
            role='provider',
            is_staff=True
        )
        
        # Generate token for the standard user
        self.token = Token.objects.create(user=self.user)
        
        # Generate token for the admin user
        self.admin_token = Token.objects.create(user=self.admin_user)
    
    def test_list_users_authenticated(self):
        """Test listing users when authenticated"""
        # Authenticate with token
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
        # Make the request
        response = self.client.get(reverse('customuser-list'))
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)  # 2 users in the database
    
    def test_list_users_unauthenticated(self):
        """Test listing users when not authenticated"""
        # Make the request without authentication
        response = self.client.get(reverse('customuser-list'))
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_create_user(self):
        """Test creating a new user"""
        # Create user data
        user_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!',
            'first_name': 'New',
            'last_name': 'User',
            'role': 'patient',
            'terms_accepted': True
        }
        
        # Make the request (registration doesn't require authentication)
        response = self.client.post(
            reverse('customuser-list'),
            data=json.dumps(user_data),
            content_type='application/json'
        )
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify user was created in the database
        self.assertTrue(
            User.objects.filter(username='newuser').exists()
        )
        
        # Verify profile was created
        user = User.objects.get(username='newuser')
        self.assertTrue(hasattr(user, 'patient_profile'))
    
    def test_retrieve_user(self):
        """Test retrieving a user's details"""
        # Authenticate with token
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
        # Make the request
        response = self.client.get(
            reverse('customuser-detail', kwargs={'pk': self.user.pk})
        )
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], self.user.username)
        self.assertEqual(response.data['email'], self.user.email)
        
        # Check for profile data
        self.assertIn('patient_profile', response.data)
    
    def test_me_endpoint(self):
        """Test the 'me' endpoint"""
        # Authenticate with token
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
        # Make the request
        response = self.client.get(reverse('customuser-me'))
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], self.user.username)
        self.assertEqual(response.data['email'], self.user.email)
    
    def test_lock_user(self):
        """Test locking a user account"""
        # Authenticate as admin
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        
        # Make the request to lock a user
        response = self.client.post(
            reverse('customuser-lock', kwargs={'pk': self.user.pk})
        )
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify user is locked in the database
        self.user.refresh_from_db()
        self.assertTrue(self.user.account_locked)
    
    def test_unlock_user(self):
        """Test unlocking a user account"""
        # First lock the account
        self.user.lock_account()
        self.user.save()
        
        # Authenticate as admin
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        
        # Make the request to unlock the user
        response = self.client.post(
            reverse('customuser-unlock', kwargs={'pk': self.user.pk})
        )
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify user is unlocked in the database
        self.user.refresh_from_db()
        self.assertFalse(self.user.account_locked)
    
    def test_change_password(self):
        """Test changing a user's password"""
        # Authenticate with token
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
        # Make the request
        response = self.client.post(
            reverse('customuser-change-password'),
            data={
                'current_password': 'password123',
                'new_password': 'NewSecurePassword456!',
                'confirm_password': 'NewSecurePassword456!'
            }
        )
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewSecurePassword456!'))
    
    def test_change_password_wrong_current(self):
        """Test changing password with wrong current password"""
        # Authenticate with token
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
        # Make the request with wrong current password
        response = self.client.post(
            reverse('customuser-change-password'),
            data={
                'current_password': 'wrongpassword',
                'new_password': 'NewSecurePassword456!',
                'confirm_password': 'NewSecurePassword456!'
            }
        )
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Verify password was not changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('password123'))


class UserSearchFilterTest(TestCase):
    """Test search and filtering capabilities"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create admin user for authentication
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpassword',
            role='provider',
            is_staff=True
        )
        self.token = Token.objects.create(user=self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
        # Create test users
        roles = ['patient', 'provider', 'pharmco', 'insurer']
        for i in range(20):  # Create 20 users (5 of each role)
            role = roles[i % 4]
            User.objects.create_user(
                username=f'user{i}_{role}',
                email=f'user{i}@{role}.com',
                password='password123',
                role=role,
                first_name=f'FirstName{i}',
                last_name=f'LastName{i}'
            )
    
    def test_role_filtering(self):
        """Test filtering users by role"""
        for role in ['patient', 'provider', 'pharmco', 'insurer']:
            response = self.client.get(f"{reverse('customuser-list')}?role={role}")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            
            # Each role should have at least 5 users (plus admin for provider)
            expected_count = 5
            if role == 'provider':
                expected_count += 1  # Admin is also a provider
                
            self.assertEqual(len(response.data['results']), expected_count)
            
            # All returned users should have the correct role
            for user in response.data['results']:
                self.assertEqual(user['role'], role)
    
    def test_search_functionality(self):
        """Test searching users by username, email, or name"""
        # Search by username
        response = self.client.get(f"{reverse('customuser-list')}?search=user5")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertIn('user5', response.data['results'][0]['username'])
        
        # Search by email domain
        response = self.client.get(f"{reverse('customuser-list')}?search=patient.com")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)  # 5 patient users
        
        # Search by first name
        response = self.client.get(f"{reverse('customuser-list')}?search=FirstName3")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['first_name'], 'FirstName3')
    
    def test_pagination(self):
        """Test pagination of user results"""
        # Default pagination should limit results
        response = self.client.get(reverse('customuser-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        
        # Total count should match total users
        self.assertEqual(response.data['count'], 21)  # 20 test users + admin
        
        # Test custom page size
        response = self.client.get(f"{reverse('customuser-list')}?page_size=5")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)
        
        # Test second page
        response = self.client.get(f"{reverse('customuser-list')}?page=2&page_size=10")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 10)
        self.assertIsNotNone(response.data['previous'])
        self.assertIsNotNone(response.data['next'])
