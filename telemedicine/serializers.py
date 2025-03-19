# telemedicine/serializers.py
from rest_framework import serializers
from .models import (
    Appointment, Consultation, Prescription, 
    Message, MedicalDocument, ProviderAvailability, ProviderTimeOff
)
from users.serializers import CustomUserSerializer

class AppointmentSerializer(serializers.ModelSerializer):
    patient_details = CustomUserSerializer(source='patient', read_only=True)
    provider_details = CustomUserSerializer(source='provider', read_only=True)
    follow_ups = serializers.SerializerMethodField()
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'provider', 'scheduled_time', 'end_time',
            'status', 'reason', 'appointment_type', 'created_at', 'updated_at',
            'patient_details', 'provider_details', 'is_recurring',
            'recurrence_pattern', 'recurrence_end_date', 'parent_appointment',
            'follow_ups', 'send_reminder'
        ]
        read_only_fields = ['created_at', 'updated_at', 'follow_ups']
    
    def get_follow_ups(self, obj):
        """Get follow-up appointments if any exist"""
        follow_ups = obj.follow_up_appointments.all()
        if follow_ups:
            return AppointmentSerializer(follow_ups, many=True).data
        return []


class ConsultationSerializer(serializers.ModelSerializer):
    zoom_join_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Consultation
        fields = [
            'id', 'appointment', 'start_time', 'end_time',
            'duration', 'notes', 'zoom_join_info'
        ]
        read_only_fields = ['duration', 'zoom_join_info']
    
    def get_zoom_join_info(self, obj):
        """Return Zoom join information based on user role"""
        request = self.context.get('request')
        if not request or not request.user:
            return None
        
        # Only return meeting ID and password
        if obj.zoom_meeting_id:
            return {
                'meeting_id': obj.zoom_meeting_id,
                'password': obj.zoom_meeting_password,
                'join_url': obj.zoom_join_url
                # Note: start_url is only returned in the join_info action for providers
            }
        return None


class PrescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prescription
        fields = [
            'id', 'consultation', 'medication_name', 'dosage',
            'frequency', 'duration', 'refills', 'notes',
            'pharmacy', 'created_at'
        ]
        read_only_fields = ['created_at']


class MessageSerializer(serializers.ModelSerializer):
    sender_details = CustomUserSerializer(source='sender', read_only=True)
    receiver_details = CustomUserSerializer(source='receiver', read_only=True)
    
    class Meta:
        model = Message
        fields = [
            'id', 'sender', 'receiver', 'appointment', 'content',
            'read', 'sent_at', 'read_at', 'sender_details', 'receiver_details'
        ]
        read_only_fields = ['sent_at', 'read_at']


class MedicalDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_details = CustomUserSerializer(source='uploaded_by', read_only=True)
    
    class Meta:
        model = MedicalDocument
        fields = [
            'id', 'patient', 'uploaded_by', 'appointment', 'document_type',
            'title', 'file', 'notes', 'uploaded_at', 'uploaded_by_details'
        ]
        read_only_fields = ['uploaded_at']


class ProviderAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderAvailability
        fields = [
            'id', 'provider', 'day_of_week', 'start_time',
            'end_time', 'is_available'
        ]


class ProviderTimeOffSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderTimeOff
        fields = [
            'id', 'provider', 'start_date', 'end_date', 'reason'
        ]

class AvailableSlotSerializer(serializers.Serializer):
    """Serializer for provider available time slots"""
    start = serializers.TimeField()
    end = serializers.TimeField()
