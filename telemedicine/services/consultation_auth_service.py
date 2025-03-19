# telemedicine/services/consultation_auth_service.py

import random
import string
from django.utils import timezone
from datetime import timedelta
from .email_service import EmailService

class ConsultationAuthService:
    """Service for consultation authentication via email"""
    
    @staticmethod
    def generate_access_code(length=6):
        """
        Generate a numeric access code
        
        Args:
            length (int, optional): Length of the code. Defaults to 6.
            
        Returns:
            str: Random numeric access code
        """
        return ''.join(random.choices(string.digits, k=length))
    
    @staticmethod
    def send_access_code(consultation):
        """
        Send consultation access code to patient via email
        
        Args:
            consultation: The consultation object
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        patient = consultation.appointment.patient
        provider = consultation.appointment.provider
        
        if not patient.email:
            return False
        
        # Generate a random access code
        access_code = ConsultationAuthService.generate_access_code()
        
        # Store the code and its expiration time on the consultation
        consultation.access_code = access_code
        consultation.access_code_expires = timezone.now() + timedelta(minutes=15)
        consultation.save()
        
        # Format consultation details
        consultation_time = consultation.appointment.scheduled_time.strftime("%I:%M %p")
        consultation_date = consultation.appointment.scheduled_time.strftime("%A, %B %d, %Y")
        
        # Create email content
        subject = f"Access Code for Your Video Consultation with Dr. {provider.last_name}"
        
        html_content = f"""
        <html>
        <body>
            <h2>Video Consultation Access Code</h2>
            <p>Dear {patient.first_name},</p>
            <p>Here is your access code for the upcoming video consultation:</p>
            <div style="background-color: #f0f0f0; padding: 10px; text-align: center; font-size: 24px; letter-spacing: 5px; font-weight: bold;">
                {access_code}
            </div>
            <p>Consultation details:</p>
            <ul>
                <li><strong>Provider:</strong> {provider.get_full_name()}</li>
                <li><strong>Date:</strong> {consultation_date}</li>
                <li><strong>Time:</strong> {consultation_time}</li>
            </ul>
            <p>This code will expire in 15 minutes. You'll need to enter this code to join the video consultation.</p>
            <p>Thank you,<br>
            Klararety Health Platform</p>
        </body>
        </html>
        """
        
        text_content = f"""
        VIDEO CONSULTATION ACCESS CODE
        
        Dear {patient.first_name},
        
        Here is your access code for the upcoming video consultation:
        
        {access_code}
        
        Consultation details:
        Provider: {provider.get_full_name()}
        Date: {consultation_date}
        Time: {consultation_time}
        
        This code will expire in 15 minutes. You'll need to enter this code to join the video consultation.
        
        Thank you,
        Klararety Health Platform
        """
        
        return EmailService.send_email(
            recipient_email=patient.email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
    
    @staticmethod
    def verify_access_code(consultation, code):
        """
        Verify the access code for a consultation
        
        Args:
            consultation: The consultation object
            code (str): The access code to verify
            
        Returns:
            bool: True if code is valid and not expired, False otherwise
        """
        # Check if code matches and is not expired
        if (consultation.access_code == code and 
            consultation.access_code_expires and 
            consultation.access_code_expires > timezone.now()):
            
            # Clear the code after successful verification
            consultation.access_code = None
            consultation.access_code_expires = None
            consultation.save()
            
            return True
        
        return False
