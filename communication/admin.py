# communication/admin.py
from django.contrib import admin
from .models import (
    Conversation, Message, MessageReceipt, Attachment,
    Notification, Announcement, AnnouncementReadStatus,
    CommunicationAuditLog
)

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ('sender', 'content', 'sent_at', 'is_system_message')
    readonly_fields = ('sent_at',)
    max_num = 10
    can_delete = False

class MessageReceiptInline(admin.TabularInline):
    model = MessageReceipt
    extra = 0
    fields = ('recipient', 'delivered_at', 'read_at')
    readonly_fields = ('delivered_at', 'read_at')
    can_delete = False

class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0
    fields = ('file', 'file_name', 'file_type', 'file_size', 'uploaded_at')
    readonly_fields = ('file_size', 'file_type', 'uploaded_at')

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'get_participants', 'created_at', 'updated_at')
    search_fields = ('title', 'participants__username', 'participants__first_name', 'participants__last_name')
    filter_horizontal = ('participants',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [MessageInline]
    
    def get_participants(self, obj):
        return ", ".join([user.username for user in obj.participants.all()[:3]])
    get_participants.short_description = 'Participants'

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'preview_content', 'sent_at', 'is_system_message')
    search_fields = ('content', 'sender__username', 'conversation__title')
    list_filter = ('is_system_message', 'sent_at')
    readonly_fields = ('sent_at',)
    inlines = [MessageReceiptInline, AttachmentInline]
    
    def preview_content(self, obj):
        if len(obj.content) > 50:
            return obj.content[:50] + "..."
        return obj.content
    preview_content.short_description = 'Content'

@admin.register(MessageReceipt)
class MessageReceiptAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'recipient', 'delivered_at', 'read_at')
    search_fields = ('recipient__username', 'message__content')
    list_filter = ('delivered_at', 'read_at')
    readonly_fields = ('delivered_at', 'read_at')

@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'file_name', 'file_type', 'file_size', 'uploaded_at')
    search_fields = ('file_name', 'message__content')
    list_filter = ('file_type', 'uploaded_at')
    readonly_fields = ('file_size', 'file_type', 'uploaded_at')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipient', 'notification_type', 'title', 'created_at', 'read_at')
    search_fields = ('recipient__username', 'title', 'message')
    list_filter = ('notification_type', 'created_at', 'read_at')
    readonly_fields = ('created_at', 'read_at')

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'audience', 'created_at', 'expires_at', 'is_active', 'created_by')
    search_fields = ('title', 'content')
    list_filter = ('audience', 'is_active', 'created_at')
    readonly_fields = ('created_at',)

@admin.register(AnnouncementReadStatus)
class AnnouncementReadStatusAdmin(admin.ModelAdmin):
    list_display = ('id', 'announcement', 'user', 'read_at')
    search_fields = ('announcement__title', 'user__username')
    list_filter = ('read_at',)
    readonly_fields = ('read_at',)

@admin.register(CommunicationAuditLog)
class CommunicationAuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'action_type', 'timestamp', 'ip_address')
    search_fields = ('user__username', 'details')
    list_filter = ('action_type', 'timestamp')
    readonly_fields = ('user', 'action_type', 'timestamp', 'ip_address', 'user_agent', 'conversation', 'message', 'attachment', 'details')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
