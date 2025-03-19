# communication/views.py
from rest_framework import viewsets, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import (
    Conversation, Message, MessageReceipt, Attachment,
    Notification, Announcement, AnnouncementReadStatus,
    CommunicationAuditLog
)
from .serializers import (
    ConversationSerializer, ConversationDetailSerializer, MessageSerializer,
    AttachmentSerializer, NotificationSerializer, AnnouncementSerializer
)
from .permissions import (
    IsConversationParticipant, CanSendMessage, IsMessageSender,
    IsNotificationRecipient, CanManageAnnouncements
)
from .services.message_service import MessageService

class ConversationViewSet(viewsets.ModelViewSet):
    """
    API endpoints for managing conversations.
    
    list:
    Returns a list of conversations where the current user is a participant.
    
    retrieve:
    Returns a conversation by ID if the user is a participant.
    
    create:
    Creates a new conversation with the specified participants.
    
    update:
    Updates a conversation (title only).
    
    destroy:
    Deletes a conversation.
    """
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated, IsConversationParticipant]
    
    def get_queryset(self):
        """Get conversations where the user is a participant"""
        user = self.request.user
        
        # Admin can see all conversations
        if user.is_staff:
            return Conversation.objects.all()
        
        # Others can only see conversations they're part of
        return user.conversations.all()
    
    def get_serializer_class(self):
        """Return different serializers for list and detail views"""
        if self.action == 'retrieve':
            return ConversationDetailSerializer
        return ConversationSerializer
    
    def perform_create(self, serializer):
        """Create conversation and log it"""
        conversation = serializer.save()
        
        # Add audit log entry
        CommunicationAuditLog.objects.create(
            user=self.request.user,
            action_type='conversation_created',
            conversation=conversation,
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT'),
            details=f"Created conversation with {conversation.participants.count()} participants"
        )
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """
        Get messages in a conversation with pagination.
        Also marks messages as read for the current user.
        """
        conversation = self.get_object()
        
        # Get pagination parameters
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
        # Get messages with pagination
        messages = conversation.messages.order_by('-sent_at')[
            (page - 1) * page_size:page * page_size
        ]
        
        # Serialize and return
        serializer = MessageSerializer(messages, many=True, context={'request': request})
        
        # Mark messages as read for the current user
        for message in messages:
            if message.sender != request.user:
                receipt = MessageReceipt.objects.filter(
                    message=message,
                    recipient=request.user
                ).first()
                if receipt and not receipt.read_at:
                    receipt.mark_read()
                    
                    # Log message read event
                    CommunicationAuditLog.objects.create(
                        user=request.user,
                        action_type='message_read',
                        conversation=conversation,
                        message=message,
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT')
                    )
        
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_participant(self, request, pk=None):
        """
        Add a user to a conversation.
        
        Required parameters:
        - user_id: ID of the user to add
        """
        conversation = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'User ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if the user exists
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Add the user if not already a participant
        if user not in conversation.participants.all():
            conversation.participants.add(user)
            
            # Add system message about new participant
            MessageService.send_message(
                conversation=conversation,
                sender=request.user,
                content=f"{user.get_full_name() or user.username} was added to the conversation",
                is_system_message=True,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            # Log participant added event
            CommunicationAuditLog.objects.create(
                user=request.user,
                action_type='conversation_participant_added',
                conversation=conversation,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                details=f"Added {user.username} to conversation"
            )
        
        serializer = self.get_serializer(conversation)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def remove_participant(self, request, pk=None):
        """
        Remove a user from a conversation.
        
        Required parameters:
        - user_id: ID of the user to remove
        """
        conversation = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'User ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if the user exists
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Remove the user if they are a participant
        if user in conversation.participants.all():
            # Don't allow removing the last participant
            if conversation.participants.count() <= 1:
                return Response(
                    {'error': 'Cannot remove the last participant'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            conversation.participants.remove(user)
            
            # Add system message about removed participant
            MessageService.send_message(
                conversation=conversation,
                sender=request.user,
                content=f"{user.get_full_name() or user.username} was removed from the conversation",
                is_system_message=True,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            # Log participant removed event
            CommunicationAuditLog.objects.create(
                user=request.user,
                action_type='conversation_participant_removed',
                conversation=conversation,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                details=f"Removed {user.username} from conversation"
            )
        
        serializer = self.get_serializer(conversation)
        return Response(serializer.data)


class MessageViewSet(viewsets.ModelViewSet):
    """
    API endpoints for messages.
    
    list:
    Returns a list of messages the user has access to.
    
    retrieve:
    Returns a message by ID if the user has access.
    
    create:
    Creates a new message in a conversation.
    
    update:
    Not supported.
    
    destroy:
    Not supported.
    """
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated, CanSendMessage]
    
    def get_queryset(self):
        """Filter messages for the current user"""
        user = self.request.user
        
        # Admin can see all messages
        if user.is_staff:
            return Message.objects.all()
        
        # Others can only see messages in conversations they're part of
        return Message.objects.filter(conversation__participants=user)
    
    def perform_create(self, serializer):
        """Create message and log it"""
        # Ensure the sender is the current user
        message = serializer.save(sender=self.request.user)
        
        # Update the conversation's timestamp
        conversation = message.conversation
        conversation.updated_at = timezone.now()
        conversation.save()
        
        # Log message sent event
        CommunicationAuditLog.objects.create(
            user=self.request.user,
            action_type='message_sent',
            conversation=conversation,
            message=message,
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT')
        )
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """
        Mark a message as read.
        """
        message = self.get_object()
        
        # Find the receipt for the current user
        receipt = MessageReceipt.objects.filter(
            message=message,
            recipient=request.user
        ).first()
        
        if receipt:
            receipt.mark_read()
            
            # Log message read event
            CommunicationAuditLog.objects.create(
                user=request.user,
                action_type='message_read',
                conversation=message.conversation,
                message=message,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            return Response({'status': 'message marked as read'})
        
        return Response(
            {'error': 'Receipt not found'},
            status=status.HTTP_404_NOT_FOUND
        )


class AttachmentViewSet(viewsets.ModelViewSet):
    """
    API endpoints for file attachments.
    
    list:
    Returns a list of file attachments the user has access to.
    
    retrieve:
    Returns a file attachment by ID if the user has access.
    
    create:
    Uploads a new file attachment for a message.
    
    update:
    Not supported.
    
    destroy:
    Deletes a file attachment.
    """
    queryset = Attachment.objects.all()
    serializer_class = AttachmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter attachments for the current user"""
        user = self.request.user
        
        # Admin can see all attachments
        if user.is_staff:
            return Attachment.objects.all()
        
        # Others can only see attachments in conversations they're part of
        return Attachment.objects.filter(message__conversation__participants=user)
    
    def perform_create(self, serializer):
        """Create attachment with file info"""
        # Extract file information
        file = serializer.validated_data.get('file')
        
        attachment = serializer.save(
            file_name=file.name,
            file_type=file.content_type,
            file_size=file.size
        )
        
        # Log attachment uploaded event
        CommunicationAuditLog.objects.create(
            user=self.request.user,
            action_type='attachment_uploaded',
            conversation=attachment.message.conversation,
            message=attachment.message,
            attachment=attachment,
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT'),
            details=f"Uploaded {file.name} ({file.size} bytes)"
        )
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        Get a download URL for an attachment.
        Also logs the download event.
        """
        attachment = self.get_object()
        
        # Log attachment downloaded event
        CommunicationAuditLog.objects.create(
            user=request.user,
            action_type='attachment_downloaded',
            conversation=attachment.message.conversation,
            message=attachment.message,
            attachment=attachment,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        
        return Response({
            'download_url': request.build_absolute_uri(attachment.file.url)
        })


class NotificationViewSet(viewsets.ModelViewSet):
    """
    API endpoints for user notifications.
    
    list:
    Returns a list of notifications for the current user.
    
    retrieve:
    Returns a notification by ID if the user is the recipient.
    
    create:
    Not typically used directly (notifications are created by the system).
    
    update:
    Not supported.
    
    destroy:
    Deletes a notification.
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated, IsNotificationRecipient]
    filterset_fields = ['notification_type', 'read_at']
    search_fields = ['title', 'message']
    
    def get_queryset(self):
        """Get notifications for the current user"""
        user = self.request.user
        
        # Admin can see all notifications
        if user.is_staff and self.request.query_params.get('all') == 'true':
            return Notification.objects.all()
        
        # By default, users only see their own notifications
        return Notification.objects.filter(recipient=user)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """
        Mark a notification as read.
        """
        notification = self.get_object()
        notification.mark_read()
        serializer = self.get_serializer(notification)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """
        Mark all notifications as read for the current user.
        """
        count = Notification.objects.filter(
            recipient=request.user,
            read_at__isnull=True
        ).update(read_at=timezone.now())
        
        return Response({
            'status': 'success',
            'count': count,
            'message': f'Marked {count} notifications as read'
        })
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """
        Get count of unread notifications for the current user.
        """
        count = Notification.objects.filter(
            recipient=request.user,
            read_at__isnull=True
        ).count()
        
        return Response({
            'unread_count': count
        })


class AnnouncementViewSet(viewsets.ModelViewSet):
    """
    API endpoints for system announcements.
    
    list:
    Returns a list of active announcements for the user's role.
    
    retrieve:
    Returns an announcement by ID.
    
    create:
    Creates a new announcement (staff only).
    
    update:
    Updates an announcement (staff only).
    
    destroy:
    Deletes an announcement (staff only).
    """
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAuthenticated, CanManageAnnouncements]
    filterset_fields = ['audience', 'is_active']
    search_fields = ['title', 'content']
    
    def get_queryset(self):
        """Filter announcements based on user role"""
        user = self.request.user
        queryset = Announcement.objects.filter(is_active=True)
        
        # Filter by expiration
        queryset = queryset.filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        )
        
        # If not an admin requesting all announcements
        if not (user.is_staff and self.request.query_params.get('all') == 'true'):
            # Filter by audience
            queryset = queryset.filter(
                Q(audience='all') |
                Q(audience=user.role) |
                (Q(audience='providers') & Q(user__role='provider'))
            )
        
        return queryset
    
    def perform_create(self, serializer):
        """Set the created_by field to the current user"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """
        Mark an announcement as read by the current user.
        """
        announcement = self.get_object()
        
        # Create or get read status
        AnnouncementReadStatus.objects.get_or_create(
            announcement=announcement,
            user=request.user
        )
        
        return Response({'status': 'announcement marked as read'})
    
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """
        Get unread announcements for the current user.
        """
        # Get the user's role to filter by audience
        user_role = request.user.role
        
        # Get active and non-expired announcements
        queryset = Announcement.objects.filter(
            is_active=True
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        )
        
        # Filter by audience
        queryset = queryset.filter(
            Q(audience='all') |
            Q(audience=user_role)
        )
        
        # Exclude announcements the user has already read
        read_announcements = AnnouncementReadStatus.objects.filter(
            user=request.user
        ).values_list('announcement_id', flat=True)
        
        queryset = queryset.exclude(id__in=read_announcements)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
