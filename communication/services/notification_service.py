# communication/services/notification_service.py
from django.utils import timezone
from django.contrib.auth import get_user_model
from ..models import Notification

User = get_user_model()

class NotificationService:
    """Service for creating and managing notifications"""
    
    @staticmethod
    def create_notification(recipient, notification_type, title, message, **kwargs):
        """
        Create a notification for a user
        
        Args:
            recipient: The user to notify
            notification_type: The type of notification (from NOTIFICATION_TYPES)
            title: The notification title
            message: The notification message
            **kwargs: Additional fields (related_object_type, related_object_id, data)
            
        Returns:
            Notification: The created notification
        """
        # Create the notification
        notification = Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            related_object_type=kwargs.get('related_object_type'),
            related_object_id=kwargs.get('related_object_id'),
            data=kwargs.get('data', {})
        )
        
        return notification
    
    @staticmethod
    def notify_new_message(message):
        """
        Create notifications for a new message
        
        Args:
            message: The message that was sent
        """
        # Skip notification for system messages
        if message.is_system_message:
            return
        
        conversation = message.conversation
        sender = message.sender
        
        # Get a preview of the message content
        content_preview = message.content
        if len(content_preview) > 50:
            content_preview = content_preview[:47] + "..."
            
        # Create a notification for each participant except the sender
        for participant in conversation.participants.all():
            if participant != sender:
                # Create the notification
                NotificationService.create_notification(
                    recipient=participant,
                    notification_type='message',
                    title=f"New message from {sender.get_full_name() or sender.username}",
                    message=content_preview,
                    related_object_type='message',
                    related_object_id=message.id,
                    data={
                        'conversation_id': conversation.id,
                        'sender_id': sender.id,
                        'sender_name': sender.get_full_name() or sender.username
                    }
                )
    
    @staticmethod
    def notify_health_event(event_type, users, title, message, related_object=None):
        """
        Create notifications for a healthcare event
        
        Args:
            event_type: The type of notification (appointment, lab_result, prescription)
            users: List of users to notify
            title: The notification title
            message: The notification message
            related_object: Optional related object (appointment, lab_test, etc.)
        """
        related_object_type = None
        related_object_id = None
        data = {}
        
        # Set related object info if provided
        if related_object:
            related_object_type = related_object.__class__.__name__.lower()
            related_object_id = related_object.id
            
            # Add basic data about the related object
            data = {
                f"{related_object_type}_id": related_object.id
            }
            
            # Add specific data based on object type
            if hasattr(related_object, 'scheduled_time'):
                data['scheduled_time'] = related_object.scheduled_time.isoformat()
                
            if hasattr(related_object, 'test_date'):
                data['test_date'] = related_object.test_date.isoformat()
        
        # Create notifications for all specified users
        for user in users:
            NotificationService.create_notification(
                recipient=user,
                notification_type=event_type,
                title=title,
                message=message,
                related_object_type=related_object_type,
                related_object_id=related_object_id,
                data=data
            )
    
    @staticmethod
    def mark_all_read(user):
        """
        Mark all notifications as read for a user
        
        Args:
            user: The user whose notifications to mark as read
            
        Returns:
            int: Number of notifications marked as read
        """
        return Notification.objects.filter(
            recipient=user,
            read_at__isnull=True
        ).update(read_at=timezone.now())
    
    @staticmethod
    def get_unread_count(user):
        """
        Get the number of unread notifications for a user
        
        Args:
            user: The user to check
            
        Returns:
            int: The number of unread notifications
        """
        return Notification.objects.filter(
            recipient=user,
            read_at__isnull=True
        ).count()
