# users/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, PatientProfileViewSet, 
    ProviderProfileViewSet, PharmcoProfileViewSet,
    InsurerProfileViewSet
)

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'patient-profiles', PatientProfileViewSet)
router.register(r'provider-profiles', ProviderProfileViewSet)
router.register(r'pharmco-profiles', PharmcoProfileViewSet)
router.register(r'insurer-profiles', InsurerProfileViewSet)

# The API URLs are determined automatically by the router
urlpatterns = [
    path('', include(router.urls)),
]
