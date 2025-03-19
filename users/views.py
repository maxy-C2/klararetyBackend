# users/views.py
import pyotp
import qrcode
from io import BytesIO
import base64

from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Q

from rest_framework import status, viewsets, generics, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import (
    CustomUser, PatientProfile, ProviderProfile, 
    PharmcoProfile, InsurerProfile, UserSession
)
from .serializers import (
    CustomUserSerializer, UserDetailSerializer, UserRegistrationSerializer,
    PatientProfileSerializer, ProviderProfileSerializer,
    PharmcoProfileSerializer, InsurerProfileSerializer,
    PasswordChangeSerializer, TwoFactorSetupSerializer
)
from .permissions import IsOwnerOrProvider, IsProviderOrReadOnly, IsAdminOrSelfOnly, IsRoleOwnerOrReadOnly
from .auth import verify_totp


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint for user management
    
    This viewset handles all user-related operations including:
    - User registration
    - User profile management
    - Account locking/unlocking
    - Authentication (login/logout)
    - Password management
    - Two-factor authentication setup
    """
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return UserRegistrationSerializer
        elif self.action in ['retrieve', 'me']:
            return UserDetailSerializer
        return CustomUserSerializer
    
    def get_permissions(self):
        """Set permission classes based on action"""
        # Allow registration without authentication
        if self.action in ['create', 'login', 'verify_2fa']:
            return [permissions.AllowAny()]
        return super().get_permissions()
    
    def get_queryset(self):
        """Filter users based on role and search parameters"""
        queryset = CustomUser.objects.all()
        
        # Role filtering
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        
        # Search by name or email
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) | 
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        
        return queryset
    
    @swagger_auto_schema(
        operation_description="Get current authenticated user's details",
        responses={
            200: UserDetailSerializer,
            401: 'Unauthorized'
        }
    )
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current authenticated user's details"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Administratively lock a user account",
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                }
            ),
            403: 'Forbidden',
            404: 'User not found'
        }
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrSelfOnly])
    def lock(self, request, pk=None):
        """Administratively lock a user account"""
        user = self.get_object()
        user.lock_account()
        return Response({'message': f'User {user.username} has been locked'})
    
    @swagger_auto_schema(
        operation_description="Unlock a user account",
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                }
            ),
            403: 'Forbidden',
            404: 'User not found'
        }
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrSelfOnly])
    def unlock(self, request, pk=None):
        """Unlock a user account"""
        user = self.get_object()
        user.unlock_account()
        return Response({'message': f'User {user.username} has been unlocked'})
    
    @swagger_auto_schema(
        operation_description="Change user password with validation",
        request_body=PasswordChangeSerializer,
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                }
            ),
            400: 'Validation Error',
            401: 'Unauthorized'
        }
    )
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Change user password with validation"""
        serializer = PasswordChangeSerializer(data=request.data)
        if serializer.is_valid():
            # Check current password
            if not request.user.check_password(serializer.validated_data['current_password']):
                return Response(
                    {'current_password': 'Wrong password'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Set new password
            request.user.change_password(serializer.validated_data['new_password'])
            
            # Update user session
            user_session = UserSession.objects.filter(
                user=request.user, 
                session_key=request.session.session_key
            ).first()
            
            if user_session:
                user_session.logout_time = timezone.now()
                user_session.save(update_fields=['logout_time'])
            
            # Clear all sessions except current
            UserSession.objects.filter(user=request.user).exclude(
                session_key=request.session.session_key
            ).update(
                was_forced_logout=True,
                logout_time=timezone.now()
            )
            
            return Response({'message': 'Password changed successfully. Please login again with your new password.'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        method='post',
        operation_description="User login with 2FA handling",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING),
                'password': openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=['username', 'password']
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'token': openapi.Schema(type=openapi.TYPE_STRING, description="Auth token for API requests"),
                    'user': openapi.Schema(type=openapi.TYPE_OBJECT, description="User details"),
                    'requires_2fa': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Whether 2FA verification is required"),
                }
            ),
            400: 'Bad Request',
            401: 'Invalid Credentials or Account Locked'
        }
    )
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def login(self, request):
        """User login with 2FA handling"""
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response(
                {'error': 'Please provide both username and password.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = authenticate(username=username, password=password)
        
        if not user:
            # Find the user to increment failed login attempts
            try:
                user_obj = CustomUser.objects.get(username=username)
                user_obj.increment_failed_login()
            except CustomUser.DoesNotExist:
                pass
                
            return Response(
                {'error': 'Invalid credentials.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Check if account is locked
        if user.account_locked:
            if user.locked_until and user.locked_until > timezone.now():
                minutes_remaining = int((user.locked_until - timezone.now()).total_seconds() / 60) + 1
                return Response(
                    {'error': f'Account is locked. Try again in {minutes_remaining} minutes.'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            else:
                # Unlock if lock period has expired
                user.unlock_account()
        
        # Start the session for non-2FA users or for first step of 2FA
        login(request, user)
        
        # Create user session for audit
        ip_address = self.request.META.get('REMOTE_ADDR', '')
        user_agent = self.request.META.get('HTTP_USER_AGENT', '')
        
        UserSession.objects.create(
            user=user,
            session_key=request.session.session_key,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Record login but don't reset failed attempts yet (wait for 2FA)
        user.last_login = timezone.now()
        user.last_login_ip = ip_address
        user.save(update_fields=['last_login', 'last_login_ip'])
        
        # Check if 2FA is required
        if user.two_factor_enabled:
            return Response({
                'message': 'Please complete two-factor authentication',
                'requires_2fa': True,
                'user_id': user.id  # Send user_id for the 2FA verification step
            })
        
        # If 2FA not required, complete the login process
        user.reset_failed_login()
        token, _ = Token.objects.get_or_create(user=user)
        
        return Response({
            'token': token.key,
            'user': UserDetailSerializer(user).data,
            'requires_2fa': False
        })
    
    @swagger_auto_schema(
        method='post',
        operation_description="Verify the 2FA token to complete login",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'token': openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=['user_id', 'token']
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'token': openapi.Schema(type=openapi.TYPE_STRING),
                    'user': openapi.Schema(type=openapi.TYPE_OBJECT),
                }
            ),
            400: 'Bad Request',
            401: 'Invalid Token',
            404: 'User not found'
        }
    )
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def verify_2fa(self, request):
        """Verify the 2FA token to complete login"""
        user_id = request.data.get('user_id')
        token = request.data.get('token')
        
        if not user_id or not token:
            return Response(
                {'error': 'Please provide both user_id and token.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response(
                {'error': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verify TOTP using auth helper function
        if not verify_totp(user, token):
            return Response(
                {'error': 'Invalid 2FA token.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Complete the login process
        user.reset_failed_login()
        auth_token, _ = Token.objects.get_or_create(user=user)
        
        return Response({
            'token': auth_token.key,
            'user': UserDetailSerializer(user).data
        })
    
    @swagger_auto_schema(
        operation_description="User logout with session tracking",
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        }
    )
    @action(detail=False, methods=['post'])
    def logout(self, request):
        """User logout with session tracking"""
        if request.user.is_authenticated:
            # Update the user session
            session = UserSession.objects.filter(
                user=request.user, 
                session_key=request.session.session_key
            ).first()
            
            if session:
                session.logout_time = timezone.now()
                session.save(update_fields=['logout_time'])
            
            # Delete the auth token
            Token.objects.filter(user=request.user).delete()
            
            # Django logout
            logout(request)
        
        return Response({'message': 'Successfully logged out.'})
    
    @swagger_auto_schema(
        operation_description="Set up two-factor authentication for the user",
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'secret': openapi.Schema(type=openapi.TYPE_STRING),
                    'qr_code': openapi.Schema(type=openapi.TYPE_STRING, description="Base64 encoded QR code image"),
                    'setup_complete': openapi.Schema(type=openapi.TYPE_BOOLEAN)
                }
            )
        }
    )
    @action(detail=False, methods=['post'])
    def setup_2fa(self, request):
        """Set up two-factor authentication for the user"""
        user = request.user
        
        # Generate a new secret if user doesn't have one
        if not user.two_factor_secret:
            user.two_factor_secret = pyotp.random_base32()
            user.save(update_fields=['two_factor_secret'])
        
        # Generate QR code for Google Authenticator
        totp = pyotp.TOTP(user.two_factor_secret)
        uri = totp.provisioning_uri(
            name=user.email,
            issuer_name="Klararety Health"
        )
        
        # Create QR code image
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 for front-end display
        buffer = BytesIO()
        img.save(buffer)
        qr_code_image = base64.b64encode(buffer.getvalue()).decode()
        
        # Return the secret and QR code for verification
        return Response({
            'secret': user.two_factor_secret,
            'qr_code': qr_code_image,
            'setup_complete': False
        })
    
    @swagger_auto_schema(
        operation_description="Verify and enable 2FA after setup",
        request_body=TwoFactorSetupSerializer,
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'setup_complete': openapi.Schema(type=openapi.TYPE_BOOLEAN)
                }
            ),
            400: 'Invalid verification code'
        }
    )
    @action(detail=False, methods=['post'])
    def verify_2fa_setup(self, request):
        """Verify and enable 2FA after setup"""
        user = request.user
        serializer = TwoFactorSetupSerializer(data=request.data)
        
        if serializer.is_valid():
            token = serializer.validated_data['token']
            
            # Verify the token against the user's secret
            if verify_totp(user, token):
                # Enable 2FA for the user
                user.two_factor_enabled = True
                user.save(update_fields=['two_factor_enabled'])
                
                return Response({
                    'message': 'Two-factor authentication has been enabled.',
                    'setup_complete': True
                })
            else:
                return Response(
                    {'error': 'Invalid verification code.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_description="Disable two-factor authentication",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'password': openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=['password']
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                }
            ),
            400: 'Invalid password'
        }
    )
    @action(detail=False, methods=['post'])
    def disable_2fa(self, request):
        """Disable two-factor authentication"""
        user = request.user
        
        # Require password confirmation to disable 2FA
        password = request.data.get('password')
        if not password or not user.check_password(password):
            return Response(
                {'error': 'Invalid password.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.two_factor_enabled = False
        user.save(update_fields=['two_factor_enabled'])
        
        return Response({'message': 'Two-factor authentication has been disabled.'})


# Base viewset with common functionality for all profile types
class BaseProfileViewSet(viewsets.ModelViewSet):
    """Base viewset for all profile types with common functionality"""
    permission_classes = [IsAuthenticated, IsRoleOwnerOrReadOnly]
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context


class PatientProfileViewSet(BaseProfileViewSet):
    """API endpoint for patient profile management"""
    queryset = PatientProfile.objects.all()
    serializer_class = PatientProfileSerializer
    
    def get_queryset(self):
        """Limit to current user's profile or all profiles for providers"""
        user = self.request.user
        if user.role == 'provider':
            return PatientProfile.objects.all()
        return PatientProfile.objects.filter(user=user)


class ProviderProfileViewSet(BaseProfileViewSet):
    """API endpoint for healthcare provider profile management"""
    queryset = ProviderProfile.objects.all()
    serializer_class = ProviderProfileSerializer
    
    def get_queryset(self):
        """Limit to current user's profile or all providers for patients"""
        user = self.request.user
        if user.role == 'provider':
            return ProviderProfile.objects.filter(user=user)
        return ProviderProfile.objects.all()


class PharmcoProfileViewSet(BaseProfileViewSet):
    """API endpoint for pharmacy profile management"""
    queryset = PharmcoProfile.objects.all()
    serializer_class = PharmcoProfileSerializer
    
    def get_queryset(self):
        """Limit to current user's profile or all pharmacies for others"""
        user = self.request.user
        if user.role == 'pharmco':
            return PharmcoProfile.objects.filter(user=user)
        return PharmcoProfile.objects.all()


class InsurerProfileViewSet(BaseProfileViewSet):
    """API endpoint for insurance provider profile management"""
    queryset = InsurerProfile.objects.all()
    serializer_class = InsurerProfileSerializer
    
    def get_queryset(self):
        """Limit to current user's profile or all insurers for others"""
        user = self.request.user
        if user.role == 'insurer':
            return InsurerProfile.objects.filter(user=user)
        return InsurerProfile.objects.all()
