# telemedicine/services/reminder_service.py

from django.utils import timezone
from datetime import timedelta
from .email_service import EmailService
import logging

logger = logging.getLogger(__name__)

class AppointmentReminderService:
    """Service for managing and sending appointment reminders"""
    
    @staticmethod
    def get_upcoming_reminders():
        """
        Get appointments that need reminders sent
        (24 hours before the appointment)
        
        Returns:
            QuerySet: Appointments needing reminders
        """
        from ..models import Appointment
        
        reminder_time = timezone.now() + timedelta(hours=24)
        return Appointment.objects.filter(
            scheduled_time__range=(timezone.now(), reminder_time),
            status__in=['scheduled', 'confirmed'],
            send_reminder=True,
            reminder_sent=False
        )
    
    @staticmethod
    def send_reminder(appointment):
        """
        Send an email reminder for an appointment
        
        Args:
            appointment: The appointment object
            
        Returns:
            bool: True if reminder sent successfully, False otherwise
        """
        try:
            patient = appointment.patient
            provider = appointment.provider
            
            # Skip if patient has no email
            if not patient.email:
                logger.warning(f"Cannot send reminder: Patient {patient.id} has no email")
                return False
            
            # Format appointment time in user-friendly format
            appointment_time = appointment.scheduled_time.strftime("%A, %B %d, %Y at %I:%M %p")
            appointment_type_display = dict(appointment.APPOINTMENT_TYPE_CHOICES).get(
                appointment.appointment_type, appointment.appointment_type
            )
            
            # Create email subject
            subject = f"Reminder: Your {appointment_type_display} with Dr. {provider.last_name} tomorrow"
            
            # Create email content
            html_content = f"""
            <html>
            <body>
                <h2>Appointment Reminder</h2>
                <p>Dear {patient.first_name},</p>
                <p>This is a reminder of your upcoming appointment:</p>
                <ul>
                    <li><strong>Provider:</strong> {provider.get_full_name()}</li>
                    <li><strong>Date/Time:</strong> {appointment_time}</li>
                    <li><strong>Type:</strong> {appointment_type_display}</li>
                </ul>
                
                <p>If you need to reschedule, please contact us as soon as possible.</p>
                
                <p>Thank you,<br>
                Klararety Health Platform</p>
            </body>
            </html>
            """
            
            text_content = f"""
            APPOINTMENT REMINDER
            
            Dear {patient.first_name},
            
            This is a reminder of your upcoming appointment:
            
            Provider: {provider.get_full_name()}
            Date/Time: {appointment_time}
            Type: {appointment_type_display}
            
            If you need to reschedule, please contact us as soon as possible.
            
            Thank you,
            Klararety Health Platform
            """
            
            # Send the email using the EmailService
            email_sent = EmailService.send_email(
                recipient_email=patient.email,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            
            if email_sent:
                # Mark reminder as sent
                appointment.reminder_sent = True
                appointment.save()
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Error sending reminder for appointment {appointment.id}: {str(e)}")
            return False
