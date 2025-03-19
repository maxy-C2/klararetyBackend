# communication/services/email_service.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending emails"""
    
    @staticmethod
    def send_email(recipient_email, subject, html_content, text_content=None):
        """
        Send an email using SMTP
        
        Args:
            recipient_email: Email address of the recipient
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text alternative (optional)
            
        Returns:
            bool: True if the email was sent successfully, False otherwise
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
            
            # Send the message via SMTP server
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
    def send_notification_email(cls, notification):
        """
        Send an email for a notification
        
        Args:
            notification: The notification to send an email for
            
        Returns:
            bool: True if the email was sent successfully, False otherwise
        """
        recipient = notification.recipient
        
        if not recipient.email:
            logger.warning(f"Cannot send notification email: User {recipient.id} has no email")
            return False
        
        # Create email content
        html_content = f"""
        <html>
        <body>
            <h2>{notification.title}</h2>
            <p>{notification.message}</p>
            <p>Log in to your account to view more details.</p>
            <p>Thank you,<br>
            Klararety Health Platform</p>
        </body>
        </html>
        """
        
        text_content = f"""
        {notification.title}
        
        {notification.message}
        
        Log in to your account to view more details.
        
        Thank you,
        Klararety Health Platform
        """
        
        # Send the email
        return cls.send_email(
            recipient_email=recipient.email,
            subject=notification.title,
            html_content=html_content,
            text_content=text_content
        )
    
    @classmethod
    def send_message_notification_email(cls, message, recipient):
        """
        Send an email notification for a new message
        
        Args:
            message: The message that was sent
            recipient: The recipient of the notification
            
        Returns:
            bool: True if the email was sent successfully, False otherwise
        """
        if not recipient.email:
            logger.warning(f"Cannot send message notification email: User {recipient.id} has no email")
            return False
        
        sender = message.sender
        sender_name = sender.get_full_name() or sender.username
        
        # Create message preview
        message_preview = message.content
        if len(message_preview) > 200:
            message_preview = message_preview[:197] + "..."
        
        # Create email content
        html_content = f"""
        <html>
        <body>
            <h2>New Message from {sender_name}</h2>
            <p><strong>{sender_name}</strong> has sent you a message.</p>
            <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 15px 0;">
                <p>{message_preview}</p>
            </div>
            <p>Log in to your account to view the full conversation.</p>
            <p>Thank you,<br>
            Klararety Health Platform</p>
        </body>
        </html>
        """
        
        text_content = f"""
        New Message from {sender_name}
        
        {sender_name} has sent you a message.
        
        "{message_preview}"
        
        Log in to your account to view the full conversation.
        
        Thank you,
        Klararety Health Platform
        """
        
        # Send the email
        return cls.send_email(
            recipient_email=recipient.email,
            subject=f"New Message from {sender_name}",
            html_content=html_content,
            text_content=text_content
        )
