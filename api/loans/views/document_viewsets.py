"""
ViewSets para CU-12: Gestión Documental.

Proporciona endpoints REST para:
- Clientes: cargar documentos de sus solicitudes
- Staff: revisar y aprobar/rechazar documentos
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from api.loans.models_documents import LoanApplicationDocumentRequirement
from api.loans.serializers.document_serializers import (
    LoanApplicationDocumentRequirementSerializer,
    DocumentUploadSerializer,
    DocumentReviewSerializer
)
from api.loans.services.document_service import DocumentService
from api.loans.permissions import CanReviewDocuments, IsDocumentOwner


class ClientDocumentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para que clientes gestionen sus documentos.
    
    Endpoints:
    - GET /api/loans/my-documents/ - Listar mis documentos
    - GET /api/loans/my-documents/{id}/ - Detalle de documento
    - POST /api/loans/my-documents/{id}/upload/ - Cargar documento
    """
    
    serializer_class = LoanApplicationDocumentRequirementSerializer
    permission_classes = [IsAuthenticated, IsDocumentOwner]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        # Solo documentos de solicitudes del cliente
        # Verificar si el usuario tiene un cliente asociado
        if not hasattr(self.request.user, 'client'):
            return LoanApplicationDocumentRequirement.objects.none()
        
        return LoanApplicationDocumentRequirement.objects.filter(
            institution=self.request.tenant,
            loan_application__client=self.request.user.client
        ).select_related(
            'product_document_requirement',
            'file_resource',
            'loan_application'
        )

    
    @action(detail=True, methods=['post'])
    def upload(self, request, pk=None):
        """
        Carga un documento.
        
        POST /api/loans/my-documents/{id}/upload/
        Body (multipart/form-data):
        - file: archivo
        - notes: notas (opcional)
        """
        doc_req = self.get_object()
        
        if not request.FILES.get('file'):
            return Response(
                {'error': 'El campo "file" es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = DocumentUploadSerializer(data={
            'document_requirement_id': doc_req.id,
            'file': request.FILES.get('file')
        })
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            updated_doc = DocumentService.upload_document(
                document_requirement_id=doc_req.id,
                file=serializer.validated_data['file'],
                uploaded_by=request.user,
                notes=request.data.get('notes', '')
            )
            
            result_serializer = self.get_serializer(updated_doc)
            return Response(result_serializer.data)
        
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Error al cargar el documento: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StaffDocumentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para que staff revise documentos.
    
    Endpoints:
    - GET /api/loans/staff/documents/ - Listar documentos para revisar
    - GET /api/loans/staff/documents/{id}/ - Detalle
    - POST /api/loans/staff/documents/{id}/review/ - Revisar documento
    
    Query params:
    - status: Filtrar por estado (PENDING, UPLOADED, UNDER_REVIEW, APPROVED, REJECTED)
    """
    
    serializer_class = LoanApplicationDocumentRequirementSerializer
    permission_classes = [IsAuthenticated, CanReviewDocuments]
    
    def get_queryset(self):
        queryset = LoanApplicationDocumentRequirement.objects.filter(
            institution=self.request.tenant
        ).select_related(
            'product_document_requirement',
            'file_resource',
            'loan_application',
            'loan_application__client'
        )

        
        # Filtrar por estado
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        else:
            # Por defecto, mostrar solo los que requieren revisión
            queryset = queryset.filter(
                status__in=['UPLOADED', 'UNDER_REVIEW']
            )
        
        return queryset.order_by('-uploaded_at')
    
    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """
        Revisa un documento.
        
        POST /api/loans/staff/documents/{id}/review/
        Body:
        - action: APPROVED | REJECTED | REQUESTED_REUPLOAD
        - comments: comentarios
        """
        doc_req = self.get_object()
        
        serializer = DocumentReviewSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            reviewed_doc = DocumentService.review_document(
                document_requirement_id=doc_req.id,
                action=serializer.validated_data['action'],
                reviewed_by=request.user,
                comments=serializer.validated_data.get('comments', '')
            )
            
            result_serializer = self.get_serializer(reviewed_doc)
            return Response(result_serializer.data)
        
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Error al revisar el documento: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
