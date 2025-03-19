# users/tests/test_admin.py
from django.test import TestCase
from django.urls import reverse
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from users.admin import CustomUserAdmin
from users.models import CustomUser

User = get_user_model()

class MockRequest:
    def __init__(self, user=None):
        self.user = user

class AdminInterfaceTest(TestCase):
    """Test the admin interface customizations"""
    
    def setUp(self):
        self.site = AdminSite()
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpassword',
            role='provider'
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='user@example.com',
            password='password123',
            role='patient'
        )
        self.client.login(username='admin', password='adminpassword')
        
        # Create model admin instance
        self.user_admin = CustomUserAdmin(CustomUser, self.site)
    
    def test_custom_actions(self):
        """Test custom admin actions"""
        # Test lock_accounts action
        request = MockRequest(user=self.admin)
        
        # Execute the action on queryset containing the test user
        queryset = CustomUser.objects.filter(pk=self.user.pk)
        self.user_admin.lock_accounts(request, queryset)
        
        # Check that user is locked
        self.user.refresh_from_db()
        self.assertTrue(self.user.account_locked)
        
        # Test unlock_accounts action
        self.user_admin.unlock_accounts(request, queryset)
        self.user.refresh_from_db()
        self.assertFalse(self.user.account_locked)
        
        # Test disable_2fa action
        self.user.two_factor_enabled = True
        self.user.save()
        self.user_admin.disable_2fa(request, queryset)
        self.user.refresh_from_db()
        self.assertFalse(self.user.two_factor_enabled)

    def test_admin_changelist(self):
        """Test that the admin changelist page works"""
        response = self.client.get(reverse('admin:users_customuser_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'testuser')
        
        # Test filtering
        response = self.client.get(reverse('admin:users_customuser_changelist') + '?role=patient')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'testuser')
        
        response = self.client.get(reverse('admin:users_customuser_changelist') + '?role=provider')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'admin')
        self.assertNotContains(response, 'testuser')
    
    def test_admin_detail(self):
        """Test that the admin detail page works"""
        response = self.client.get(reverse('admin:users_customuser_change', args=[self.user.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'testuser')
        self.assertContains(response, 'patient')  # Role field
        
        # Check for security and permissions fieldsets
        self.assertContains(response, 'Security')
        self.assertContains(response, 'Permissions')
    
    def test_admin_add_user(self):
        """Test that the admin add user page works"""
        response = self.client.get(reverse('admin:users_customuser_add'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'username')
        self.assertContains(response, 'role')
        
        # Try adding a user via admin
        user_data = {
            'username': 'adminaddeduser',
            'email': 'adminadded@example.com',
            'password1': 'SecureAdminPassword123!',
            'password2': 'SecureAdminPassword123!',
            'role': 'patient',
            'is_active': True
        }
        response = self.client.post(
            reverse('admin:users_customuser_add'),
            data=user_data
        )
        
        # Check redirect (success)
        self.assertEqual(response.status_code, 302)
        
        # Check user was created
        self.assertTrue(User.objects.filter(username='adminaddeduser').exists())
