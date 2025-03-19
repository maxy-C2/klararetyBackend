# telemedicine/tests/test_models.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, time
from telemedicine.models import (
    Appointment, Consultation, Prescription, 
    Message, MedicalDocument, ProviderAvailability, ProviderTimeOff
)

User = get_user_model()

class AppointmentModelTests(TestCase):
    def setUp(self):
        # Create test users
        self.patient = User.objects.create_user(
            username='testpatient',
            email='patient@example.com',
            password='testpass123',
            role='patient'
        )
        self.provider = User.objects.create_user(
            username='testprovider',
            email='provider@example.com',
            password='testpass123',
            role='provider'
        )
        
        # Create a test appointment
        self.now = timezone.now()
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            provider=self.provider,
            scheduled_time=self.now + timedelta(days=1),
            end_time=self.now + timedelta(days=1, hours=1),
            reason='Annual checkup',
            appointment_type='video_consultation'
        )
    
    def test_appointment_creation(self):
        """Test that appointment was created with the correct attributes"""
        self.assertEqual(self.appointment.patient, self.patient)
        self.assertEqual(self.appointment.provider, self.provider)
        self.assertEqual(self.appointment.status, 'scheduled')
        self.assertEqual(self.appointment.reason, 'Annual checkup')
        self.assertEqual(self.appointment.appointment_type, 'video_consultation')
    
    def test_appointment_string_representation(self):
        """Test the string representation of the appointment"""
        expected_str = f"{self.patient.username} with {self.provider.username} on {self.appointment.scheduled_time}"
        self.assertEqual(str(self.appointment), expected_str)
    
    def test_is_upcoming_method(self):
        """Test that is_upcoming returns the correct value"""
        # Test upcoming appointment
        self.assertTrue(self.appointment.is_upcoming())
        
        # Test completed appointment
        self.appointment.status = 'completed'
        self.appointment.save()
        self.assertFalse(self.appointment.is_upcoming())
        
        # Test past appointment
        self.appointment.status = 'scheduled'
        self.appointment.scheduled_time = self.now - timedelta(days=1)
        self.appointment.end_time = self.now - timedelta(days=1, hours=1)
        self.appointment.save()
        self.assertFalse(self.appointment.is_upcoming())


class ConsultationModelTests(TestCase):
    def setUp(self):
        # Create test users
        self.patient = User.objects.create_user(
            username='testpatient', 
            email='patient@example.com',
            password='testpass123',
            role='patient'
        )
        self.provider = User.objects.create_user(
            username='testprovider',
            email='provider@example.com',
            password='testpass123',
            role='provider'
        )
        
        # Create a test appointment
        self.now = timezone.now()
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            provider=self.provider,
            scheduled_time=self.now + timedelta(days=1),
            end_time=self.now + timedelta(days=1, hours=1),
            reason='Annual checkup',
            appointment_type='video_consultation'
        )
        
        # Create a test consultation
        self.consultation = Consultation.objects.create(
            appointment=self.appointment,
            notes='Patient appears healthy',
            zoom_meeting_id='123456789',
            zoom_meeting_password='password123',
            zoom_join_url='https://zoom.us/j/123456789',
            zoom_start_url='https://zoom.us/s/123456789'
        )
    
    def test_consultation_creation(self):
        """Test that consultation was created with the correct attributes"""
        self.assertEqual(self.consultation.appointment, self.appointment)
        self.assertEqual(self.consultation.notes, 'Patient appears healthy')
        self.assertEqual(self.consultation.zoom_meeting_id, '123456789')
        self.assertEqual(self.consultation.zoom_meeting_password, 'password123')
        self.assertIsNone(self.consultation.start_time)
        self.assertIsNone(self.consultation.end_time)
        self.assertIsNone(self.consultation.duration)
    
    def test_consultation_string_representation(self):
        """Test the string representation of the consultation"""
        expected_str = f"Consultation for {self.appointment}"
        self.assertEqual(str(self.consultation), expected_str)
    
    def test_duration_calculation(self):
        """Test that the duration is calculated correctly when the consultation is saved"""
        # Set start and end times
        start_time = self.now
        end_time = start_time + timedelta(hours=1)
        
        self.consultation.start_time = start_time
        self.consultation.end_time = end_time
        self.consultation.save()
        
        # Check that duration was calculated correctly
        self.assertEqual(self.consultation.duration, timedelta(hours=1))


