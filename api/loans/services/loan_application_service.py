"""
Servicio para gestión de solicitudes de crédito.

Maneja la lógica de negocio para:
- Creación y envío de solicitudes
- Revisión y evaluación
- Aprobación y rechazo
- Desembolso
- Cálculo de score y ratios
"""

from django.db import transaction
from django.utils import timezone
from api.loans.models import LoanApplication


class LoanApplicationService:
    """
    Servicio para gestión de solicitudes de crédito.
    """
    
    @staticmethod
    @transaction.atomic
    def submit_application(application):
        """
        Envía una solicitud de crédito para revisión.
        
        Args:
            application: LoanApplication
        
        Returns:
            LoanApplication: Solicitud actualizada
        """
        if application.status != LoanApplication.Status.DRAFT:
            raise ValueError("Solo se pueden enviar solicitudes en estado DRAFT")
        
        application.status = LoanApplication.Status.SUBMITTED
        application.submitted_at = timezone.now()
        application.save(update_fields=['status', 'submitted_at'])
        
        return application
    
    @staticmethod
    @transaction.atomic
    def start_review(application, reviewer):
        """
        Inicia la revisión de una solicitud.
        
        Args:
            application: LoanApplication
            reviewer: Usuario que revisa
        
        Returns:
            LoanApplication: Solicitud actualizada
        """
        if application.status != LoanApplication.Status.SUBMITTED:
            raise ValueError("Solo se pueden revisar solicitudes en estado SUBMITTED")
        
        application.status = LoanApplication.Status.UNDER_REVIEW
        application.reviewed_by = reviewer
        application.reviewed_at = timezone.now()
        application.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
        
        return application
    
    @staticmethod
    @transaction.atomic
    def update_evaluation(application, **evaluation_data):
        """
        Actualiza la evaluación de una solicitud.
        
        Args:
            application: LoanApplication
            **evaluation_data: Datos de evaluación
        
        Returns:
            LoanApplication: Solicitud actualizada
        """
        for key, value in evaluation_data.items():
            if hasattr(application, key):
                setattr(application, key, value)
        
        application.save()
        return application
    
    @staticmethod
    def calculate_score(application):
        """
        Calcula el score crediticio de una solicitud.
        
        Args:
            application: LoanApplication
        
        Returns:
            float: Score calculado
        """
        # TODO: Implementar lógica de cálculo de score
        # Por ahora retornar un valor por defecto
        return 0.0
    
    @staticmethod
    def determine_risk_level(score):
        """
        Determina el nivel de riesgo basado en el score.
        
        Args:
            score: Score crediticio
        
        Returns:
            str: Nivel de riesgo
        """
        if score >= 80:
            return 'LOW'
        elif score >= 60:
            return 'MEDIUM'
        else:
            return 'HIGH'
    
    @staticmethod
    def calculate_debt_to_income_ratio(application):
        """
        Calcula el ratio deuda/ingreso.
        
        Args:
            application: LoanApplication
        
        Returns:
            float: Ratio calculado
        """
        if not application.monthly_income or application.monthly_income == 0:
            return 0.0
        
        # TODO: Calcular deudas totales del cliente
        total_debt = 0.0
        
        return (total_debt / application.monthly_income) * 100
    
    @staticmethod
    @transaction.atomic
    def approve_application(application, approver, **approval_data):
        """
        Aprueba una solicitud de crédito.
        
        Args:
            application: LoanApplication
            approver: Usuario que aprueba
            **approval_data: Datos de aprobación
        
        Returns:
            LoanApplication: Solicitud actualizada
        """
        if application.status not in [LoanApplication.Status.UNDER_REVIEW, LoanApplication.Status.SUBMITTED]:
            raise ValueError("Solo se pueden aprobar solicitudes en revisión")
        
        application.status = LoanApplication.Status.APPROVED
        application.approved_by = approver
        application.approved_at = timezone.now()
        
        # Actualizar datos de aprobación
        for key, value in approval_data.items():
            if hasattr(application, key):
                setattr(application, key, value)
        
        application.save()
        return application
    
    @staticmethod
    @transaction.atomic
    def reject_application(application, reviewer, rejection_reason=''):
        """
        Rechaza una solicitud de crédito.
        
        Args:
            application: LoanApplication
            reviewer: Usuario que rechaza
            rejection_reason: Razón del rechazo
        
        Returns:
            LoanApplication: Solicitud actualizada
        """
        if application.status not in [LoanApplication.Status.UNDER_REVIEW, LoanApplication.Status.SUBMITTED]:
            raise ValueError("Solo se pueden rechazar solicitudes en revisión")
        
        application.status = LoanApplication.Status.REJECTED
        application.reviewed_by = reviewer
        application.reviewed_at = timezone.now()
        application.rejection_reason = rejection_reason
        application.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'rejection_reason'])
        
        return application
    
    @staticmethod
    @transaction.atomic
    def disburse_application(application, **disbursement_data):
        """
        Desembolsa una solicitud aprobada.
        
        Args:
            application: LoanApplication
            **disbursement_data: Datos de desembolso
        
        Returns:
            LoanApplication: Solicitud actualizada
        """
        if application.status != LoanApplication.Status.APPROVED:
            raise ValueError("Solo se pueden desembolsar solicitudes aprobadas")
        
        application.status = LoanApplication.Status.DISBURSED
        application.disbursed_at = timezone.now()
        
        # Actualizar datos de desembolso
        for key, value in disbursement_data.items():
            if hasattr(application, key):
                setattr(application, key, value)
        
        application.save()
        return application
