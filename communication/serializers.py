# communication/serializers.py
from rest_framework import serializers
from .models import (
    Conversation, Message, MessageReceipt, Attachment,
    Notification, Announcement, AnnouncementReadStatus
)
from users.serializers import CustomUserSerializer
from django.utils import timezone

class AttachmentSerializer(serializers.ModelSerializer):
    """
    Serializer for file attachments.
    
    Handles file uploads and provides download URLs.
    """
    download_url = serializers.SerializerMethodField(
        help_text="URL to download the attachment"
    )
    
    class Meta:
        model = Attachment
        fields = [
            'id', 'message', 'file', 'file_name', 'file_type',
            'file_size', 'uploaded_at', 'download_url'
        ]
        read_only_fields = ['uploaded_at', 'file_size', 'file_type']
        extra_kwargs = {
            'file': {'help_text': 'The file to upload'},
            'file_name': {'help_text': 'Original filename of the attachment'},
            'file_type': {'help_text': 'MIME type of the file'},
            'file_size': {'help_text': 'Size of the file in bytes'},
            'message': {'help_text': 'ID of the message this attachment belongs to'},
        }
    
    def get_download_url(self, obj):
        """Get the download URL for the attachment"""
        request = self.context.get('request')
        if request and obj.file:
            return request.build_absolute_uri(obj.file.url)
        return None


class MessageReceiptSerializer(serializers.ModelSerializer):
    """
    Serializer for message delivery and read receipts.
    
    Tracks when messages are delivered and read by recipients.
    """
    recipient_details = CustomUserSerializer(
        source='recipient', 
        read_only=True,
        help_text="Details about the recipient user"
    )
    
    class Meta:
        model = MessageReceipt
        fields = [
            'id', 'message', 'recipient', 'delivered_at',
            'read_at', 'recipient_details'
        ]
        read_only_fields = ['delivered_at', 'read_at']
        extra_kwargs = {
            'message': {'help_text': 'ID of the message this receipt is for'},
            'recipient': {'help_text': 'ID of the user who received the message'},
            'delivered_at': {'help_text': 'When the message was delivered'},
            'read_at': {'help_text': 'When the message was read'},
        }


class MessageSerializer(serializers.ModelSerializer):
    """
    Serializer for messages.
    
    Includes sender details, attachments, and read receipts.
    """
    sender_details = CustomUserSerializer(
        source='sender', 
        read_only=True,
        help_text="Details about the message sender"
    )
    attachments = AttachmentSerializer(
        many=True, 
        read_only=True,
        help_text="File attachments for this message"
    )
    receipts = MessageReceiptSerializer(
        many=True, 
        read_only=True,
        help_text="Read receipts for this message"
    )
    
    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'content', 'sent_at',
            'is_system_message', 'sender_details', 'attachments', 'receipts'
        ]
        read_only_fields = ['sent_at', 'is_system_message']
        extra_kwargs = {
            'conversation': {'help_text': 'ID of the conversation this message belongs to'},
            'sender': {'help_text': 'ID of the user who sent the message', 'read_only': True},
            'content': {'help_text': 'Text content of the message'},
            'sent_at': {'help_text': 'When the message was sent'},
            'is_system_message': {'help_text': 'Whether this is a system-generated message'},
        }
    
    def create(self, validated_data):
        # Create the message
        message = super().create(validated_data)
        
        # Create receipts for all participants except the sender
        conversation = message.conversation
        for participant in conversation.participants.all():
            if participant != message.sender:
                MessageReceipt.objects.create(
                    message=message,
                    recipient=participant
                )
        
        return message


