# telemedicine/tests/test_urls.py
from django.test import TestCase
from django.urls import reverse, resolve
from rest_framework.test import APIRequestFactory

from telemedicine.views import (
    AppointmentViewSet, ConsultationViewSet, PrescriptionViewSet,
    MessageViewSet, MedicalDocumentViewSet, 
    ProviderAvailabilityViewSet, ProviderTimeOffViewSet
)

class URLPatternTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
    
    def test_appointment_list_url(self):
        """Test the URL pattern for appointment list"""
        url = reverse('appointment-list')
        self.assertEqual(url, '/appointments/')
        
        resolver = resolve('/appointments/')
        self.assertEqual(
            resolver.func.__name__,
            AppointmentViewSet.as_view({'get': 'list'}).__name__
        )
    
    def test_appointment_detail_url(self):
        """Test the URL pattern for appointment detail"""
        url = reverse('appointment-detail', args=[1])
        self.assertEqual(url, '/appointments/1/')
        
        resolver = resolve('/appointments/1/')
        self.assertEqual(
            resolver.func.__name__,
            AppointmentViewSet.as_view({'get': 'retrieve'}).__name__
        )
    
    def test_appointment_upcoming_url(self):
        """Test the URL pattern for upcoming appointments"""
        url = reverse('appointment-upcoming')
        self.assertEqual(url, '/appointments/upcoming/')
        
        resolver = resolve('/appointments/upcoming/')
        self.assertEqual(
            resolver.func.__name__,
            AppointmentViewSet.as_view({'get': 'upcoming'}).__name__
        )
    
    def test_appointment_cancel_url(self):
        """Test the URL pattern for cancelling an appointment"""
        url = reverse('appointment-cancel', args=[1])
        self.assertEqual(url, '/appointments/1/cancel/')
        
        resolver = resolve('/appointments/1/cancel/')
        self.assertEqual(
            resolver.func.__name__,
            AppointmentViewSet.as_view({'post': 'cancel'}).__name__
        )
    
    def test_appointment_reschedule_url(self):
        """Test the URL pattern for rescheduling an appointment"""
        url = reverse('appointment-reschedule', args=[1])
        self.assertEqual(url, '/appointments/1/reschedule/')
        
        resolver = resolve('/appointments/1/reschedule/')
        self.assertEqual(
            resolver.func.__name__,
            AppointmentViewSet.as_view({'post': 'reschedule'}).__name__
        )
    
    def test_consultation_list_url(self):
        """Test the URL pattern for consultation list"""
        url = reverse('consultation-list')
        self.assertEqual(url, '/consultations/')
        
        resolver = resolve('/consultations/')
        self.assertEqual(
            resolver.func.__name__,
            ConsultationViewSet.as_view({'get': 'list'}).__name__
        )
    
    def test_consultation_detail_url(self):
        """Test the URL pattern for consultation detail"""
        url = reverse('consultation-detail', args=[1])
        self.assertEqual(url, '/consultations/1/')
        
        resolver = resolve('/consultations/1/')
        self.assertEqual(
            resolver.func.__name__,
            ConsultationViewSet.as_view({'get': 'retrieve'}).__name__
        )
    
    def test_consultation_start_url(self):
        """Test the URL pattern for starting a consultation"""
        url = reverse('consultation-start', args=[1])
        self.assertEqual(url, '/consultations/1/start/')
        
        resolver = resolve('/consultations/1/start/')
        self.assertEqual(
            resolver.func.__name__,
            ConsultationViewSet.as_view({'post': 'start'}).__name__
        )
    
    def test_consultation_end_url(self):
        """Test the URL pattern for ending a consultation"""
        url = reverse('consultation-end', args=[1])
        self.assertEqual(url, '/consultations/1/end/')
        
        resolver = resolve('/consultations/1/end/')
        self.assertEqual(
            resolver.func.__name__,
            ConsultationViewSet.as_view({'post': 'end'}).__name__
        )
    
    def test_consultation_join_info_url(self):
        """Test the URL pattern for getting consultation join info"""
        url = reverse('consultation-join-info', args=[1])
        self.assertEqual(url, '/consultations/1/join_info/')
        
        resolver = resolve('/consultations/1/join_info/')
        self.assertEqual(
            resolver.func.__name__,
            ConsultationViewSet.as_view({'get': 'join_info'}).__name__
        )
    
    def test_prescription_list_url(self):
        """Test the URL pattern for prescription list"""
        url = reverse('prescription-list')
        self.assertEqual(url, '/prescriptions/')
        
        resolver = resolve('/prescriptions/')
        self.assertEqual(
            resolver.func.__name__,
            PrescriptionViewSet.as_view({'get': 'list'}).__name__
        )
    
    def test_prescription_detail_url(self):
        """Test the URL pattern for prescription detail"""
        url = reverse('prescription-detail', args=[1])
        self.assertEqual(url, '/prescriptions/1/')
        
        resolver = resolve('/prescriptions/1/')
        self.assertEqual(
            resolver.func.__name__,
            PrescriptionViewSet.as_view({'get': 'retrieve'}).__name__
        )
    
    def test_message_list_url(self):
        """Test the URL pattern for message list"""
        url = reverse('message-list')
        self.assertEqual(url, '/messages/')
        
        resolver = resolve('/messages/')
        self.assertEqual(
            resolver.func.__name__,
            MessageViewSet.as_view({'get': 'list'}).__name__
        )
    
    def test_message_detail_url(self):
        """Test the URL pattern for message detail"""
        url = reverse('message-detail', args=[1])
        self.assertEqual(url, '/messages/1/')
        
        resolver = resolve('/messages/1/')
        self.assertEqual(
            resolver.func.__name__,
            MessageViewSet.as_view({'get': 'retrieve'}).__name__
        )
    
    def test_message_mark_read_url(self):
        """Test the URL pattern for marking a message as read"""
        url = reverse('message-mark-read', args=[1])
        self.assertEqual(url, '/messages/1/mark_read/')
        
        resolver = resolve('/messages/1/mark_read/')
        self.assertEqual(
            resolver.func.__name__,
            MessageViewSet.as_view({'post': 'mark_read'}).__name__
        )
    
    def test_message_unread_url(self):
        """Test the URL pattern for unread messages"""
        url = reverse('message-unread')
        self.assertEqual(url, '/messages/unread/')
        
        resolver = resolve('/messages/unread/')
        self.assertEqual(
            resolver.func.__name__,
            MessageViewSet.as_view({'get': 'unread'}).__name__
        )
    
    def test_document_list_url(self):
        """Test the URL pattern for document list"""
        url = reverse('medicaldocument-list')
        self.assertEqual(url, '/documents/')
        
        resolver = resolve('/documents/')
        self.assertEqual(
            resolver.func.__name__,
            MedicalDocumentViewSet.as_view({'get': 'list'}).__name__
        )
    
    def test_document_detail_url(self):
        """Test the URL pattern for document detail"""
        url = reverse('medicaldocument-detail', args=[1])
        self.assertEqual(url, '/documents/1/')
        
        resolver = resolve('/documents/1/')
        self.assertEqual(
            resolver.func.__name__,
            MedicalDocumentViewSet.as_view({'get': 'retrieve'}).__name__
        )
    
    def test_availability_list_url(self):
        """Test the URL pattern for availability list"""
        url = reverse('provideravailability-list')
        self.assertEqual(url, '/availability/')
        
        resolver = resolve('/availability/')
        self.assertEqual(
            resolver.func.__name__,
            ProviderAvailabilityViewSet.as_view({'get': 'list'}).__name__
        )
    
    def test_availability_detail_url(self):
        """Test the URL pattern for availability detail"""
        url = reverse('provideravailability-detail', args=[1])
        self.assertEqual(url, '/availability/1/')
        
        resolver = resolve('/availability/1/')
        self.assertEqual(
            resolver.func.__name__,
            ProviderAvailabilityViewSet.as_view({'get': 'retrieve'}).__name__
        )
    
    def test_timeoff_list_url(self):
        """Test the URL pattern for time off list"""
        url = reverse('providertimeoff-list')
        self.assertEqual(url, '/timeoff/')
        
        resolver = resolve('/timeoff/')
        self.assertEqual(
            resolver.func.__name__,
            ProviderTimeOffViewSet.as_view({'get': 'list'}).__name__
        )
    
    def test_timeoff_detail_url(self):
        """Test the URL pattern for time off detail"""
        url = reverse('providertimeoff-detail', args=[1])
        self.assertEqual(url, '/timeoff/1/')
        
        resolver = resolve('/timeoff/1/')
        self.assertEqual(
            resolver.func.__name__,
            ProviderTimeOffViewSet.as_view({'get': 'retrieve'}).__name__
        )
