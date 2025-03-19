# telemedicine/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AppointmentViewSet, ConsultationViewSet, PrescriptionViewSet,
    MessageViewSet, MedicalDocumentViewSet, 
    ProviderAvailabilityViewSet, ProviderTimeOffViewSet
)

router = DefaultRouter()
router.register(r'appointments', AppointmentViewSet)
router.register(r'consultations', ConsultationViewSet)
router.register(r'prescriptions', PrescriptionViewSet)
router.register(r'messages', MessageViewSet)
router.register(r'documents', MedicalDocumentViewSet)
router.register(r'availability', ProviderAvailabilityViewSet)
router.register(r'timeoff', ProviderTimeOffViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