class ConversationSerializer(serializers.ModelSerializer):
    """
    Serializer for conversations.
    
    Includes participant details, last message, and unread count.
    """
    participants_details = CustomUserSerializer(
        source='participants', 
        many=True, 
        read_only=True,
        help_text="Details about the conversation participants"
    )
    last_message = serializers.SerializerMethodField(
        help_text="Information about the most recent message"
    )
    unread_count = serializers.SerializerMethodField(
        help_text="Number of unread messages for the current user"
    )
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'title', 'created_at', 'updated_at', 'participants',
            'related_to_appointment', 'related_to_medical_record',
            'participants_details', 'last_message', 'unread_count'
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'title': {'help_text': 'Optional title for the conversation'},
            'participants': {'help_text': 'IDs of users participating in the conversation'},
            'related_to_appointment': {'help_text': 'Optional related appointment ID'},
            'related_to_medical_record': {'help_text': 'Optional related medical record ID'},
        }
    
    def get_last_message(self, obj):
        """Get information about the most recent message"""
        last_msg = obj.last_message()
        if last_msg:
            return {
                'id': last_msg.id,
                'sender': last_msg.sender.get_full_name() or last_msg.sender.username,
                'content': last_msg.content[:100] + '...' if len(last_msg.content) > 100 else last_msg.content,
                'sent_at': last_msg.sent_at
            }
        return None
    
    def get_unread_count(self, obj):
        """Get count of unread messages for the current user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Count messages without read receipts for this user
            return MessageReceipt.objects.filter(
                message__conversation=obj,
                recipient=request.user,
                read_at__isnull=True
            ).count()
        return 0
    
    def create(self, validated_data):
        participants_data = validated_data.pop('participants', [])
        conversation = Conversation.objects.create(**validated_data)
        
        # Add participants
        if participants_data:
            conversation.participants.set(participants_data)
        
        # Add the current user as a participant if not already included
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            conversation.participants.add(request.user)
        
        return conversation


class ConversationDetailSerializer(ConversationSerializer):
    """
    Detailed serializer for conversation with messages.
    
    Extends ConversationSerializer to include recent messages.
    """
    messages = serializers.SerializerMethodField(
        help_text="Recent messages in the conversation"
    )
    
    class Meta(ConversationSerializer.Meta):
        fields = ConversationSerializer.Meta.fields + ['messages']
    
    def get_messages(self, obj):
        """Get the most recent messages (limited to 50)"""
        messages = obj.messages.order_by('-sent_at')[:50]
        return MessageSerializer(messages, many=True, context=self.context).data


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for user notifications.
    
    Handles various types of system notifications.
    """
    notification_type_display = serializers.CharField(
        source='get_notification_type_display', 
        read_only=True,
        help_text="Human-readable notification type"
    )
    
    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'notification_type', 'notification_type_display',
            'title', 'message', 'created_at', 'read_at',
            'related_object_type', 'related_object_id', 'data'
        ]
        read_only_fields = ['created_at', 'read_at']
        extra_kwargs = {
            'recipient': {'help_text': 'ID of the user receiving the notification'},
            'notification_type': {'help_text': 'Type of notification (message, appointment, etc.)'},
            'title': {'help_text': 'Short notification title'},
            'message': {'help_text': 'Longer notification message'},
            'read_at': {'help_text': 'When the notification was read (null if unread)'},
            'related_object_type': {'help_text': 'Type of related object (message, appointment, etc.)'},
            'related_object_id': {'help_text': 'ID of the related object'},
            'data': {'help_text': 'Additional data as JSON'},
        }


class AnnouncementSerializer(serializers.ModelSerializer):
    """
    Serializer for system announcements.
    
    Handles system-wide or targeted announcements.
    """
    created_by_details = CustomUserSerializer(
        source='created_by', 
        read_only=True,
        help_text="Details about who created the announcement"
    )
    is_read = serializers.SerializerMethodField(
        help_text="Whether the current user has read this announcement"
    )
    audience_display = serializers.CharField(
        source='get_audience_display', 
        read_only=True,
        help_text="Human-readable target audience"
    )
    
    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'content', 'audience', 'audience_display',
            'created_at', 'expires_at', 'created_by', 'created_by_details',
            'is_active', 'image', 'action_text', 'action_url', 'is_read'
        ]
        read_only_fields = ['created_at', 'is_read']
        extra_kwargs = {
            'title': {'help_text': 'Announcement title'},
            'content': {'help_text': 'Announcement content'},
            'audience': {'help_text': 'Target audience (all, patients, providers, etc.)'},
            'expires_at': {'help_text': 'When the announcement expires (optional)'},
            'created_by': {'help_text': 'ID of the admin user who created the announcement', 'read_only': True},
            'is_active': {'help_text': 'Whether the announcement is currently active'},
            'image': {'help_text': 'Optional image for the announcement'},
            'action_text': {'help_text': 'Optional call-to-action text'},
            'action_url': {'help_text': 'Optional call-to-action URL'},
        }
    
    def get_is_read(self, obj):
        """Check if the current user has read this announcement"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return AnnouncementReadStatus.objects.filter(
                announcement=obj,
                user=request.user
            ).exists()
        return False