class PrescriptionModelTests(TestCase):
    def setUp(self):
        # Create test users
        self.patient = User.objects.create_user(
            username='testpatient',
            email='patient@example.com',
            password='testpass123',
            role='patient'
        )
        self.provider = User.objects.create_user(
            username='testprovider',
            email='provider@example.com',
            password='testpass123',
            role='provider'
        )
        self.pharmco = User.objects.create_user(
            username='testpharmco',
            email='pharmacy@example.com',
            password='testpass123',
            role='pharmco'
        )
        
        # Create a test appointment and consultation
        self.now = timezone.now()
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            provider=self.provider,
            scheduled_time=self.now,
            end_time=self.now + timedelta(hours=1),
            reason='Treatment',
            appointment_type='video_consultation'
        )
        
        self.consultation = Consultation.objects.create(
            appointment=self.appointment,
            start_time=self.now,
            end_time=self.now + timedelta(hours=1),
            notes='Patient has a sinus infection'
        )
        
        # Create a test prescription
        self.prescription = Prescription.objects.create(
            consultation=self.consultation,
            medication_name='Amoxicillin',
            dosage='500mg',
            frequency='3 times daily',
            duration='10 days',
            refills=1,
            notes='Take with food',
            pharmacy=self.pharmco
        )
    
    def test_prescription_creation(self):
        """Test that prescription was created with the correct attributes"""
        self.assertEqual(self.prescription.consultation, self.consultation)
        self.assertEqual(self.prescription.medication_name, 'Amoxicillin')
        self.assertEqual(self.prescription.dosage, '500mg')
        self.assertEqual(self.prescription.frequency, '3 times daily')
        self.assertEqual(self.prescription.duration, '10 days')
        self.assertEqual(self.prescription.refills, 1)
        self.assertEqual(self.prescription.notes, 'Take with food')
        self.assertEqual(self.prescription.pharmacy, self.pharmco)
    
    def test_prescription_string_representation(self):
        """Test the string representation of the prescription"""
        expected_str = f"Amoxicillin for {self.patient.username}"
        self.assertEqual(str(self.prescription), expected_str)


class MessageModelTests(TestCase):
    def setUp(self):
        # Create test users
        self.patient = User.objects.create_user(
            username='testpatient',
            email='patient@example.com',
            password='testpass123',
            role='patient'
        )
        self.provider = User.objects.create_user(
            username='testprovider',
            email='provider@example.com',
            password='testpass123',
            role='provider'
        )
        
        # Create a test appointment
        self.now = timezone.now()
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            provider=self.provider,
            scheduled_time=self.now + timedelta(days=1),
            end_time=self.now + timedelta(days=1, hours=1),
            reason='Annual checkup',
            appointment_type='video_consultation'
        )
        
        # Create a test message
        self.message = Message.objects.create(
            sender=self.patient,
            receiver=self.provider,
            appointment=self.appointment,
            content='Do I need to prepare anything for the appointment?'
        )
    
    def test_message_creation(self):
        """Test that message was created with the correct attributes"""
        self.assertEqual(self.message.sender, self.patient)
        self.assertEqual(self.message.receiver, self.provider)
        self.assertEqual(self.message.appointment, self.appointment)
        self.assertEqual(self.message.content, 'Do I need to prepare anything for the appointment?')
        self.assertFalse(self.message.read)
        self.assertIsNone(self.message.read_at)
    
    def test_message_string_representation(self):
        """Test the string representation of the message"""
        expected_str = f"Message from {self.patient.username} to {self.provider.username}"
        self.assertEqual(str(self.message), expected_str)
    
    def test_mark_as_read_method(self):
        """Test that mark_as_read method works correctly"""
        # Message should be unread initially
        self.assertFalse(self.message.read)
        self.assertIsNone(self.message.read_at)
        
        # Mark message as read
        self.message.mark_as_read()
        
        # Check that message is marked as read with timestamp
        self.assertTrue(self.message.read)
        self.assertIsNotNone(self.message.read_at)
        
        # Mark already read message
        original_read_at = self.message.read_at
        self.message.mark_as_read()
        self.assertEqual(self.message.read_at, original_read_at)  # Should not change


