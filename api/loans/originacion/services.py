"""
Servicios de lógica de negocio para CU-11: Gestionar Originación de Créditos

Implementa la lógica de negocio para:
- Crear solicitudes de crédito (borrador)
- Enviar solicitudes para evaluación
- Cambiar estados de solicitudes
- Validar reglas de negocio
- Generar timeline de eventos
- Integración con CU-13 (Verificación de Identidad)
"""

from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from decimal import Decimal
from typing import Optional, Dict, Any

from ..models import (
    LoanApplication,
    LoanApplicationStatusHistory,
    LoanApplicationComment,
)
from api.audit.models import AuditLog
from api.identity_verification.models import IdentityVerification

User = get_user_model()


class CreditApplicationValidationError(Exception):
    """Excepción para errores de validación de solicitudes de crédito"""
    pass


class InvalidStatusTransitionError(Exception):
    """Excepción para transiciones de estado inválidas"""
    pass


class CreditApplicationService:
    """
    Servicio para gestionar solicitudes de crédito originadas (CU-11)
    
    Proporciona métodos para:
    - Crear solicitudes en borrador
    - Actualizar borradores
    - Enviar solicitudes
    - Cambiar estados
    - Generar timeline
    - Auditar acciones
    """
    
    # Transiciones de estado válidas
    VALID_TRANSITIONS = {
        LoanApplication.Status.DRAFT: [
            LoanApplication.Status.SUBMITTED,
            LoanApplication.Status.CANCELLED,
        ],
        LoanApplication.Status.SUBMITTED: [
            LoanApplication.Status.IN_REVIEW,
            LoanApplication.Status.OBSERVED,
            LoanApplication.Status.REJECTED,
            LoanApplication.Status.CANCELLED,
        ],
        LoanApplication.Status.IN_REVIEW: [
            LoanApplication.Status.OBSERVED,
            LoanApplication.Status.APPROVED,
            LoanApplication.Status.REJECTED,
            LoanApplication.Status.SUBMITTED,
        ],
        LoanApplication.Status.OBSERVED: [
            LoanApplication.Status.SUBMITTED,
            LoanApplication.Status.IN_REVIEW,
            LoanApplication.Status.REJECTED,
            LoanApplication.Status.CANCELLED,
        ],
        LoanApplication.Status.APPROVED: [
            LoanApplication.Status.DISBURSED,
            LoanApplication.Status.CANCELLED,
        ],
        LoanApplication.Status.REJECTED: [],
        LoanApplication.Status.DISBURSED: [],
        LoanApplication.Status.CANCELLED: [],
        # Para compatibilidad con estado antiguo
        LoanApplication.Status.UNDER_REVIEW: [
            LoanApplication.Status.OBSERVED,
            LoanApplication.Status.APPROVED,
            LoanApplication.Status.REJECTED,
            LoanApplication.Status.SUBMITTED,
        ],
    }

    @staticmethod
    def _has_internal_role(user: User, institution) -> bool:
        """Verifica si el usuario tiene un rol interno activo en la institución."""
        if user.is_staff or user.is_superuser:
            return True

        try:
            return user.user_roles.filter(
                institution=institution,
                is_active=True,
            ).exists()
        except Exception:
            return False
    
    @staticmethod
    @transaction.atomic
    def create_draft(user: User, institution, data: Dict[str, Any]) -> LoanApplication:
        """
        Crear una nueva solicitud de crédito en borrador.
        
        Args:
            user: Usuario que crea la solicitud (prestatario)
            institution: Institución financiera (tenant)
            data: Datos de la solicitud
            
        Returns:
            LoanApplication: Solicitud creada en estado DRAFT
            
        Raises:
            CreditApplicationValidationError: Si los datos son inválidos
        """
        try:
            # Obtener el cliente del usuario
            client = user.client_profile
        except Exception:
            raise CreditApplicationValidationError("El usuario no tiene un perfil de cliente asociado")
        
        # Validar que el cliente pertenece a la institución
        if client.institution_id != institution.id:
            raise CreditApplicationValidationError("El cliente no pertenece a esta institución")
        
        # Crear la solicitud
        application = LoanApplication(
            institution=institution,
            client=client,
            product_id=data.get('product_id'),
            requested_amount=data.get('requested_amount'),
            term_months=data.get('term_months'),
            purpose=data.get('purpose', ''),
            monthly_income=data.get('monthly_income'),
            employment_type=data.get('employment_type'),
            employment_description=data.get('employment_description', ''),
            additional_data=data.get('additional_data', {}),
            branch_id=data.get('branch_id'),
            status=LoanApplication.Status.DRAFT,
            created_by=user,
            updated_by=user,
        )
        
        application.save()
        
        # Registrar auditoría
        AuditLog.objects.create(
            user=user,
            action='create',
            resource_type='LoanApplication',
            resource_id=application.id,
            institution=institution,
            description=f'Solicitud de crédito creada en borrador por {user.email}',
            metadata={
                'application_number': application.application_number,
                'amount': str(application.requested_amount),
                'client_id': client.id,
            }
        )
        
        return application
    
    @staticmethod
    @transaction.atomic
    def update_draft(
        user: User,
        application: LoanApplication,
        data: Dict[str, Any]
    ) -> LoanApplication:
        """
        Actualizar una solicitud en estado DRAFT.
        
        Args:
            user: Usuario que actualiza
            application: Solicitud a actualizar
            data: Nuevos datos
            
        Returns:
            LoanApplication: Solicitud actualizada
            
        Raises:
            CreditApplicationValidationError: Si la solicitud no está en DRAFT
        """
        if application.status != LoanApplication.Status.DRAFT:
            raise CreditApplicationValidationError(
                f"Solo se pueden actualizar solicitudes en borrador. "
                f"Estado actual: {application.get_status_display()}"
            )
        
        # Solo el propietario puede editar su solicitud, o usuario de staff
        if application.client.user_id != user.id:
            # Verificar si es staff con permiso
            try:
                if not user.user_roles.filter(
                    institution=application.institution,
                    is_active=True
                ).exists():
                    raise CreditApplicationValidationError(
                        "No tiene permiso para actualizar esta solicitud"
                    )
            except:
                raise CreditApplicationValidationError(
                    "No tiene permiso para actualizar esta solicitud"
                )
        
        # Actualizar campos permitidos
        allowed_fields = [
            'product_id', 'requested_amount', 'term_months', 'purpose',
            'monthly_income', 'employment_type', 'employment_description',
            'additional_data', 'branch_id'
        ]
        
        for field in allowed_fields:
            if field in data:
                setattr(application, field, data[field])
        
        application.updated_by = user
        application.save()
        
        # Registrar auditoría
        AuditLog.objects.create(
            user=user,
            action='update_partial',
            resource_type='LoanApplication',
            resource_id=application.id,
            institution=application.institution,
            description=f'Solicitud de crédito actualizada por {user.email}',
            metadata={
                'application_number': application.application_number,
                'fields_updated': list(data.keys()),
            }
        )
        
        return application
    
    @staticmethod
    @transaction.atomic
    def submit_application(
        user: User,
        application: LoanApplication,
        check_identity: bool = True
    ) -> LoanApplication:
        """
        Enviar solicitud para evaluación.
        
        Valida que todos los campos requeridos estén completos y que se cumplan
        las reglas de negocio antes de permitir el envío.
        
        Args:
            user: Usuario que envía
            application: Solicitud a enviar
            check_identity: Si True, verifica el estado de identidad (CU-13)
            
        Returns:
            LoanApplication: Solicitud enviada
            
        Raises:
            CreditApplicationValidationError: Si no se cumplen requisitos
        """
        # Validar estado actual
        if application.status != LoanApplication.Status.DRAFT:
            raise CreditApplicationValidationError(
                f"Solo se pueden enviar solicitudes en borrador. "
                f"Estado actual: {application.get_status_display()}"
            )
        
        # Validar que el usuario sea el dueño o staff
        if application.client.user_id != user.id:
            try:
                if not user.user_roles.filter(
                    institution=application.institution,
                    is_active=True
                ).exists():
                    raise CreditApplicationValidationError(
                        "No tiene permiso para enviar esta solicitud"
                    )
            except:
                raise CreditApplicationValidationError(
                    "No tiene permiso para enviar esta solicitud"
                )
        
        # Validaciones de campos requeridos
        CreditApplicationService._validate_required_fields(application)
        
        # Validaciones de producto
        CreditApplicationService._validate_product_rules(application)
        
        # Validaciones de identidad (CU-13 integration)
        if check_identity:
            identity_status = CreditApplicationService._validate_identity_verification(
                application
            )
            application.identity_verification_status = identity_status
        
        # Cambiar estado
        application.status = LoanApplication.Status.SUBMITTED
        application.submitted_at = timezone.now()
        application.updated_by = user
        application.save()
        
        # Crear evento en timeline
        CreditApplicationService._create_timeline_event(
            application=application,
            previous_status=LoanApplication.Status.DRAFT,
            new_status=LoanApplication.Status.SUBMITTED,
            actor=user,
            title='Solicitud enviada',
            description='El prestatario envió la solicitud de crédito para evaluación',
            is_visible_to_borrower=True
        )
        
        # Registrar auditoría
        AuditLog.objects.create(
            user=user,
            action='system_action',
            resource_type='LoanApplication',
            resource_id=application.id,
            institution=application.institution,
            description=f'Solicitud de crédito enviada por {user.email}',
            metadata={
                'application_number': application.application_number,
                'new_status': LoanApplication.Status.SUBMITTED,
                'event': 'Application submitted for review'
            }
        )
        
        return application
    
    @staticmethod
    @transaction.atomic
    def change_status(
        user: User,
        application: LoanApplication,
        new_status: str,
        reason: str = '',
        metadata: Optional[Dict] = None
    ) -> LoanApplication:
        """
        Cambiar el estado de una solicitud.
        
        Valida que la transición sea permitida y registra el evento en timeline.
        
        Args:
            user: Usuario que cambia el estado (debe ser staff)
            application: Solicitud
            new_status: Nuevo estado
            reason: Motivo del cambio
            metadata: Metadata adicional
            
        Returns:
            LoanApplication: Solicitud con estado actualizado
            
        Raises:
            InvalidStatusTransitionError: Si la transición no es válida
            CreditApplicationValidationError: Si hay otros errores
        """
        if not CreditApplicationService._has_internal_role(user, application.institution):
            raise CreditApplicationValidationError(
                'No tiene permisos para cambiar el estado de esta solicitud'
            )

        # Validar transición
        current_status = application.status
        valid_next_statuses = CreditApplicationService.VALID_TRANSITIONS.get(
            current_status, []
        )
        
        if new_status not in valid_next_statuses:
            raise InvalidStatusTransitionError(
                f"Transición inválida de {current_status} a {new_status}. "
                f"Transiciones permitidas: {valid_next_statuses}"
            )
        
        # Guardar estado anterior
        previous_status = application.status
        
        # Actualizar según el nuevo estado
        if new_status == LoanApplication.Status.IN_REVIEW:
            application.status = new_status
            application.reviewed_by = user
            application.reviewed_at = timezone.now()
            title = 'Revisión iniciada'
            description = 'El personal inició la revisión de la solicitud'
        elif new_status == LoanApplication.Status.OBSERVED:
            application.status = new_status
            application.observation_reason = reason
            title = 'Solicitud observada'
            description = f'Observación: {reason}'
        elif new_status == LoanApplication.Status.APPROVED:
            application.status = new_status
            application.approved_at = timezone.now()
            application.approved_by = user
            title = 'Solicitud aprobada'
            description = 'La solicitud fue aprobada exitosamente'
        elif new_status == LoanApplication.Status.REJECTED:
            application.status = new_status
            application.rejection_reason = reason
            application.rejected_at = timezone.now()
            title = 'Solicitud rechazada'
            description = f'Motivo del rechazo: {reason}'
        elif new_status == LoanApplication.Status.CANCELLED:
            application.status = new_status
            title = 'Solicitud cancelada'
            description = 'La solicitud fue cancelada'
        else:
            application.status = new_status
            title = f'Estado cambiado a {new_status}'
            description = reason or ''
        
        application.updated_by = user
        application.save()
        
        # Crear evento en timeline
        CreditApplicationService._create_timeline_event(
            application=application,
            previous_status=previous_status,
            new_status=new_status,
            actor=user,
            title=title,
            description=description,
            is_visible_to_borrower=(
                new_status in [
                    LoanApplication.Status.APPROVED,
                    LoanApplication.Status.REJECTED,
                    LoanApplication.Status.OBSERVED,
                ]
            ),
            metadata=metadata or {}
        )
        
        # Registrar auditoría
        action_map = {
            LoanApplication.Status.APPROVED: 'loan_approve',
            LoanApplication.Status.REJECTED: 'loan_reject',
            LoanApplication.Status.IN_REVIEW: 'update_partial',
        }
        
        audit_action = action_map.get(new_status, 'update_full')
        
        AuditLog.objects.create(
            user=user,
            action=audit_action,
            resource_type='LoanApplication',
            resource_id=application.id,
            institution=application.institution,
            description=(
                f'Estado de solicitud cambiado de {previous_status} a {new_status}'
            ),
            metadata={
                'application_number': application.application_number,
                'previous_status': previous_status,
                'new_status': new_status,
                'reason': reason,
            }
        )
        
        return application
    
    @staticmethod
    def _validate_required_fields(application: LoanApplication) -> None:
        """
        Validar que todos los campos requeridos estén completos.
        
        Raises:
            CreditApplicationValidationError: Si faltan campos requeridos
        """
        required_fields = {
            'product_id': 'Producto Crediticio',
            'requested_amount': 'Monto Solicitado',
            'term_months': 'Plazo',
            'purpose': 'Propósito del Crédito',
            'monthly_income': 'Ingreso Mensual',
            'employment_type': 'Tipo de Empleo',
        }
        
        missing_fields = []
        for field, label in required_fields.items():
            value = getattr(application, field, None)
            if not value:
                missing_fields.append(label)
        
        if missing_fields:
            raise CreditApplicationValidationError(
                f"Campos requeridos incompletos: {', '.join(missing_fields)}"
            )
    
    @staticmethod
    def _validate_product_rules(application: LoanApplication) -> None:
        """
        Validar que la solicitud cumple con las reglas del producto.
        
        Raises:
            CreditApplicationValidationError: Si no cumple las reglas
        """
        product = application.product
        
        if not product.is_active:
            raise CreditApplicationValidationError(
                "El producto crediticio no está activo"
            )
        
        # Validar monto
        if product.min_amount and application.requested_amount < product.min_amount:
            raise CreditApplicationValidationError(
                f"El monto solicitado (${application.requested_amount}) "
                f"es menor al mínimo permitido (${product.min_amount})"
            )
        
        if product.max_amount and application.requested_amount > product.max_amount:
            raise CreditApplicationValidationError(
                f"El monto solicitado (${application.requested_amount}) "
                f"excede el máximo permitido (${product.max_amount})"
            )
        
        # Validar plazo
        if product.min_term_months and application.term_months < product.min_term_months:
            raise CreditApplicationValidationError(
                f"El plazo solicitado ({application.term_months} meses) "
                f"es menor al mínimo permitido ({product.min_term_months} meses)"
            )
        
        if product.max_term_months and application.term_months > product.max_term_months:
            raise CreditApplicationValidationError(
                f"El plazo solicitado ({application.term_months} meses) "
                f"excede el máximo permitido ({product.max_term_months} meses)"
            )
    
    @staticmethod
    def _validate_identity_verification(
        application: LoanApplication
    ) -> str:
        """
        Validar el estado de verificación de identidad (CU-13).
        
        Returns:
            str: Estado de verificación de identidad
            
        Raises:
            CreditApplicationValidationError: Si la identidad no está verificada
        """
        try:
            # Obtener la verificación más reciente
            verification = IdentityVerification.objects.filter(
                user=application.client.user,
                institution=application.institution
            ).latest('created_at')
            
            if verification.status == IdentityVerification.Status.APPROVED:
                return LoanApplication.IdentityVerificationStatus.APPROVED
            elif verification.status == IdentityVerification.Status.PENDING:
                return LoanApplication.IdentityVerificationStatus.PENDING
            elif verification.status == IdentityVerification.Status.IN_PROGRESS:
                return LoanApplication.IdentityVerificationStatus.IN_PROGRESS
            elif verification.status == IdentityVerification.Status.DECLINED:
                raise CreditApplicationValidationError(
                    "La verificación de identidad fue rechazada. "
                    "Debe completar una nueva verificación."
                )
            else:
                return LoanApplication.IdentityVerificationStatus.MANUAL_REVIEW
        except IdentityVerification.DoesNotExist:
            # No hay verificación, solicitar que inicie una
            raise CreditApplicationValidationError(
                "Debe completar la verificación de identidad antes de enviar la solicitud"
            )
    
    @staticmethod
    def _create_timeline_event(
        application: LoanApplication,
        previous_status: str,
        new_status: str,
        actor: User,
        title: str,
        description: str,
        is_visible_to_borrower: bool = True,
        metadata: Optional[Dict] = None
    ) -> LoanApplicationStatusHistory:
        """
        Crear un evento en el timeline de la solicitud.
        
        Args:
            application: Solicitud
            previous_status: Estado anterior
            new_status: Nuevo estado
            actor: Usuario que causó el cambio
            title: Título del evento
            description: Descripción del evento
            is_visible_to_borrower: Si es visible para el prestatario
            metadata: Metadata adicional
            
        Returns:
            LoanApplicationStatusHistory: Evento creado
        """
        # Obtener rol del actor si es posible
        actor_role = 'BORROWER'
        try:
            user_role = actor.user_roles.filter(
                institution=application.institution,
                is_active=True
            ).first()
            if user_role:
                actor_role = user_role.role.name
        except:
            pass
        
        event = LoanApplicationStatusHistory.objects.create(
            institution=application.institution,
            application=application,
            previous_status=previous_status,
            new_status=new_status,
            title=title,
            description=description,
            actor=actor,
            actor_role=actor_role,
            is_visible_to_borrower=is_visible_to_borrower,
            metadata=metadata or {}
        )
        
        return event
    
    @staticmethod
    @transaction.atomic
    def add_comment(
        user: User,
        application: LoanApplication,
        comment_text: str,
        is_internal: bool = True
    ) -> LoanApplicationComment:
        """
        Agregar un comentario a una solicitud.
        
        Args:
            user: Usuario que comenta
            application: Solicitud
            comment_text: Texto del comentario
            is_internal: Si es solo visible internamente
            
        Returns:
            LoanApplicationComment: Comentario creado
        """
        comment = LoanApplicationComment.objects.create(
            institution=application.institution,
            application=application,
            user=user,
            comment=comment_text,
            is_internal=is_internal
        )
        
        return comment
    
    @staticmethod
    def get_application_timeline(
        application: LoanApplication,
        borrower_view: bool = False
    ) -> list:
        """
        Obtener el timeline de una solicitud.
        
        Args:
            application: Solicitud
            borrower_view: Si True, solo eventos visibles para prestatario
            
        Returns:
            list: Lista de eventos
        """
        queryset = LoanApplicationStatusHistory.objects.filter(
            application=application
        )
        
        if borrower_view:
            queryset = queryset.filter(is_visible_to_borrower=True)
        
        return queryset.order_by('created_at')
