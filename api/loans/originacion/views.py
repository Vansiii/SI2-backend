"""
Vistas para CU-11: Gestionar Originación de Créditos

Proporciona endpoints REST para:
- Crear y gestionar solicitudes de crédito
- Cambiar estados
- Ver timeline y comentarios
- Filtrar y listar solicitudes
"""

from rest_framework import generics, status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q

from ..models import LoanApplication, LoanApplicationStatusHistory, LoanApplicationComment
from .serializers import (
    CreditApplicationCreateSerializer,
    CreditApplicationUpdateDraftSerializer,
    CreditApplicationSubmitSerializer,
    CreditApplicationChangeStatusSerializer,
    CreditApplicationListSerializer,
    CreditApplicationDetailSerializer,
    CreditApplicationBorrowerListSerializer,
    LoanApplicationStatusHistorySerializer,
    LoanApplicationCommentSerializer,
)
from .services import (
    CreditApplicationService,
    CreditApplicationValidationError,
    InvalidStatusTransitionError,
)
from api.core.permissions import HasPermission
from api.core.pagination import StandardResultsSetPagination


class CreditApplicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar solicitudes de crédito (CU-11)
    
    GET /credit-applications/ - Listar solicitudes (según rol)
    POST /credit-applications/ - Crear solicitud en borrador
    GET /credit-applications/{id}/ - Ver detalle
    PATCH /credit-applications/{id}/ - Actualizar borrador
    POST /credit-applications/{id}/submit/ - Enviar solicitud
    POST /credit-applications/{id}/change-status/ - Cambiar estado
    GET /credit-applications/{id}/timeline/ - Ver timeline
    POST /credit-applications/{id}/comments/ - Agregar comentario
    GET /credit-applications/{id}/comments/ - Listar comentarios
    """
    
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['status', 'branch_id', 'product_id', 'identity_verification_status']
    search_fields = ['application_number', 'client__user__email', 'client__user__first_name']
    ordering_fields = ['created_at', 'submitted_at', 'approved_at', 'requested_amount']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Retornar solicitudes según el rol del usuario"""
        user = self.request.user
        queryset = LoanApplication.objects.select_related(
            'client', 'product', 'branch', 'assigned_to', 'reviewed_by', 'approved_by'
        )
        
        # Verificar si es prestatario (cliente)
        if hasattr(user, 'client_profile'):
            # Solo mostrar sus propias solicitudes
            return queryset.filter(
                client=user.client_profile,
                institution=user.client_profile.institution
            )
        
        # Es personal interno - mostrar solicitudes del tenant
        try:
            # Obtener institución del usuario
            membership = user.institution_memberships.filter(
                is_active=True
            ).first()
            if membership:
                queryset = queryset.filter(institution=membership.institution)
                
                # Verificar si está asignado a una sucursal
                branches = user.assigned_branches.filter(
                    institution=membership.institution
                )
                if branches.exists():
                    queryset = queryset.filter(
                        Q(branch__in=branches) | Q(assigned_to=user)
                    )
                
                return queryset
        except:
            pass
        
        return queryset.none()
    
    def get_serializer_class(self):
        """Retornar serializer según la acción"""
        if self.action == 'create':
            return CreditApplicationCreateSerializer
        elif self.action == 'partial_update':
            return CreditApplicationUpdateDraftSerializer
        elif self.action == 'submit':
            return CreditApplicationSubmitSerializer
        elif self.action == 'change_status':
            return CreditApplicationChangeStatusSerializer
        elif self.action == 'list':
            # Mostrar vista simplificada en listas
            user = self.request.user
            if hasattr(user, 'client_profile'):
                return CreditApplicationBorrowerListSerializer
            return CreditApplicationListSerializer
        elif self.action == 'retrieve':
            return CreditApplicationDetailSerializer
        return CreditApplicationDetailSerializer
    
    def create(self, request, *args, **kwargs):
        """Crear una nueva solicitud de crédito"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Obtener la institución del usuario
            if hasattr(request.user, 'client_profile'):
                institution = request.user.client_profile.institution
            else:
                membership = request.user.institution_memberships.filter(
                    is_active=True
                ).first()
                if not membership:
                    return Response(
                        {'error': 'No tiene institución asociada'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                institution = membership.institution
            
            # Crear solicitud usando el servicio
            application = CreditApplicationService.create_draft(
                user=request.user,
                institution=institution,
                data=serializer.validated_data
            )
            
            response_serializer = CreditApplicationDetailSerializer(
                application, context={'request': request}
            )
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        except CreditApplicationValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def partial_update(self, request, pk=None):
        """Actualizar un borrador"""
        application = self.get_object()
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            application = CreditApplicationService.update_draft(
                user=request.user,
                application=application,
                data=serializer.validated_data
            )
            
            response_serializer = CreditApplicationDetailSerializer(
                application, context={'request': request}
            )
            return Response(response_serializer.data)
        
        except CreditApplicationValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Enviar solicitud para evaluación"""
        application = self.get_object()
        
        try:
            application = CreditApplicationService.submit_application(
                user=request.user,
                application=application,
                check_identity=True
            )
            
            response_serializer = CreditApplicationDetailSerializer(
                application, context={'request': request}
            )
            return Response(response_serializer.data)
        
        except CreditApplicationValidationError as e:
            return Response(
                {'error': str(e), 'requires_identity_verification': True},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """Cambiar el estado de la solicitud"""
        application = self.get_object()

        if not request.user.is_staff and not request.user.is_superuser:
            try:
                has_role = request.user.user_roles.filter(
                    institution=application.institution,
                    is_active=True,
                ).exists()
            except Exception:
                has_role = False

            if not has_role:
                return Response(
                    {'error': 'No tiene permisos para cambiar el estado de esta solicitud'},
                    status=status.HTTP_403_FORBIDDEN,
                )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            application = CreditApplicationService.change_status(
                user=request.user,
                application=application,
                new_status=serializer.validated_data['new_status'],
                reason=serializer.validated_data.get('reason', ''),
                metadata={
                    'approved_amount': serializer.validated_data.get('approved_amount'),
                    'approved_term_months': serializer.validated_data.get('approved_term_months'),
                    'approved_interest_rate': serializer.validated_data.get('approved_interest_rate'),
                }
            )
            
            response_serializer = CreditApplicationDetailSerializer(
                application, context={'request': request}
            )
            return Response(response_serializer.data)
        
        except InvalidStatusTransitionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except CreditApplicationValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def timeline(self, request, pk=None):
        """Obtener timeline de la solicitud"""
        application = self.get_object()
        
        # Verificar si es prestatario
        is_borrower = False
        if hasattr(request.user, 'client_profile'):
            is_borrower = (application.client.user_id == request.user.id)
        
        timeline = CreditApplicationService.get_application_timeline(
            application=application,
            borrower_view=is_borrower
        )
        
        serializer = LoanApplicationStatusHistorySerializer(
            timeline, many=True, context={'request': request}
        )
        return Response(serializer.data)
    
    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        """Obtener o crear comentarios"""
        application = self.get_object()
        
        if request.method == 'POST':
            # Crear comentario
            try:
                comment_text = request.data.get('comment')
                is_internal = request.data.get('is_internal', True)
                
                if not comment_text:
                    return Response(
                        {'error': 'El comentario no puede estar vacío'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Verificar permisos
                if hasattr(request.user, 'client_profile'):
                    # Prestatario solo puede crear comentarios públicos
                    is_internal = False
                
                comment = CreditApplicationService.add_comment(
                    user=request.user,
                    application=application,
                    comment_text=comment_text,
                    is_internal=is_internal
                )
                
                serializer = LoanApplicationCommentSerializer(
                    comment, context={'request': request}
                )
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        else:
            # Listar comentarios
            comments = application.comments.all()
            
            # Filtrar según permisos
            if hasattr(request.user, 'client_profile'):
                is_borrower = (application.client.user_id == request.user.id)
                if is_borrower:
                    comments = comments.filter(is_internal=False)
            
            serializer = LoanApplicationCommentSerializer(
                comments, many=True, context={'request': request}
            )
            return Response(serializer.data)