class MedicalDocumentModelTests(TestCase):
    def setUp(self):
        # Create test users
        self.patient = User.objects.create_user(
            username='testpatient',
            email='patient@example.com',
            password='testpass123',
            role='patient'
        )
        self.provider = User.objects.create_user(
            username='testprovider',
            email='provider@example.com',
            password='testpass123',
            role='provider'
        )
        
        # Create a test appointment
        self.now = timezone.now()
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            provider=self.provider,
            scheduled_time=self.now,
            end_time=self.now + timedelta(hours=1),
            reason='Annual checkup',
            appointment_type='video_consultation'
        )
        
        # Create a test document
        self.document = MedicalDocument.objects.create(
            patient=self.patient,
            uploaded_by=self.provider,
            appointment=self.appointment,
            document_type='lab_result',
            title='Blood Test Results',
            file='test_file.pdf',
            notes='Routine blood work'
        )
    
    def test_document_creation(self):
        """Test that document was created with the correct attributes"""
        self.assertEqual(self.document.patient, self.patient)
        self.assertEqual(self.document.uploaded_by, self.provider)
        self.assertEqual(self.document.appointment, self.appointment)
        self.assertEqual(self.document.document_type, 'lab_result')
        self.assertEqual(self.document.title, 'Blood Test Results')
        self.assertEqual(self.document.file, 'test_file.pdf')
        self.assertEqual(self.document.notes, 'Routine blood work')
    
    def test_document_string_representation(self):
        """Test the string representation of the document"""
        expected_str = f"Blood Test Results for {self.patient.username}"
        self.assertEqual(str(self.document), expected_str)


class ProviderAvailabilityModelTests(TestCase):
    def setUp(self):
        # Create test provider
        self.provider = User.objects.create_user(
            username='testprovider',
            email='provider@example.com',
            password='testpass123',
            role='provider'
        )
        
        # Create test availability
        self.availability = ProviderAvailability.objects.create(
            provider=self.provider,
            day_of_week=1,  # Tuesday
            start_time=time(9, 0),  # 9:00 AM
            end_time=time(17, 0),  # 5:00 PM
            is_available=True
        )
    
    def test_availability_creation(self):
        """Test that availability was created with the correct attributes"""
        self.assertEqual(self.availability.provider, self.provider)
        self.assertEqual(self.availability.day_of_week, 1)
        self.assertEqual(self.availability.start_time, time(9, 0))
        self.assertEqual(self.availability.end_time, time(17, 0))
        self.assertTrue(self.availability.is_available)
    
    def test_availability_string_representation(self):
        """Test the string representation of the availability"""
        expected_str = f"{self.provider.username} - Tuesday 09:00:00 to 17:00:00"
        self.assertEqual(str(self.availability), expected_str)


class ProviderTimeOffModelTests(TestCase):
    def setUp(self):
        # Create test provider
        self.provider = User.objects.create_user(
            username='testprovider',
            email='provider@example.com',
            password='testpass123',
            role='provider'
        )
        
        # Create test time off
        self.now = timezone.now()
        self.time_off = ProviderTimeOff.objects.create(
            provider=self.provider,
            start_date=self.now + timedelta(days=10),
            end_date=self.now + timedelta(days=15),
            reason='Vacation'
        )
    
    def test_time_off_creation(self):
        """Test that time off was created with the correct attributes"""
        self.assertEqual(self.time_off.provider, self.provider)
        self.assertEqual(self.time_off.start_date, self.now + timedelta(days=10))
        self.assertEqual(self.time_off.end_date, self.now + timedelta(days=15))
        self.assertEqual(self.time_off.reason, 'Vacation')
    
    def test_time_off_string_representation(self):
        """Test the string representation of the time off"""
        expected_str = f"{self.provider.username} - {(self.now + timedelta(days=10)).date()} to {(self.now + timedelta(days=15)).date()}"
        self.assertEqual(str(self.time_off), expected_str)
