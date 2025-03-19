# communication/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone

class Conversation(models.Model):
    """
    Group conversation between multiple users.
    
    Attributes:
        title (str): Optional conversation title
        created_at (datetime): When the conversation was created
        updated_at (datetime): When the conversation was last updated
        participants (M2M): Users participating in the conversation
        related_to_appointment (FK): Optional related appointment
        related_to_medical_record (FK): Optional related medical record
    """
    title = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Participants in the conversation
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='conversations'
    )
    
    # Optional related objects
    related_to_appointment = models.ForeignKey(
        'telemedicine.Appointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversations'
    )
    related_to_medical_record = models.ForeignKey(
        'healthcare.MedicalRecord',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversations'
    )
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        if self.title:
            return self.title
        
        participants = self.participants.all()
        if participants.count() <= 3:
            # For small conversations, list all participants
            return f"Chat: {', '.join([p.get_full_name() or p.username for p in participants])}"
        else:
            # For larger group chats, show a few participants
            return f"Group: {', '.join([p.get_full_name() or p.username for p in participants[:2]])} and {participants.count() - 2} others"
    
    def last_message(self):
        """Get the last message in the conversation"""
        return self.messages.order_by('-sent_at').first()


class Message(models.Model):
    """
    Individual message within a conversation.
    
    Attributes:
        conversation (FK): The conversation this message belongs to
        sender (FK): The user who sent the message
        content (str): Message content
        sent_at (datetime): When the message was sent
        is_system_message (bool): Whether this is a system-generated message
    """
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='communication_sent_messages'
    )
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    
    # Message status
    is_system_message = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['sent_at']
    
    def __str__(self):
        return f"Message from {self.sender.username} at {self.sent_at}"


class MessageReceipt(models.Model):
    """
    Track when messages are delivered and read.
    
    Attributes:
        message (FK): The message this receipt is for
        recipient (FK): The user who received the message
        delivered_at (datetime): When the message was delivered (or null)
        read_at (datetime): When the message was read (or null)
    """
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='receipts')
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='message_receipts'
    )
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['message', 'recipient']
    
    def __str__(self):
        return f"Receipt: {self.recipient.username} - {self.message.sent_at}"
    
    def mark_delivered(self):
        """Mark the message as delivered"""
        if not self.delivered_at:
            self.delivered_at = timezone.now()
            self.save()
    
    def mark_read(self):
        """Mark the message as read"""
        if not self.read_at:
            self.read_at = timezone.now()
            if not self.delivered_at:
                self.delivered_at = self.read_at
            self.save()


class Attachment(models.Model):
    """
    File attachment for a message.
    
    Attributes:
        message (FK): The message this attachment belongs to
        file (FileField): The uploaded file
        file_name (str): Original filename
        file_type (str): MIME type of the file
        file_size (int): Size of the file in bytes
        uploaded_at (datetime): When the attachment was uploaded
    """
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='communication/attachments/%Y/%m/%d/')
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=100)
    file_size = models.PositiveIntegerField()  # Size in bytes
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.file_name


class Notification(models.Model):
    """
    User notifications for various system events.
    
    Attributes:
        recipient (FK): The user receiving the notification
        notification_type (str): Type of notification (message, appointment, etc.)
        title (str): Short notification title
        message (str): Longer notification message
        created_at (datetime): When the notification was created
        read_at (datetime): When the notification was read (or null)
        related_object_type (str): Optional related model type
        related_object_id (int): Optional related object ID
        data (JSON): Additional data as JSON
    """
    NOTIFICATION_TYPES = [
        ('message', 'New Message'),
        ('appointment', 'Appointment Reminder'),
        ('appointment_update', 'Appointment Update'),
        ('prescription', 'Prescription Update'),
        ('lab_result', 'Lab Result Available'),
        ('system', 'System Notification'),
    ]
    
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Optional related objects for context
    related_object_type = models.CharField(max_length=50, blank=True, null=True)
    related_object_id = models.PositiveIntegerField(blank=True, null=True)
    
    # Additional data as JSON
    data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_notification_type_display()} for {self.recipient.username}"
    
    def mark_read(self):
        """Mark the notification as read"""
        if not self.read_at:
            self.read_at = timezone.now()
            self.save()


class Announcement(models.Model):
    """
    System-wide or targeted announcements.
    
    Attributes:
        title (str): Announcement title
        content (str): Announcement content
        audience (str): Target audience (all, patients, providers, etc.)
        created_at (datetime): When the announcement was created
        expires_at (datetime): When the announcement expires (or null)
        created_by (FK): The admin user who created the announcement
        is_active (bool): Whether the announcement is currently active
        image (ImageField): Optional image for the announcement
        action_text (str): Optional call-to-action text
        action_url (URL): Optional call-to-action URL
    """
    AUDIENCE_CHOICES = [
        ('all', 'All Users'),
        ('patients', 'Patients Only'),
        ('providers', 'Providers Only'),
        ('pharmco', 'Pharmacies Only'),
        ('insurers', 'Insurers Only'),
    ]
    
    title = models.CharField(max_length=255)
    content = models.TextField()
    audience = models.CharField(max_length=20, choices=AUDIENCE_CHOICES, default='all')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_announcements'
    )
    
    # Control visibility
    is_active = models.BooleanField(default=True)
    
    # Optional image
    image = models.ImageField(upload_to='communication/announcements/', blank=True, null=True)
    
    # Action link
    action_text = models.CharField(max_length=50, blank=True, null=True)
    action_url = models.URLField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def is_expired(self):
        """Check if the announcement has expired"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at


class AnnouncementReadStatus(models.Model):
    """
    Track when users read announcements.
    
    Attributes:
        announcement (FK): The announcement that was read
        user (FK): The user who read the announcement
        read_at (datetime): When the announcement was read
    """
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='read_status')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='read_announcements'
    )
    read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['announcement', 'user']
    
    def __str__(self):
        return f"{self.user.username} read {self.announcement.title}"


class CommunicationAuditLog(models.Model):
    """
    Audit log for HIPAA compliance.
    
    Attributes:
        user (FK): The user who performed the action
        action_type (str): Type of action performed
        timestamp (datetime): When the action occurred
        ip_address (IP): The user's IP address
        user_agent (str): The user's browser/device user agent
        conversation (FK): Related conversation (if applicable)
        message (FK): Related message (if applicable)
        attachment (FK): Related attachment (if applicable)
        details (str): Additional details about the action
    """
    ACTION_TYPES = [
        ('message_sent', 'Message Sent'),
        ('message_read', 'Message Read'),
        ('attachment_uploaded', 'Attachment Uploaded'),
        ('attachment_downloaded', 'Attachment Downloaded'),
        ('conversation_created', 'Conversation Created'),
        ('conversation_participant_added', 'Participant Added'),
        ('conversation_participant_removed', 'Participant Removed'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='communication_audit_logs'
    )
    action_type = models.CharField(max_length=32, choices=ACTION_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    
    # Related objects
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    attachment = models.ForeignKey(
        Attachment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    
    # Additional details
    details = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.action_type} by {self.user.username} at {self.timestamp}"
