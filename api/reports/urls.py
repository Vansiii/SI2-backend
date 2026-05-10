"""
URLs para el módulo de reportes.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ReportCatalogViewSet,
    ReportTemplateViewSet,
    ReportGenerationViewSet,
    GeneratedReportViewSet,
    VoiceReportViewSet
)

app_name = 'reports'

router = DefaultRouter()
router.register(r'catalog', ReportCatalogViewSet, basename='report-catalog')
router.register(r'templates', ReportTemplateViewSet, basename='report-template')
router.register(r'generate', ReportGenerationViewSet, basename='report-generation')
router.register(r'generated', GeneratedReportViewSet, basename='generated-report')
router.register(r'voice', VoiceReportViewSet, basename='voice-report')

urlpatterns = [
    path('', include(router.urls)),
]
