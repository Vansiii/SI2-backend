"""
Servicio para gestión del workflow de solicitudes de crédito.

Maneja transiciones de estado, validaciones, acciones automatizadas y escalamiento.
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


class WorkflowService:
    """
    Servicio para gestión del workflow de solicitudes.
    
    Maneja la lógica de negocio para:
    - Transiciones de estado
    - Validación de transiciones
    - Acciones automatizadas
    - Escalamiento por timeout
    - Avance automático basado en condiciones
    """
    
    # Definición de transiciones válidas por defecto
    VALID_TRANSITIONS = {
        'DRAFT': ['SUBMITTED'],
        'SUBMITTED': ['IN_REVIEW', 'DOCUMENTS', 'REJECTED'],  # Agregar IN_REVIEW
        'IN_REVIEW': ['DOCUMENTS', 'OBSERVED', 'REJECTED'],  # Nuevo estado intermedio
        'DOCUMENTS': ['KYC', 'REJECTED'],
        'KYC': ['SCORING', 'REJECTED'],
        'SCORING': ['REVIEW', 'APPROVED', 'REJECTED'],
        'REVIEW': ['APPROVED', 'REJECTED'],
        'APPROVED': ['DISBURSED'],
        'REJECTED': [],  # Estado final
        'DISBURSED': [],  # Estado final
        'CANCELLED': [],  # Estado final
        'OBSERVED': ['IN_REVIEW', 'DOCUMENTS', 'REJECTED'],  # Puede volver a revisión o documentos
    }
    
    @staticmethod
    @transaction.atomic
    def transition_state(
        loan_application_id: int,
        to_status: str,
        changed_by=None,
        notes: str = '',
        client_message: str = '',
        requires_client_action: bool = False,
        action_description: str = '',
        action_url: str = '',
        send_notification: bool = True
    ):
        """
        Realiza una transición de estado de una solicitud.
        
        FASE 2 - Backend Robusto:
        - Logging mejorado con prefijo [WORKFLOW]
        - Manejo robusto de errores
        - Validación exhaustiva
        
        Args:
            loan_application_id: ID de la solicitud
            to_status: Estado destino
            changed_by: Usuario que realiza el cambio (None para sistema)
            notes: Notas internas
            client_message: Mensaje para el cliente
            requires_client_action: Si requiere acción del cliente
            action_description: Descripción de la acción
            action_url: URL de la acción
            send_notification: Si enviar notificación
        
        Returns:
            LoanApplication: Solicitud actualizada
        
        Raises:
            ValidationError: Si la transición no es válida
        """
        from api.loans.models import LoanApplication
        
        # Obtener solicitud con lock para evitar race conditions
        try:
            application = LoanApplication.objects.select_for_update().get(
                id=loan_application_id
            )
        except LoanApplication.DoesNotExist:
            logger.error(f"[WORKFLOW] Solicitud {loan_application_id} no encontrada")
            raise ValidationError(f"Solicitud {loan_application_id} no encontrada")
        
        from_status = application.status
        
        logger.info(
            f"[WORKFLOW] Iniciando transición: Solicitud {loan_application_id} "
            f"de {from_status} a {to_status}"
        )
        
        # Validar transición
        try:
            WorkflowService.validate_transition(application, to_status)
        except ValidationError as e:
            logger.error(
                f"[WORKFLOW] Transición inválida para solicitud {loan_application_id}: {str(e)}"
            )
            raise
        
        # Ejecutar acciones pre-transición
        try:
            WorkflowService._execute_pre_transition_actions(application, to_status)
        except Exception as e:
            logger.error(
                f"[WORKFLOW] Error en acciones pre-transición: {str(e)}",
                exc_info=True
            )
            # Continuar con la transición aunque fallen las acciones pre
        
        # Obtener configuración de la etapa destino
        stage_config = WorkflowService._get_stage_config(application, to_status)
        
        # Usar mensaje de la configuración si no se proporciona uno
        if not client_message and stage_config:
            client_message = stage_config.client_message_template or \
                           WorkflowService._get_default_message(to_status)
        elif not client_message:
            client_message = WorkflowService._get_default_message(to_status)
        
        # Usar configuración de acción del cliente si está disponible
        if stage_config and stage_config.requires_client_action:
            requires_client_action = True
            action_description = action_description or stage_config.client_action_description
            action_url = action_url or stage_config.client_action_url
        
        # Crear evento en timeline
        try:
            application.add_timeline_event(
                to_status=to_status,
                changed_by=changed_by,
                notes=notes,
                is_visible_to_client=True,
                client_message=client_message,
                requires_client_action=requires_client_action,
                action_description=action_description,
                action_url=action_url,
                send_notification=send_notification
            )
        except Exception as e:
            logger.error(
                f"[WORKFLOW] Error creando evento en timeline: {str(e)}",
                exc_info=True
            )
            raise
        
        # Ejecutar acciones post-transición
        try:
            WorkflowService._execute_post_transition_actions(application, to_status)
        except Exception as e:
            logger.error(
                f"[WORKFLOW] Error en acciones post-transición: {str(e)}",
                exc_info=True
            )
            # Continuar aunque fallen las acciones post
        
        # Verificar si puede avanzar automáticamente
        if stage_config and stage_config.auto_advance_enabled:
            WorkflowService._schedule_auto_advance_check(application)
        
        logger.info(
            f"[WORKFLOW] Transición completada: Solicitud {loan_application_id} "
            f"ahora en estado {to_status}"
        )
        
        return application
    
    @staticmethod
    def validate_transition(loan_application, to_status: str):
        """
        Valida que una transición sea válida basándose en el workflow dinámico.
        
        VALIDACIÓN DINÁMICA:
        - Verifica que el estado destino esté en los estados válidos siguientes
        - Valida prerrequisitos basándose en el ORDEN del workflow configurado
        - NO asume un orden fijo (ej: documentos antes de KYC)
        
        Args:
            loan_application: LoanApplication instance
            to_status: Estado destino
        
        Raises:
            ValidationError: Si la transición no es válida
        """
        from_status = loan_application.status
        
        # Obtener transiciones válidas desde la configuración del workflow
        valid_next_states = WorkflowService._get_valid_next_states(loan_application)
        
        if to_status not in valid_next_states:
            raise ValidationError(
                f"Transición no válida: {from_status} → {to_status}. "
                f"Estados válidos desde {from_status}: {', '.join(valid_next_states)}"
            )
        
        # Validaciones dinámicas basadas en el orden del workflow
        WorkflowService._validate_prerequisites_dynamic(loan_application, to_status)
        
        # Validaciones específicas de estados finales
        if to_status == 'APPROVED':
            # Verificar que tenga score calculado (si aplica)
            if hasattr(loan_application, 'credit_score') and not loan_application.credit_score:
                raise ValidationError(
                    "No se puede aprobar sin calcular el score crediticio"
                )
        
        if to_status == 'DISBURSED':
            # Verificar que esté aprobado
            if loan_application.status != 'APPROVED':
                raise ValidationError(
                    "Solo se pueden desembolsar solicitudes aprobadas"
                )
    
    @staticmethod
    def _validate_prerequisites_dynamic(loan_application, to_status: str):
        """
        Valida prerrequisitos de forma dinámica basándose en el orden del workflow.
        
        Esta validación verifica que todas las etapas ANTERIORES en el workflow
        estén completadas antes de permitir avanzar a la etapa destino.
        
        Ejemplo:
        - Si el workflow es: SUBMITTED → DOCUMENTS → KYC → SCORING
          Y quiero ir a KYC, valida que DOCUMENTS esté completo
        
        - Si el workflow es: SUBMITTED → KYC → DOCUMENTS → SCORING
          Y quiero ir a DOCUMENTS, valida que KYC esté completo
        
        Args:
            loan_application: LoanApplication instance
            to_status: Estado destino
        
        Raises:
            ValidationError: Si faltan prerrequisitos
        """
        # Si no hay workflow configurado, no validar prerrequisitos
        if not loan_application.rule_set_snapshot:
            logger.warning(
                f"[WORKFLOW] Solicitud {loan_application.id} sin rule_set_snapshot. "
                f"Saltando validación de prerrequisitos."
            )
            return
        
        # Obtener todas las etapas del workflow ordenadas
        workflow_stages = loan_application.rule_set_snapshot.workflow_stages.order_by('order')
        
        # Encontrar la posición de la etapa destino
        target_stage = workflow_stages.filter(stage_code=to_status).first()
        if not target_stage:
            # Si no está en el workflow, permitir (puede ser un estado especial)
            return
        
        # Obtener todas las etapas anteriores a la etapa destino
        previous_stages = workflow_stages.filter(order__lt=target_stage.order)
        
        # Validar que las etapas anteriores estén completadas
        for stage in previous_stages:
            # Saltar etapas opcionales o de sistema
            if stage.stage_code in ['DRAFT', 'SUBMITTED', 'IN_REVIEW', 'REVIEW', 'OBSERVED']:
                continue
            
            # Validar según el tipo de etapa
            if stage.stage_code == 'DOCUMENTS':
                if loan_application.documents_status != 'COMPLETE':
                    raise ValidationError([
                        f"No se puede pasar a {target_stage.stage_name} sin completar los documentos obligatorios"
                    ])
            
            elif stage.stage_code == 'KYC':
                if loan_application.identity_verification_status != 'APPROVED':
                    raise ValidationError([
                        f"No se puede pasar a {target_stage.stage_name} sin completar la verificación de identidad"
                    ])
            
            elif stage.stage_code == 'SCORING':
                if not hasattr(loan_application, 'credit_score') or not loan_application.credit_score:
                    raise ValidationError([
                        f"No se puede pasar a {target_stage.stage_name} sin completar el scoring crediticio"
                    ])
        
        logger.info(
            f"[WORKFLOW] Prerrequisitos validados para transición a {to_status} "
            f"en solicitud {loan_application.id}"
        )
    
    @staticmethod
    def _get_valid_next_states(loan_application) -> List[str]:
        """
        Obtiene los estados válidos siguientes para una solicitud.
        
        Primero intenta obtenerlos de la configuración del workflow,
        si no está disponible usa las transiciones por defecto.
        
        Args:
            loan_application: LoanApplication instance
            
        Returns:
            List[str]: Lista de códigos de estados válidos
        """
        from_status = loan_application.status
        
        # Intentar obtener desde la configuración del workflow
        if loan_application.rule_set_snapshot:
            current_stage = loan_application.rule_set_snapshot.workflow_stages.filter(
                stage_code=from_status
            ).first()
            
            if current_stage:
                valid_states = []
                if current_stage.next_stage_on_success:
                    valid_states.append(current_stage.next_stage_on_success)
                if current_stage.next_stage_on_failure:
                    valid_states.append(current_stage.next_stage_on_failure)
                
                # Si hay configuración, usarla
                if valid_states:
                    return valid_states
        
        # Fallback a transiciones por defecto
        return WorkflowService.VALID_TRANSITIONS.get(from_status, [])
    
    @staticmethod
    def _get_stage_config(loan_application, stage_code: str):
        """
        Obtiene la configuración de una etapa del workflow.
        
        Args:
            loan_application: LoanApplication instance
            stage_code: Código de la etapa
            
        Returns:
            WorkflowStageDefinition or None
        """
        if not loan_application.rule_set_snapshot:
            return None
        
        return loan_application.rule_set_snapshot.workflow_stages.filter(
            stage_code=stage_code
        ).first()
    
    @staticmethod
    def _execute_pre_transition_actions(loan_application, to_status: str):
        """
        Ejecuta acciones antes de la transición.
        
        Args:
            loan_application: LoanApplication instance
            to_status: Estado destino
        """
        logger.info(f"Ejecutando acciones pre-transición para {to_status}")
        
        if to_status == 'SCORING':
            # Iniciar cálculo de score
            try:
                from api.loans.services.scoring_service import ScoringService
                ScoringService.calculate_score(loan_application)
                logger.info(f"Score calculado para solicitud {loan_application.id}")
            except Exception as e:
                logger.error(f"Error calculando score: {str(e)}")
        
        if to_status == 'APPROVED':
            # Generar contrato (si existe el servicio)
            try:
                from api.loans.services.contract_service import ContractService
                ContractService.generate_contract(loan_application)
                logger.info(f"Contrato generado para solicitud {loan_application.id}")
            except ImportError:
                logger.warning("ContractService no disponible")
            except Exception as e:
                logger.error(f"Error generando contrato: {str(e)}")
    
    @staticmethod
    def _execute_post_transition_actions(loan_application, to_status: str):
        """
        Ejecuta acciones después de la transición.
        
        Args:
            loan_application: LoanApplication instance
            to_status: Estado destino
        """
        logger.info(f"Ejecutando acciones post-transición para {to_status}")
        
        if to_status == 'DISBURSED':
            # Registrar desembolso
            try:
                from api.loans.services.disbursement_service import DisbursementService
                DisbursementService.record_disbursement(loan_application)
                logger.info(f"Desembolso registrado para solicitud {loan_application.id}")
            except ImportError:
                logger.warning("DisbursementService no disponible")
            except Exception as e:
                logger.error(f"Error registrando desembolso: {str(e)}")
        
        if to_status == 'REJECTED':
            # Notificar rechazo
            try:
                from api.notifications.services import NotificationService
                NotificationService.send_rejection_notification(loan_application)
                logger.info(f"Notificación de rechazo enviada para solicitud {loan_application.id}")
            except ImportError:
                logger.warning("NotificationService no disponible")
            except Exception as e:
                logger.error(f"Error enviando notificación: {str(e)}")
    
    @staticmethod
    def _get_default_message(status: str) -> str:
        """
        Retorna el mensaje por defecto para un estado.
        
        Args:
            status: Código del estado
        
        Returns:
            str: Mensaje por defecto
        """
        messages = {
            'DRAFT': 'Solicitud en borrador',
            'SUBMITTED': 'Solicitud enviada para revisión',
            'IN_REVIEW': 'Tu solicitud está en revisión. Por favor completa los pasos requeridos.',
            'DOCUMENTS': 'Esperando documentación',
            'KYC': 'Verificación de identidad en proceso',
            'SCORING': 'Evaluación crediticia en proceso',
            'REVIEW': 'En revisión por analista',
            'APPROVED': '¡Felicitaciones! Tu crédito ha sido aprobado',
            'REJECTED': 'Solicitud rechazada',
            'DISBURSED': 'Crédito desembolsado',
            'CANCELLED': 'Solicitud cancelada',
            'OBSERVED': 'Tu solicitud tiene observaciones. Por favor revisa los comentarios.',
        }
        
        return messages.get(status, f'Estado actualizado a {status}')
    
    @staticmethod
    def get_next_valid_states(loan_application) -> List[str]:
        """
        Retorna los estados válidos siguientes para una solicitud.
        
        Args:
            loan_application: LoanApplication instance
        
        Returns:
            List[str]: Lista de códigos de estados válidos
        """
        return WorkflowService._get_valid_next_states(loan_application)
    
    @staticmethod
    def check_escalation(loan_application) -> Optional[Dict]:
        """
        Verifica si una solicitud debe ser escalada por timeout.
        
        Args:
            loan_application: LoanApplication instance
        
        Returns:
            dict: Información de escalamiento o None
        """
        stage_config = WorkflowService._get_stage_config(
            loan_application,
            loan_application.status
        )
        
        if not stage_config:
            return None
        
        return stage_config.should_escalate(loan_application)
    
    @staticmethod
    @transaction.atomic
    def auto_transition_if_applicable(loan_application) -> bool:
        """
        Realiza transición automática si aplica.
        
        Usado para etapas automatizadas o con avance automático.
        
        Args:
            loan_application: LoanApplication instance
        
        Returns:
            bool: True si se realizó transición automática
        """
        stage_config = WorkflowService._get_stage_config(
            loan_application,
            loan_application.status
        )
        
        if not stage_config:
            return False
        
        # Verificar si la etapa es automatizada
        if not stage_config.is_automated and not stage_config.auto_advance_enabled:
            return False
        
        # Verificar condiciones de avance automático
        if stage_config.auto_advance_enabled:
            if not stage_config.check_auto_advance_conditions(loan_application):
                logger.info(
                    f"Condiciones de avance automático no cumplidas para "
                    f"solicitud {loan_application.id} en etapa {stage_config.stage_code}"
                )
                return False
        
        # Determinar siguiente etapa
        next_stage = None
        
        # Lógica específica por etapa
        if loan_application.status == 'SCORING':
            # Decisión basada en score
            if hasattr(loan_application, 'credit_score'):
                score = loan_application.credit_score.score
                
                if loan_application.rule_set_snapshot:
                    threshold = getattr(
                        loan_application.rule_set_snapshot,
                        'decision_threshold',
                        None
                    )
                    
                    if threshold:
                        if score >= threshold.min_score_auto_approval:
                            next_stage = 'APPROVED'
                            notes = 'Aprobación automática por score alto'
                            client_msg = '¡Felicitaciones! Tu crédito ha sido aprobado automáticamente'
                        elif score <= threshold.max_score_auto_rejection:
                            next_stage = 'REJECTED'
                            notes = 'Rechazo automático por score bajo'
                            client_msg = 'Tu solicitud no cumple con los requisitos mínimos'
                        else:
                            next_stage = 'REVIEW'
                            notes = 'Requiere revisión manual'
                            client_msg = 'Tu solicitud está en revisión por un analista'
                    else:
                        # Sin threshold, pasar a revisión
                        next_stage = stage_config.next_stage_on_success or 'REVIEW'
                        notes = 'Score calculado, pasando a revisión'
                        client_msg = 'Tu solicitud está en revisión'
                else:
                    # Sin rule_set, usar configuración de la etapa
                    next_stage = stage_config.next_stage_on_success
                    notes = 'Avance automático'
                    client_msg = WorkflowService._get_default_message(next_stage)
            else:
                logger.warning(
                    f"No se puede hacer transición automática: "
                    f"solicitud {loan_application.id} no tiene score"
                )
                return False
        else:
            # Para otras etapas, usar configuración
            next_stage = stage_config.next_stage_on_success
            notes = f'Avance automático desde {stage_config.stage_name}'
            client_msg = WorkflowService._get_default_message(next_stage)
        
        if not next_stage:
            logger.warning(
                f"No se definió siguiente etapa para avance automático "
                f"desde {loan_application.status}"
            )
            return False
        
        # Realizar transición
        try:
            WorkflowService.transition_state(
                loan_application_id=loan_application.id,
                to_status=next_stage,
                changed_by=None,  # Sistema
                notes=notes,
                client_message=client_msg
            )
            
            logger.info(
                f"Transición automática exitosa: solicitud {loan_application.id} "
                f"de {loan_application.status} a {next_stage}"
            )
            
            return True
        except Exception as e:
            logger.error(
                f"Error en transición automática para solicitud {loan_application.id}: "
                f"{str(e)}"
            )
            return False
    
    @staticmethod
    def _schedule_auto_advance_check(loan_application):
        """
        Programa una verificación de avance automático.
        
        En una implementación real, esto podría usar Celery o similar.
        Por ahora, simplemente intenta el avance inmediatamente.
        
        Args:
            loan_application: LoanApplication instance
        """
        # TODO: Implementar con Celery para verificación asíncrona
        # Por ahora, verificar inmediatamente
        try:
            WorkflowService.auto_transition_if_applicable(loan_application)
        except Exception as e:
            logger.error(
                f"Error en verificación de avance automático: {str(e)}"
            )
    
    @staticmethod
    def process_escalations():
        """
        Procesa escalamientos para todas las solicitudes que excedan el tiempo límite.
        
        Este método debe ser llamado periódicamente (ej: cada hora via cron/Celery).
        
        Returns:
            dict: Resumen de escalamientos procesados
        """
        from api.loans.models import LoanApplication
        
        # Obtener solicitudes activas (no en estados finales)
        active_applications = LoanApplication.objects.exclude(
            status__in=['APPROVED', 'REJECTED', 'DISBURSED', 'CANCELLED']
        )
        
        escalated_count = 0
        errors = []
        
        for application in active_applications:
            try:
                escalation_info = WorkflowService.check_escalation(application)
                
                if escalation_info and escalation_info.get('should_escalate'):
                    # Procesar escalamiento
                    WorkflowService._execute_escalation(application, escalation_info)
                    escalated_count += 1
                    
            except Exception as e:
                logger.error(
                    f"Error procesando escalamiento para solicitud {application.id}: "
                    f"{str(e)}"
                )
                errors.append({
                    'application_id': application.id,
                    'error': str(e)
                })
        
        logger.info(f"Procesados {escalated_count} escalamientos")
        
        return {
            'escalated_count': escalated_count,
            'errors': errors
        }
    
    @staticmethod
    def _execute_escalation(loan_application, escalation_info: Dict):
        """
        Ejecuta el escalamiento de una solicitud.
        
        Args:
            loan_application: LoanApplication instance
            escalation_info: Información del escalamiento
        """
        logger.info(
            f"Ejecutando escalamiento para solicitud {loan_application.id}: "
            f"{escalation_info}"
        )
        
        escalation_rules = escalation_info.get('escalation_rules', {})
        
        # Notificar supervisor
        if escalation_rules.get('notify_supervisor'):
            try:
                from api.notifications.services import NotificationService
                NotificationService.send_escalation_notification(
                    loan_application,
                    escalation_info
                )
            except ImportError:
                logger.warning("NotificationService no disponible")
            except Exception as e:
                logger.error(f"Error enviando notificación de escalamiento: {str(e)}")
        
        # Reasignar a rol superior
        if escalation_rules.get('escalate_to_role'):
            # TODO: Implementar lógica de reasignación
            pass
        
        # Registrar evento de escalamiento
        loan_application.add_timeline_event(
            to_status=loan_application.status,  # Mantener mismo estado
            changed_by=None,  # Sistema
            notes=f"Escalamiento automático: {escalation_info.get('stage')} "
                  f"excedió tiempo límite de {escalation_info.get('time_limit_hours')}h",
            is_visible_to_client=False,
            client_message='',
            send_notification=False
        )
