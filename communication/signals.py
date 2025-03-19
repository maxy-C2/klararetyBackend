# communication/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Notification, Message
from .services.email_service import EmailService
from .services.notification_service import NotificationService

@receiver(post_save, sender=Notification)
def send_notification_email(sender, instance, created, **kwargs):
    """Send an email for new notifications"""
    if created:
        # Send an email notification
        EmailService.send_notification_email(instance)

@receiver(post_save, sender=Message)
def handle_new_message(sender, instance, created, **kwargs):
    """Handle post-save actions for new messages"""
    if created and not instance.is_system_message:
        # Create notification for all participants
        NotificationService.notify_new_message(instance)
        
        # Send email notifications
        conversation = instance.conversation
        for participant in conversation.participants.all():
            if participant != instance.sender and participant.email:
                EmailService.send_message_notification_email(instance, participant)
