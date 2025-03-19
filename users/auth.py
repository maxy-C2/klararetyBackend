# users/auth.py
import pyotp
from datetime import datetime
from django.conf import settings

def generate_totp_secret():
    """
    Generate a new TOTP secret key for Google Authenticator.
    
    Returns:
        str: A base32-encoded random secret key suitable for TOTP authentication
    """
    return pyotp.random_base32()

def verify_totp(user, token):
    """
    Verify a TOTP token against a user's secret.
    
    Args:
        user (CustomUser): The user whose TOTP secret will be used for verification
        token (str): The 6-digit TOTP token to verify
        
    Returns:
        bool: True if the token is valid, False otherwise
    """
    if not user.two_factor_secret:
        return False
    
    totp = pyotp.TOTP(user.two_factor_secret)
    return totp.verify(token)

def get_totp_uri(user):
    """
    Get the Google Authenticator URI for QR code generation.
    
    This URI can be encoded in a QR code which can be scanned by
    Google Authenticator or compatible apps.
    
    Args:
        user (CustomUser): The user whose TOTP secret will be used
        
    Returns:
        str: The URI for the authenticator app, or None if the user has no secret
    """
    if not user.two_factor_secret:
        return None
    
    totp = pyotp.TOTP(user.two_factor_secret)
    return totp.provisioning_uri(
        name=user.email,
        issuer_name="Klararety Health"
    )
