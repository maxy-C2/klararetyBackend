# communication/services/message_service.py
from django.utils import timezone
from django.db import transaction
from ..models import Conversation, Message, MessageReceipt, CommunicationAuditLog

class MessageService:
    """Service for message operations"""
    
    @staticmethod
    @transaction.atomic
    def send_message(conversation, sender, content, is_system_message=False, ip_address=None, user_agent=None):
        """
        Send a message in a conversation
        
        Args:
            conversation: The conversation to send the message in
            sender: The user sending the message
            content: The message content
            is_system_message: Whether this is a system message (default: False)
            ip_address: The sender's IP address (for logging)
            user_agent: The sender's user agent (for logging)
            
        Returns:
            Message: The created message
        """
        # Create the message
        message = Message.objects.create(
            conversation=conversation,
            sender=sender,
            content=content,
            is_system_message=is_system_message
        )
        
        # Create receipts for all participants except the sender
        for participant in conversation.participants.all():
            if participant != sender:
                MessageReceipt.objects.create(
                    message=message,
                    recipient=participant
                )
        
        # Update the conversation's timestamp
        conversation.updated_at = timezone.now()
        conversation.save()
        
        # Log message sent event
        CommunicationAuditLog.objects.create(
            user=sender,
            action_type='message_sent',
            conversation=conversation,
            message=message,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return message
    
    @staticmethod
    def create_conversation(participants, title=None, ip_address=None, user_agent=None, **kwargs):
        """
        Create a new conversation
        
        Args:
            participants: List of users to participate in the conversation
            title: Optional title for the conversation
            ip_address: The creator's IP address (for logging)
            user_agent: The creator's user agent (for logging)
            **kwargs: Additional fields (related_to_appointment, related_to_medical_record)
            
        Returns:
            Conversation: The created conversation
        """
        # Create the conversation
        conversation = Conversation.objects.create(
            title=title,
            related_to_appointment=kwargs.get('related_to_appointment'),
            related_to_medical_record=kwargs.get('related_to_medical_record')
        )
        
        # Add participants
        for participant in participants:
            conversation.participants.add(participant)
        
        # Log conversation created event
        CommunicationAuditLog.objects.create(
            user=participants[0],  # First participant is assumed to be the creator
            action_type='conversation_created',
            conversation=conversation,
            ip_address=ip_address,
            user_agent=user_agent,
            details=f"Created conversation with {conversation.participants.count()} participants"
        )
        
        return conversation
    
    @staticmethod
    def get_unread_count(user):
        """
        Get the number of unread messages for a user
        
        Args:
            user: The user to check
            
        Returns:
            int: The number of unread messages
        """
        return MessageReceipt.objects.filter(
            recipient=user,
            read_at__isnull=True
        ).count()
        
    @staticmethod
    def mark_message_read(message, user, ip_address=None, user_agent=None):
        """
        Mark a message as read for a specific user
        
        Args:
            message: The message to mark as read
            user: The user who read the message
            ip_address: The user's IP address (for logging)
            user_agent: The user's user agent (for logging)
            
        Returns:
            bool: True if the message was marked as read, False if it was already read
        """
        receipt = MessageReceipt.objects.filter(
            message=message,
            recipient=user
        ).first()
        
        if receipt and not receipt.read_at:
            receipt.mark_read()
            
            # Log message read event
            CommunicationAuditLog.objects.create(
                user=user,
                action_type='message_read',
                conversation=message.conversation,
                message=message,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return True
            
        return False
