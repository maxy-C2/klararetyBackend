# telemedicine/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
        ('rescheduled', 'Rescheduled'),
    ]
    
    APPOINTMENT_TYPE_CHOICES = [
        ('video_consultation', 'Video Consultation'),
        ('phone_consultation', 'Phone Consultation'),
        ('in_person', 'In-Person Visit'),
        ('follow_up', 'Follow-up'),
        ('urgent_care', 'Urgent Care'),
        ('specialist_referral', 'Specialist Referral'),
    ]

    appointment_type = models.CharField(
        max_length=50, 
        choices=APPOINTMENT_TYPE_CHOICES,
        default='video_consultation'
    )

    parent_appointment = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        related_name='follow_up_appointments'
    )

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='patient_appointments',
        limit_choices_to={'role': 'patient'}
    )
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='provider_appointments',
        limit_choices_to={'role': 'provider'}
    )

    is_recurring = models.BooleanField(default=False)
    recurrence_pattern = models.CharField(max_length=50, blank=True, null=True)  # e.g., 'weekly', 'biweekly', 'monthly'
    recurrence_end_date = models.DateField(blank=True, null=True)
    send_reminder = models.BooleanField(default=True)
    reminder_sent = models.BooleanField(default=False)
    
    scheduled_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    reason = models.TextField()
    appointment_type = models.CharField(max_length=50, default='video_consultation')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.patient.username} with {self.provider.username} on {self.scheduled_time}"
    
    def is_upcoming(self):
        return self.scheduled_time > timezone.now() and self.status not in ['completed', 'cancelled', 'no_show']


class Consultation(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='consultation')
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    duration = models.DurationField(blank=True, null=True)
    
    # Zoom-specific fields
    zoom_meeting_id = models.CharField(max_length=255, blank=True, null=True)
    zoom_meeting_password = models.CharField(max_length=255, blank=True, null=True)
    zoom_join_url = models.URLField(blank=True, null=True)
    zoom_start_url = models.URLField(blank=True, null=True)  # For providers to start the meeting
    
    access_code = models.CharField(max_length=6, blank=True, null=True)
    access_code_expires = models.DateTimeField(blank=True, null=True)

    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Consultation for {self.appointment}"
    
    def save(self, *args, **kwargs):
        if self.start_time and self.end_time:
            self.duration = self.end_time - self.start_time
        super().save(*args, **kwargs)


class Prescription(models.Model):
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name='prescriptions')
    medication_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration = models.CharField(max_length=100)
    refills = models.PositiveSmallIntegerField(default=0)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Pharmacy to fill the prescription (optional)
    pharmacy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prescriptions',
        limit_choices_to={'role': 'pharmco'}
    )
    
    def __str__(self):
        return f"{self.medication_name} for {self.consultation.appointment.patient.username}"


class Message(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='telemedicine_sent_messages'
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='telemedicine_received_messages'
    )
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name='messages',
        null=True,
        blank=True
    )
    content = models.TextField()
    read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Message from {self.sender.username} to {self.receiver.username}"
    
    def mark_as_read(self):
        if not self.read:
            self.read = True
            self.read_at = timezone.now()
            self.save()


class MedicalDocument(models.Model):
    DOCUMENT_TYPES = [
        ('lab_result', 'Lab Result'),
        ('imaging', 'Imaging'),
        ('report', 'Medical Report'),
        ('prescription', 'Prescription'),
        ('other', 'Other'),
    ]
    
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='medical_documents',
        limit_choices_to={'role': 'patient'}
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='uploaded_documents'
    )
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.SET_NULL,
        related_name='documents',
        null=True,
        blank=True
    )
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='medical_documents/%Y/%m/%d/')
    notes = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} for {self.patient.username}"


class ProviderAvailability(models.Model):
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='availability_slots',
        limit_choices_to={'role': 'provider'}
    )
    day_of_week = models.PositiveSmallIntegerField()  # 0=Monday, 6=Sunday
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    
    def __str__(self):
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return f"{self.provider.username} - {days[self.day_of_week]} {self.start_time} to {self.end_time}"


class ProviderTimeOff(models.Model):
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='time_off',
        limit_choices_to={'role': 'provider'}
    )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    reason = models.CharField(max_length=255, blank=True, null=True)
    
    def __str__(self):
        return f"{self.provider.username} - {self.start_date.date()} to {self.end_date.date()}"
