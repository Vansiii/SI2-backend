"""
URLs para solicitudes de crédito
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .originacion.views import CreditApplicationViewSet

app_name = 'loans'

# Router para CU-11 ViewSet
router = DefaultRouter()
router.register(r'credit-applications', CreditApplicationViewSet, basename='credit-application')

urlpatterns = [
    # URLs del router (CU-11)
    path('', include(router.urls)),
    
    # Rutas legacy (compatibilidad)
    # CRUD básico
    path(
        'legacy/',
        views.LoanApplicationListCreateAPIView.as_view(),
        name='loan-list-create'
    ),
    path(
        'legacy/<int:pk>/',
        views.LoanApplicationDetailAPIView.as_view(),
        name='loan-detail'
    ),
    
    # Acciones de workflow
    path(
        'legacy/<int:pk>/submit/',
        views.LoanApplicationSubmitAPIView.as_view(),
        name='loan-submit'
    ),
    path(
        'legacy/<int:pk>/review/',
        views.LoanApplicationReviewAPIView.as_view(),
        name='loan-review'
    ),
    path(
        'legacy/<int:pk>/calculate-score/',
        views.LoanApplicationCalculateScoreAPIView.as_view(),
        name='loan-calculate-score'
    ),
    path(
        'legacy/<int:pk>/approve/',
        views.LoanApplicationApproveAPIView.as_view(),
        name='loan-approve'
    ),
    path(
        'legacy/<int:pk>/reject/',
        views.LoanApplicationRejectAPIView.as_view(),
        name='loan-reject'
    ),
    path(
        'legacy/<int:pk>/disburse/',
        views.LoanApplicationDisburseAPIView.as_view(),
        name='loan-disburse'
    ),
    
    # Documentos
    path(
        'legacy/<int:application_id>/documents/',
        views.LoanApplicationDocumentListCreateAPIView.as_view(),
        name='loan-documents'
    ),
    
    # Comentarios
    path(
        'legacy/<int:application_id>/comments/',
        views.LoanApplicationCommentListCreateAPIView.as_view(),
        name='loan-comments'
    ),
]
