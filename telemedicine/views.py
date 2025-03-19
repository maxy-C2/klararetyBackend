# telemedicine/views.py
from datetime import datetime, time, timedelta
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from django.db.models import Q

from users.models import CustomUser
from .services.zoom_service import ZoomService
from .services.reminder_service import AppointmentReminderService
from .services.email_service import EmailService
from .services.consultation_auth_service import ConsultationAuthService
from telemedicine import serializers
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import logging


logger = logging.getLogger(__name__)

from .models import (
    Appointment, Consultation, Prescription, 
    Message, MedicalDocument, ProviderAvailability, ProviderTimeOff
)
from .serializers import (
    AppointmentSerializer, ConsultationSerializer, PrescriptionSerializer,
    MessageSerializer, MedicalDocumentSerializer, 
    ProviderAvailabilitySerializer, ProviderTimeOffSerializer,
    AvailableSlotSerializer
)
from .permissions import IsProviderOrReadOnly, IsPatientOrProvider


class AppointmentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for appointment management
    """
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # Filter based on user role
        if user.role == 'patient':
            return Appointment.objects.filter(patient=user)
        elif user.role == 'provider':
            return Appointment.objects.filter(provider=user)
        
        # Admin can see all
        if user.is_staff:
            return Appointment.objects.all()
            
        return Appointment.objects.none()
    
    @swagger_auto_schema(
        operation_description="Get user's upcoming appointments",
        responses={200: AppointmentSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get user's upcoming appointments"""
        user = request.user
        now = timezone.now()
        
        if user.role == 'patient':
            appointments = Appointment.objects.filter(
                patient=user,
                scheduled_time__gt=now,
                status__in=['scheduled', 'confirmed']
            ).order_by('scheduled_time')
        elif user.role == 'provider':
            appointments = Appointment.objects.filter(
                provider=user,
                scheduled_time__gt=now,
                status__in=['scheduled', 'confirmed']
            ).order_by('scheduled_time')
        else:
            appointments = Appointment.objects.none()
            
        serializer = self.get_serializer(appointments, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Cancel an appointment",
        responses={200: openapi.Response("Appointment cancelled successfully")}
    )
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an appointment and send cancellation email"""
        appointment = self.get_object()
        
        # Check if appointment can be cancelled
        if appointment.status in ['completed', 'cancelled', 'no_show']:
            return Response(
                {'error': 'Cannot cancel a completed or already cancelled appointment'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Cancel the appointment
        appointment.status = 'cancelled'
        appointment.save()
        
        # Send cancellation email
        EmailService.send_appointment_update(appointment, 'cancelled')
        
        return Response({'message': 'Appointment cancelled successfully'})
    
    @swagger_auto_schema(
        operation_description="Reschedule an appointment",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['scheduled_time', 'end_time'],
            properties={
                'scheduled_time': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                'end_time': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
            }
        ),
        responses={200: AppointmentSerializer()}
    )
    @action(detail=True, methods=['post'])
    def reschedule(self, request, pk=None):
        """Reschedule an appointment and send update email"""
        appointment = self.get_object()
        new_time = request.data.get('scheduled_time')
        new_end_time = request.data.get('end_time')
        
        if not new_time or not new_end_time:
            return Response(
                {'error': 'New scheduled time and end time are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Check if appointment can be rescheduled
        if appointment.status in ['completed', 'no_show']:
            return Response(
                {'error': 'Cannot reschedule a completed appointment'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Update the appointment
        appointment.scheduled_time = new_time
        appointment.end_time = new_end_time
        appointment.status = 'rescheduled'  # Set to 'rescheduled' status
        appointment.save()
        
        # Send rescheduling email
        EmailService.send_appointment_update(appointment, 'rescheduled')
        
        serializer = self.get_serializer(appointment)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Get available appointment slots for a provider",
        manual_parameters=[
            openapi.Parameter(
                'provider', openapi.IN_QUERY, 
                description="Provider ID", 
                type=openapi.TYPE_INTEGER, required=True
            ),
            openapi.Parameter(
                'date', openapi.IN_QUERY, 
                description="Date (YYYY-MM-DD)", 
                type=openapi.TYPE_STRING, required=True
            ),
        ],
        responses={200: AvailableSlotSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def available_slots(self, request):
        """Get available appointment slots for a provider"""
        provider_id = request.query_params.get('provider')
        date_str = request.query_params.get('date')
        
        if not provider_id or not date_str:
            return Response(
                {'error': 'Provider ID and date are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            provider = CustomUser.objects.get(id=provider_id, role='provider')
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except (CustomUser.DoesNotExist, ValueError):
            return Response(
                {'error': 'Invalid provider ID or date format'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        available_slots = self._get_provider_available_slots(provider, date_obj)
        
        return Response(available_slots)
    
    def _get_provider_available_slots(self, provider, date):
        """Calculate available time slots for a provider on a given date"""
        from .models import ProviderAvailability, ProviderTimeOff, Appointment
        
        # Check if provider is on time off for the whole day
        time_off = ProviderTimeOff.objects.filter(
            provider=provider,
            start_date__lte=timezone.make_aware(datetime.combine(date, time.max)),
            end_date__gte=timezone.make_aware(datetime.combine(date, time.min))
        ).exists()
        
        if time_off:
            return []
            
        # Get provider's availability for this day of the week
        day_of_week = date.weekday()
        availability = ProviderAvailability.objects.filter(
            provider=provider,
            day_of_week=day_of_week,
            is_available=True
        )
        
        if not availability:
            return []
            
        # Generate slots at 30-minute intervals
        all_slots = []
        slot_duration = timedelta(minutes=30)
        
        for avail in availability:
            current_time = datetime.combine(date, avail.start_time)
            end_time = datetime.combine(date, avail.end_time)
            
            while current_time + slot_duration <= end_time:
                slot_end = current_time + slot_duration
                all_slots.append({
                    'start': current_time.strftime('%H:%M'),
                    'end': slot_end.strftime('%H:%M')
                })
                current_time += slot_duration
                
        # Remove slots that conflict with existing appointments
        existing_appointments = Appointment.objects.filter(
            provider=provider,
            scheduled_time__date=date,
            status__in=['scheduled', 'confirmed', 'in_progress']
        )
        
        available_slots = []
        
        for slot in all_slots:
            slot_start = timezone.make_aware(
                datetime.combine(date, datetime.strptime(slot['start'], '%H:%M').time())
            )
            slot_end = timezone.make_aware(
                datetime.combine(date, datetime.strptime(slot['end'], '%H:%M').time())
            )
            
            conflict = existing_appointments.filter(
                scheduled_time__lt=slot_end,
                end_time__gt=slot_start
            ).exists()
            
            if not conflict:
                available_slots.append(slot)
                
        return available_slots

    @swagger_auto_schema(
        operation_description="Manually trigger sending of appointment reminders",
        responses={
            200: openapi.Response("Reminders sent successfully"),
            403: openapi.Response("Permission denied")
        }
    )
    @action(detail=False, methods=['post'])
    def send_reminders(self, request):
        """Manually trigger sending of appointment reminders"""
        if not request.user.is_staff:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
            
        reminder_service = AppointmentReminderService()
        appointments = reminder_service.get_upcoming_reminders()
        
        sent_count = 0
        for appointment in appointments:
            if reminder_service.send_reminder(appointment):
                sent_count += 1
                
        return Response({
            'message': f'Sent {sent_count} reminders out of {appointments.count()} pending'
        })
    
    def _check_provider_availability(self, provider, start_time, end_time):
        """Check if provider is available during the requested time"""
        from .models import ProviderAvailability, ProviderTimeOff, Appointment
        
        # Check day of week availability
        day_of_week = start_time.weekday()  # 0 = Monday, 6 = Sunday
        
        # Check regular availability for this day
        day_availability = ProviderAvailability.objects.filter(
            provider=provider,
            day_of_week=day_of_week,
            is_available=True
        )
        
        is_within_schedule = False
        for slot in day_availability:
            # Convert time objects to timezone-aware datetime for comparison
            slot_start = timezone.make_aware(
                datetime.combine(start_time.date(), slot.start_time)
            )
            slot_end = timezone.make_aware(
                datetime.combine(start_time.date(), slot.end_time)
            )
            
            if slot_start <= start_time and end_time <= slot_end:
                is_within_schedule = True
                break
        
        if not is_within_schedule:
            return False
        
        # Check if provider is on time off
        time_off = ProviderTimeOff.objects.filter(
            provider=provider,
            start_date__lte=end_time,
            end_date__gte=start_time
        ).exists()
        
        if time_off:
            return False
        
        # Check for conflicting appointments
        conflicts = Appointment.objects.filter(
            provider=provider,
            status__in=['scheduled', 'confirmed', 'in_progress'],
        ).filter(
            # Overlapping time check 
            (Q(scheduled_time__lt=end_time) & Q(end_time__gt=start_time))
        ).exists()
        
        return not conflicts
    
    def perform_create(self, serializer):
        """Add validation for provider availability and send confirmation email"""
        provider = serializer.validated_data.get('provider')
        scheduled_time = serializer.validated_data.get('scheduled_time')
        end_time = serializer.validated_data.get('end_time')
        
        # Check provider availability for this time slot
        is_available = self._check_provider_availability(
            provider, scheduled_time, end_time
        )
        
        if not is_available:
            raise serializers.ValidationError(
                "Provider is not available during this time slot."
            )
        
        # Create the appointment
        appointment = serializer.save()
        
        # If this is a video consultation, create the associated consultation
        if appointment.appointment_type == 'video_consultation':
            from .models import Consultation
            Consultation.objects.create(appointment=appointment)
        
        # Send confirmation email
        EmailService.send_appointment_confirmation(appointment)
        
        return appointment


class ConsultationViewSet(viewsets.ModelViewSet):
    """
    API endpoint for consultation management with Zoom integration
    """
    queryset = Consultation.objects.all()
    serializer_class = ConsultationSerializer
    permission_classes = [permissions.IsAuthenticated, IsProviderOrReadOnly]
    
    def get_queryset(self):
        user = self.request.user
        
        # Filter based on user role
        if user.role == 'patient':
            return Consultation.objects.filter(appointment__patient=user)
        elif user.role == 'provider':
            return Consultation.objects.filter(appointment__provider=user)
        
        # Admin can see all
        if user.is_staff:
            return Consultation.objects.all()
            
        return Consultation.objects.none()
    
    def perform_create(self, serializer):
        # Get appointment data
        appointment = serializer.validated_data.get('appointment')
        
        try:
            # Create Zoom meeting
            zoom = ZoomService()
            provider_email = appointment.provider.email
            
            # Calculate duration in minutes
            duration_minutes = int((appointment.end_time - appointment.scheduled_time).total_seconds() / 60)
            
            # Generate meeting topic
            topic = f"Medical Consultation - {appointment.provider.get_full_name()} and {appointment.patient.get_full_name()}"
            
            # Create Zoom meeting
            meeting = zoom.create_meeting(
                topic=topic,
                start_time=appointment.scheduled_time,
                duration_minutes=duration_minutes,
                provider_email=provider_email
            )
            
            # Save the consultation with Zoom details
            consultation = serializer.save(
                zoom_meeting_id=meeting.get('id'),
                zoom_meeting_password=meeting.get('password'),
                zoom_join_url=meeting.get('join_url'),
                zoom_start_url=meeting.get('start_url')
            )
            
            return consultation
            
        except Exception as e:
            logger.error(f"Failed to create Zoom meeting: {str(e)}")
            # Create consultation without Zoom details if there's an error
            return serializer.save()
    
    def perform_update(self, serializer):
        consultation = self.get_object()
        
        # Check if appointment timing has changed
        if 'appointment' in serializer.validated_data:
            appointment = serializer.validated_data.get('appointment')
            
            # If Zoom meeting exists and appointment timing changed
            if consultation.zoom_meeting_id and (
                appointment.scheduled_time != consultation.appointment.scheduled_time or
                appointment.end_time != consultation.appointment.end_time
            ):
                try:
                    # Update Zoom meeting
                    zoom = ZoomService()
                    duration_minutes = int((appointment.end_time - appointment.scheduled_time).total_seconds() / 60)
                    
                    zoom.update_meeting(
                        meeting_id=consultation.zoom_meeting_id,
                        start_time=appointment.scheduled_time,
                        duration_minutes=duration_minutes
                    )
                except Exception as e:
                    logger.error(f"Failed to update Zoom meeting: {str(e)}")
        
        # Save the updated consultation
        serializer.save()
    
    def perform_destroy(self, instance):
        # Delete Zoom meeting if it exists
        if instance.zoom_meeting_id:
            try:
                zoom = ZoomService()
                zoom.delete_meeting(instance.zoom_meeting_id)
            except Exception as e:
                logger.error(f"Failed to delete Zoom meeting: {str(e)}")
        
        # Delete the consultation
        instance.delete()
    
    @swagger_auto_schema(
        operation_description="Start a consultation",
        responses={
            200: ConsultationSerializer(),
            400: "Consultation has already started"
        }
    )
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a consultation"""
        consultation = self.get_object()
        
        # Check if consultation can be started
        if consultation.start_time:
            return Response(
                {'error': 'Consultation has already started'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Start the consultation
        consultation.start_time = timezone.now()
        consultation.appointment.status = 'in_progress'
        consultation.appointment.save()
        consultation.save()
        
        # Return the consultation with Zoom start URL for the provider
        serializer = self.get_serializer(consultation)
        response_data = serializer.data
        
        # Add Zoom start URL for providers
        if request.user.role == 'provider' and consultation.zoom_start_url:
            response_data['zoom_start_url'] = consultation.zoom_start_url
        
        return Response(response_data)
    
    @swagger_auto_schema(
        operation_description="End a consultation",
        responses={
            200: ConsultationSerializer(),
            400: "Consultation has not been started or has already ended"
        }
    )
    @action(detail=True, methods=['post'])
    def end(self, request, pk=None):
        """End a consultation"""
        consultation = self.get_object()
        
        # Check if consultation can be ended
        if not consultation.start_time:
            return Response(
                {'error': 'Consultation has not been started'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if consultation.end_time:
            return Response(
                {'error': 'Consultation has already ended'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # End the consultation
        consultation.end_time = timezone.now()
        consultation.appointment.status = 'completed'
        consultation.appointment.save()
        consultation.save()
        
        serializer = self.get_serializer(consultation)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Get Zoom join information for the consultation",
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'zoom_meeting_id': openapi.Schema(type=openapi.TYPE_STRING),
                    'zoom_meeting_password': openapi.Schema(type=openapi.TYPE_STRING),
                    'zoom_join_url': openapi.Schema(type=openapi.TYPE_STRING),
                    'requires_email_verification': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'zoom_start_url': openapi.Schema(type=openapi.TYPE_STRING),
                }
            ),
            400: "This consultation does not have a Zoom meeting",
            403: "You are not authorized to join this consultation"
        }
    )
    @action(detail=True, methods=['get'])
    def join_info(self, request, pk=None):
        """Get Zoom join information for the consultation"""
        consultation = self.get_object()
        
        # Check if this is a zoom consultation
        if not consultation.zoom_meeting_id:
            return Response(
                {'error': 'This consultation does not have a Zoom meeting'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user is authorized to join this consultation
        is_provider = request.user.role == 'provider' and request.user == consultation.appointment.provider
        is_patient = request.user.role == 'patient' and request.user == consultation.appointment.patient
        
        if not (is_provider or is_patient):
            return Response(
                {'error': 'You are not authorized to join this consultation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if we need to enforce 2FA for this consultation
        requires_2fa = consultation.appointment.patient.two_factor_enabled
        
        # Return join information
        response_data = {
            'zoom_meeting_id': consultation.zoom_meeting_id,
            'zoom_meeting_password': consultation.zoom_meeting_password,
            'zoom_join_url': consultation.zoom_join_url,
            'requires_email_verification': requires_2fa
        }
        
        # Only providers get the start URL
        if is_provider:
            response_data['zoom_start_url'] = consultation.zoom_start_url
        
        return Response(response_data)
        
    @swagger_auto_schema(
        operation_description="Request an access code via email to join the consultation",
        responses={
            200: "Access code sent successfully to your email",
            403: "You are not authorized to access this consultation",
            500: "Failed to send access code"
        }
    )
    @action(detail=True, methods=['post'])
    def request_access_code(self, request, pk=None):
        """Request an access code via email to join the consultation"""
        consultation = self.get_object()
        
        # Only the patient or provider of this consultation can request a code
        if (request.user != consultation.appointment.patient and 
            request.user != consultation.appointment.provider):
            return Response(
                {'error': 'You are not authorized to access this consultation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Send the access code via email
        success = ConsultationAuthService.send_access_code(consultation)
        
        if success:
            return Response({'message': 'Access code sent successfully to your email'})
        else:
            return Response(
                {'error': 'Failed to send access code'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_description="Verify access code to join consultation",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['code'],
            properties={
                'code': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'zoom_meeting_id': openapi.Schema(type=openapi.TYPE_STRING),
                    'zoom_meeting_password': openapi.Schema(type=openapi.TYPE_STRING),
                    'zoom_join_url': openapi.Schema(type=openapi.TYPE_STRING),
                    'zoom_start_url': openapi.Schema(type=openapi.TYPE_STRING),
                }
            ),
            400: "Access code is required",
            401: "Invalid or expired access code"
        }
    )
    @action(detail=True, methods=['post'])
    def verify_access_code(self, request, pk=None):
        """Verify access code to join consultation"""
        consultation = self.get_object()
        code = request.data.get('code')
        
        if not code:
            return Response(
                {'error': 'Access code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify the code
        is_valid = ConsultationAuthService.verify_access_code(consultation, code)
        
        if is_valid:
            # Return join information with an additional auth token
            response_data = {
                'message': 'Access code verified successfully',
                'zoom_meeting_id': consultation.zoom_meeting_id,
                'zoom_meeting_password': consultation.zoom_meeting_password,
                'zoom_join_url': consultation.zoom_join_url,
            }
            
            # Add start URL for providers
            if request.user.role == 'provider':
                response_data['zoom_start_url'] = consultation.zoom_start_url
            
            return Response(response_data)
        else:
            return Response(
                {'error': 'Invalid or expired access code'},
                status=status.HTTP_401_UNAUTHORIZED
            )


class PrescriptionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for prescription management
    """
    queryset = Prescription.objects.all()
    serializer_class = PrescriptionSerializer
    permission_classes = [permissions.IsAuthenticated, IsProviderOrReadOnly]
    
    def get_queryset(self):
        user = self.request.user
        
        # Filter based on user role
        if user.role == 'patient':
            return Prescription.objects.filter(consultation__appointment__patient=user)
        elif user.role == 'provider':
            return Prescription.objects.filter(consultation__appointment__provider=user)
        elif user.role == 'pharmco':
            return Prescription.objects.filter(pharmacy=user)
        
        # Admin can see all
        if user.is_staff:
            return Prescription.objects.all()
            
        return Prescription.objects.none()


class MessageViewSet(viewsets.ModelViewSet):
    """
    API endpoint for secure messaging
    """
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # User can see messages they've sent or received
        return Message.objects.filter(
            Q(sender=user) | Q(receiver=user)
        ).order_by('-sent_at')
    
    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)
    
    @swagger_auto_schema(
        operation_description="Mark a message as read",
        responses={
            200: MessageSerializer(),
            403: "You can only mark messages sent to you as read"
        }
    )
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a message as read"""
        message = self.get_object()
        
        # Only the receiver can mark a message as read
        if message.receiver != request.user:
            return Response(
                {'error': 'You can only mark messages sent to you as read'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        message.mark_as_read()
        serializer = self.get_serializer(message)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Get user's unread messages",
        responses={200: MessageSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Get user's unread messages"""
        messages = Message.objects.filter(
            receiver=request.user,
            read=False
        ).order_by('-sent_at')
        
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)


class MedicalDocumentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for medical document management
    """
    queryset = MedicalDocument.objects.all()
    serializer_class = MedicalDocumentSerializer
    permission_classes = [permissions.IsAuthenticated, IsPatientOrProvider]
    
    def get_queryset(self):
        user = self.request.user
        
        # Filter based on user role
        if user.role == 'patient':
            return MedicalDocument.objects.filter(patient=user)
        elif user.role == 'provider':
            return MedicalDocument.objects.filter(
                Q(uploaded_by=user) | 
                Q(patient__in=user.provider_profile.patients.all())
            )
        
        # Admin can see all
        if user.is_staff:
            return MedicalDocument.objects.all()
            
        return MedicalDocument.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


class ProviderAvailabilityViewSet(viewsets.ModelViewSet):
    """
    API endpoint for provider availability management
    """
    queryset = ProviderAvailability.objects.all()
    serializer_class = ProviderAvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        provider_id = self.request.query_params.get('provider')
        
        # Provider can only see/edit their own availability
        if user.role == 'provider' and not provider_id:
            return ProviderAvailability.objects.filter(provider=user)
        
        # Others can view any provider's availability
        if provider_id:
            return ProviderAvailability.objects.filter(provider_id=provider_id)
            
        # Admin can see all
        if user.is_staff:
            return ProviderAvailability.objects.all()
            
        return ProviderAvailability.objects.none()


class ProviderTimeOffViewSet(viewsets.ModelViewSet):
    """
    API endpoint for provider time off management
    """
    queryset = ProviderTimeOff.objects.all()
    serializer_class = ProviderTimeOffSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        provider_id = self.request.query_params.get('provider')
        
        # Provider can only see/edit their own time off
        if user.role == 'provider' and not provider_id:
            return ProviderTimeOff.objects.filter(provider=user)
        
        # Others can view any provider's time off
        if provider_id:
            return ProviderTimeOff.objects.filter(provider_id=provider_id)
            
        # Admin can see all
        if user.is_staff:
            return ProviderTimeOff.objects.all()
            
        return ProviderTimeOff.objects.none()
