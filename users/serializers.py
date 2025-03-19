# users/serializers.py
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.hashers import make_password
from .models import (
    CustomUser, PatientProfile, ProviderProfile, 
    PharmcoProfile, InsurerProfile, UserSession
)

class UserSessionSerializer(serializers.ModelSerializer):
    """Serializer for user session data - used for audit and security tracking"""
    class Meta:
        model = UserSession
        fields = ['id', 'ip_address', 'user_agent', 'location', 'login_time', 'logout_time']
        read_only_fields = fields


class BaseProfileSerializer(serializers.ModelSerializer):
    """Base serializer for all profile types with common validation logic"""
    def validate(self, attrs):
        if 'user' in attrs and self.context.get('request'):
            if self.context['request'].user != attrs['user'] and not self.context['request'].user.is_staff:
                raise serializers.ValidationError({"user": "You can only update your own profile"})
        return attrs


class PatientProfileSerializer(BaseProfileSerializer):
    """Serializer for patient-specific profile information"""
    class Meta:
        model = PatientProfile
        fields = [
            'id', 'medical_id', 'emergency_contact_name', 
            'emergency_contact_phone', 'emergency_contact_relationship',
            'blood_type', 'allergies', 'medical_conditions'
        ]


class ProviderProfileSerializer(BaseProfileSerializer):
    """Serializer for healthcare provider-specific profile information"""
    class Meta:
        model = ProviderProfile
        fields = [
            'id', 'license_number', 'specialty', 'practice_name',
            'practice_address', 'years_of_experience', 'npi_number'
        ]


class PharmcoProfileSerializer(BaseProfileSerializer):
    """Serializer for pharmacy-specific profile information"""
    class Meta:
        model = PharmcoProfile
        fields = [
            'id', 'pharmacy_name', 'pharmacy_address', 
            'pharmacy_license', 'pharmacy_hours', 'does_delivery'
        ]


class InsurerProfileSerializer(BaseProfileSerializer):
    """Serializer for insurance provider-specific profile information"""
    class Meta:
        model = InsurerProfile
        fields = [
            'id', 'company_name', 'company_address',
            'support_phone', 'policy_prefix'
        ]


class CustomUserSerializer(serializers.ModelSerializer):
    """Serializer for user listing and basic info"""
    
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'role', 'role_display', 'phone_number', 'date_of_birth',
            'date_joined', 'last_login', 'two_factor_enabled',
            'profile_completed'
        ]
        read_only_fields = ['date_joined', 'last_login']


class UserDetailSerializer(CustomUserSerializer):
    """Extended user serializer with profile information based on role"""
    
    patient_profile = PatientProfileSerializer(read_only=True)
    provider_profile = ProviderProfileSerializer(read_only=True)
    pharmco_profile = PharmcoProfileSerializer(read_only=True)
    insurer_profile = InsurerProfileSerializer(read_only=True)
    recent_sessions = serializers.SerializerMethodField()
    
    class Meta(CustomUserSerializer.Meta):
        fields = CustomUserSerializer.Meta.fields + [
            'patient_profile', 'provider_profile', 
            'pharmco_profile', 'insurer_profile',
            'recent_sessions'
        ]
    
    def get_recent_sessions(self, obj):
        """Retrieve the 5 most recent user sessions for security tracking"""
        sessions = UserSession.objects.filter(user=obj).order_by('-login_time')[:5]
        return UserSessionSerializer(sessions, many=True).data


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for new user registration"""
    
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)
    terms_accepted = serializers.BooleanField(required=True)
    
    class Meta:
        model = CustomUser
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'role', 'phone_number', 
            'date_of_birth', 'terms_accepted'
        ]
    
    def validate(self, attrs):
        # Check password match
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Passwords don't match"})
        
        # Check terms acceptance
        if not attrs['terms_accepted']:
            raise serializers.ValidationError({"terms_accepted": "You must accept the terms and conditions"})
        
        return attrs
    
    def create(self, validated_data):
        # Remove confirm password and terms fields
        validated_data.pop('password_confirm')
        terms_accepted = validated_data.pop('terms_accepted')
        
        # Hash the password
        validated_data['password'] = make_password(validated_data['password'])
        
        # Create the user
        user = CustomUser.objects.create(**validated_data)
        
        # Handle terms acceptance
        if terms_accepted:
            user.accept_terms()
        
        # Note: The profile creation is now solely handled by the signal
        # defined in signals.py to avoid duplicated code
        
        return user


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change with validation"""
    
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    confirm_password = serializers.CharField(required=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords don't match"})
        return attrs


class TwoFactorSetupSerializer(serializers.Serializer):
    """Serializer for enabling/verifying two-factor authentication"""
    
    token = serializers.CharField(required=True, min_length=6, max_length=6)
