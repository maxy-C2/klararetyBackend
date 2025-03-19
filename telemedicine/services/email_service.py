# telemedicine/services/email_service.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending emails via Gmail"""
    
    @staticmethod
    def send_email(recipient_email, subject, html_content, text_content=None):
        """
        Send an email using Gmail SMTP
        
        Args:
            recipient_email (str): Email address of the recipient
            subject (str): Email subject
            html_content (str): HTML content of the email
            text_content (str): Plain text alternative (optional)
        
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # Create message container
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = settings.EMAIL_HOST_USER
            msg['To'] = recipient_email
            
            # Create the plain-text version of the message
            if text_content is None:
                # Default plain text version if not provided
                text_content = "Please view this email in an HTML compatible email client."
            
            # Add text and HTML parts to the message
            part1 = MIMEText(text_content, 'plain')
            part2 = MIMEText(html_content, 'html')
            msg.attach(part1)
            msg.attach(part2)
            
            # Send the message via Gmail SMTP server
            server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
            server.ehlo()
            server.starttls()
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.sendmail(settings.EMAIL_HOST_USER, recipient_email, msg.as_string())
            server.close()
            
            logger.info(f"Email sent successfully to {recipient_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
            return False

    @classmethod
    def _format_appointment_time(cls, appointment):
        """Helper method to format appointment date and time consistently"""
        appointment_time = appointment.scheduled_time.strftime("%A, %B %d, %Y at %I:%M %p")
        appointment_type_display = dict(appointment.APPOINTMENT_TYPE_CHOICES).get(
            appointment.appointment_type, appointment.appointment_type
        )
        provider = appointment.provider
        patient = appointment.patient
        
        return {
            'appointment_time': appointment_time,
            'appointment_type_display': appointment_type_display,
            'provider': provider,
            'patient': patient
        }
    
    @classmethod
    def send_appointment_confirmation(cls, appointment):
        """Send confirmation email for a new appointment"""
        patient = appointment.patient
        
        if not patient.email:
            logger.warning(f"Cannot send confirmation: Patient {patient.id} has no email")
            return False
        
        # Format appointment details
        details = cls._format_appointment_time(appointment)
        appointment_time = details['appointment_time']
        appointment_type_display = details['appointment_type_display']
        provider = details['provider']
        
        # Create email subject
        subject = f"Appointment Confirmation: {appointment_type_display} with Dr. {provider.last_name}"
        
        # Create email content
        html_content = f"""
        <html>
        <body>
            <h2>Appointment Confirmation</h2>
            <p>Dear {patient.first_name},</p>
            <p>Your appointment has been scheduled successfully:</p>
            <ul>
                <li><strong>Provider:</strong> {provider.get_full_name()}</li>
                <li><strong>Date/Time:</strong> {appointment_time}</li>
                <li><strong>Type:</strong> {appointment_type_display}</li>
                <li><strong>Reason:</strong> {appointment.reason}</li>
            </ul>
            
            <p>Please arrive 15 minutes before your scheduled time.</p>
            
            <p>Thank you,<br>
            Klararety Health Platform</p>
        </body>
        </html>
        """
        
        text_content = f"""
        APPOINTMENT CONFIRMATION
        
        Dear {patient.first_name},
        
        Your appointment has been scheduled successfully:
        
        Provider: {provider.get_full_name()}
        Date/Time: {appointment_time}
        Type: {appointment_type_display}
        Reason: {appointment.reason}
        
        Please arrive 15 minutes before your scheduled time.
        
        Thank you,
        Klararety Health Platform
        """
        
        return cls.send_email(
            recipient_email=patient.email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
    
    @classmethod
    def send_appointment_update(cls, appointment, update_type):
        """
        Send email about appointment updates
        
        Args:
            appointment: The appointment object
            update_type: String indicating the type of update ('cancelled', 'rescheduled', etc.)
        """
        patient = appointment.patient
        
        if not patient.email:
            logger.warning(f"Cannot send update: Patient {patient.id} has no email")
            return False
        
        # Format appointment details
        details = cls._format_appointment_time(appointment)
        appointment_time = details['appointment_time']
        appointment_type_display = details['appointment_type_display']
        provider = details['provider']
        
        # Create email content based on update type
        if update_type == 'cancelled':
            subject = f"Appointment Cancelled: Your appointment with Dr. {provider.last_name}"
            html_content = f"""
            <html>
            <body>
                <h2>Appointment Cancelled</h2>
                <p>Dear {patient.first_name},</p>
                <p>Your appointment has been cancelled:</p>
                <ul>
                    <li><strong>Provider:</strong> {provider.get_full_name()}</li>
                    <li><strong>Date/Time:</strong> {appointment_time}</li>
                    <li><strong>Type:</strong> {appointment_type_display}</li>
                </ul>
                
                <p>If you need to reschedule, please book a new appointment.</p>
                
                <p>Thank you,<br>
                Klararety Health Platform</p>
            </body>
            </html>
            """
            
            text_content = f"""
            APPOINTMENT CANCELLED
            
            Dear {patient.first_name},
            
            Your appointment has been cancelled:
            
            Provider: {provider.get_full_name()}
            Date/Time: {appointment_time}
            Type: {appointment_type_display}
            
            If you need to reschedule, please book a new appointment.
            
            Thank you,
            Klararety Health Platform
            """
            
        elif update_type == 'rescheduled':
            subject = f"Appointment Rescheduled: Your appointment with Dr. {provider.last_name}"
            html_content = f"""
            <html>
            <body>
                <h2>Appointment Rescheduled</h2>
                <p>Dear {patient.first_name},</p>
                <p>Your appointment has been rescheduled to:</p>
                <ul>
                    <li><strong>Provider:</strong> {provider.get_full_name()}</li>
                    <li><strong>New Date/Time:</strong> {appointment_time}</li>
                    <li><strong>Type:</strong> {appointment_type_display}</li>
                </ul>
                
                <p>If this new time doesn't work for you, please contact us.</p>
                
                <p>Thank you,<br>
                Klararety Health Platform</p>
            </body>
            </html>
            """
            
            text_content = f"""
            APPOINTMENT RESCHEDULED
            
            Dear {patient.first_name},
            
            Your appointment has been rescheduled to:
            
            Provider: {provider.get_full_name()}
            New Date/Time: {appointment_time}
            Type: {appointment_type_display}
            
            If this new time doesn't work for you, please contact us.
            
            Thank you,
            Klararety Health Platform
            """
        else:
            # Default update message
            subject = f"Appointment Update: Your appointment with Dr. {provider.last_name}"
            html_content = f"""
            <html>
            <body>
                <h2>Appointment Update</h2>
                <p>Dear {patient.first_name},</p>
                <p>Your appointment details have been updated:</p>
                <ul>
                    <li><strong>Provider:</strong> {provider.get_full_name()}</li>
                    <li><strong>Date/Time:</strong> {appointment_time}</li>
                    <li><strong>Type:</strong> {appointment_type_display}</li>
                </ul>
                
                <p>Thank you,<br>
                Klararety Health Platform</p>
            </body>
            </html>
            """
            
            text_content = f"""
            APPOINTMENT UPDATE
            
            Dear {patient.first_name},
            
            Your appointment details have been updated:
            
            Provider: {provider.get_full_name()}
            Date/Time: {appointment_time}
            Type: {appointment_type_display}
            
            Thank you,
            Klararety Health Platform
            """
        
        return cls.send_email(
            recipient_email=patient.email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
