"""
URLs para solicitudes de crédito
"""

from django.urls import path
from . import views

app_name = 'loans'

urlpatterns = [
    # CRUD básico
    path(
        '',
        views.LoanApplicationListCreateAPIView.as_view(),
        name='loan-list-create'
    ),
    path(
        '<int:pk>/',
        views.LoanApplicationDetailAPIView.as_view(),
        name='loan-detail'
    ),
    
    # Acciones de workflow
    path(
        '<int:pk>/submit/',
        views.LoanApplicationSubmitAPIView.as_view(),
        name='loan-submit'
    ),
    path(
        '<int:pk>/review/',
        views.LoanApplicationReviewAPIView.as_view(),
        name='loan-review'
    ),
    path(
        '<int:pk>/calculate-score/',
        views.LoanApplicationCalculateScoreAPIView.as_view(),
        name='loan-calculate-score'
    ),
    path(
        '<int:pk>/approve/',
        views.LoanApplicationApproveAPIView.as_view(),
        name='loan-approve'
    ),
    path(
        '<int:pk>/reject/',
        views.LoanApplicationRejectAPIView.as_view(),
        name='loan-reject'
    ),
    path(
        '<int:pk>/disburse/',
        views.LoanApplicationDisburseAPIView.as_view(),
        name='loan-disburse'
    ),
    
    # Documentos
    path(
        '<int:application_id>/documents/',
        views.LoanApplicationDocumentListCreateAPIView.as_view(),
        name='loan-documents'
    ),
    
    # Comentarios
    path(
        '<int:application_id>/comments/',
        views.LoanApplicationCommentListCreateAPIView.as_view(),
        name='loan-comments'
    ),
]
