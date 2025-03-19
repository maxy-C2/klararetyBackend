# healthcare/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    MedicalRecordViewSet, AllergyViewSet, MedicationViewSet, ConditionViewSet,
    ImmunizationViewSet, LabTestViewSet, LabResultViewSet, VitalSignViewSet,
    FamilyHistoryViewSet, SurgicalHistoryViewSet, MedicalNoteViewSet,
    MedicalImageViewSet, HealthDocumentViewSet
)

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'medical-records', MedicalRecordViewSet)
router.register(r'allergies', AllergyViewSet)
router.register(r'medications', MedicationViewSet)
router.register(r'conditions', ConditionViewSet)
router.register(r'immunizations', ImmunizationViewSet)
router.register(r'lab-tests', LabTestViewSet)
router.register(r'lab-results', LabResultViewSet)
router.register(r'vital-signs', VitalSignViewSet)
router.register(r'family-history', FamilyHistoryViewSet)
router.register(r'surgical-history', SurgicalHistoryViewSet)
router.register(r'medical-notes', MedicalNoteViewSet)
router.register(r'medical-images', MedicalImageViewSet)
router.register(r'health-documents', HealthDocumentViewSet)


urlpatterns = [
    # API endpoints
    path('', include(router.urls)),
    
]
