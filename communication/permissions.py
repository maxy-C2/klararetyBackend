# communication/permissions.py
from rest_framework import permissions

class IsConversationParticipant(permissions.BasePermission):
    """
    Permission to only allow participants to view or modify a conversation
    """
    def has_object_permission(self, request, view, obj):
        # Admin can access anything
        if request.user.is_staff:
            return True
        
        # Check if user is a participant
        return request.user in obj.participants.all()


class CanSendMessage(permissions.BasePermission):
    """
    Permission to check if user can send a message to a conversation
    """
    def has_permission(self, request, view):
        # Only write methods need additional checks
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Check if conversation_id is provided
        conversation_id = request.data.get('conversation')
        if not conversation_id:
            return False
        
        # Check if user is part of the conversation
        try:
            from .models import Conversation
            conversation = Conversation.objects.get(id=conversation_id)
            return request.user in conversation.participants.all()
        except Conversation.DoesNotExist:
            return False


class IsMessageSender(permissions.BasePermission):
    """
    Permission to only allow the sender to modify their messages
    """
    def has_object_permission(self, request, view, obj):
        # Admin can access anything
        if request.user.is_staff:
            return True
        
        # Only the sender can modify
        return obj.sender == request.user


class IsNotificationRecipient(permissions.BasePermission):
    """
    Permission to only allow the recipient to view or modify their notifications
    """
    def has_object_permission(self, request, view, obj):
        # Admin can access anything
        if request.user.is_staff:
            return True
        
        # Only the recipient can access
        return obj.recipient == request.user


class CanManageAnnouncements(permissions.BasePermission):
    """
    Permission to check if user can manage system announcements
    """
    def has_permission(self, request, view):
        # Anyone can read announcements
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Only staff can create/edit announcements
        return request.user.is_staff
