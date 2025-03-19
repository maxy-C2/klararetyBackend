# audit/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuditEventViewSet, AuditLogExportViewSet

router = DefaultRouter()
router.register(r'events', AuditEventViewSet)
router.register(r'exports', AuditLogExportViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
