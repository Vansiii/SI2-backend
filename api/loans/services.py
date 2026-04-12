"""
Servicios de lógica de negocio para solicitudes de crédito
"""

from django.utils import timezone
from django.db import transaction
from .models import LoanApplication


class LoanApplicationService:
    """Servicio para gestionar solicitudes de crédito"""
    
    @staticmethod
    @transaction.atomic
    def submit_application(application: LoanApplication) -> LoanApplication:
        """Enviar solicitud para revisión"""
        if not application.can_be_submitted:
            raise ValueError('La solicitud no puede ser enviada')
        
        application.status = LoanApplication.Status.SUBMITTED
        application.submitted_at = timezone.now()
        application.save()
        
        return application
    
    @staticmethod
    @transaction.atomic
    def start_review(application: LoanApplication, reviewer) -> LoanApplication:
        """Iniciar revisión de solicitud"""
        if application.status != LoanApplication.Status.SUBMITTED:
            raise ValueError('Solo se pueden revisar solicitudes enviadas')
        
        application.status = LoanApplication.Status.UNDER_REVIEW
        application.reviewed_by = reviewer
        application.reviewed_at = timezone.now()
        application.save()
        
        return application
    
    @staticmethod
    @transaction.atomic
    def update_evaluation(
        application: LoanApplication,
        credit_score=None,
        risk_level=None,
        debt_to_income_ratio=None,
        notes=None
    ) -> LoanApplication:
        """Actualizar evaluación de la solicitud"""
        if credit_score is not None:
            application.credit_score = credit_score
        if risk_level is not None:
            application.risk_level = risk_level
        if debt_to_income_ratio is not None:
            application.debt_to_income_ratio = debt_to_income_ratio
        if notes is not None:
            application.notes = notes
        
        application.save()
        return application
    
    @staticmethod
    @transaction.atomic
    def approve_application(
        application: LoanApplication,
        approved_amount,
        approved_term_months,
        approved_interest_rate,
        approver,
        notes=None
    ) -> LoanApplication:
        """Aprobar solicitud"""
        if not application.can_be_approved:
            raise ValueError('La solicitud no puede ser aprobada')
        
        application.status = LoanApplication.Status.APPROVED
        application.approved_amount = approved_amount
        application.approved_term_months = approved_term_months
        application.approved_interest_rate = approved_interest_rate
        application.approved_by = approver
        application.approved_at = timezone.now()
        
        # Calcular cuota mensual
        application.monthly_payment = application.calculate_monthly_payment()
        
        if notes:
            application.notes = notes
        
        application.save()
        
        return application
    
    @staticmethod
    @transaction.atomic
    def reject_application(
        application: LoanApplication,
        rejection_reason: str,
        reviewer
    ) -> LoanApplication:
        """Rechazar solicitud"""
        if not application.can_be_rejected:
            raise ValueError('La solicitud no puede ser rechazada')
        
        application.status = LoanApplication.Status.REJECTED
        application.rejection_reason = rejection_reason
        application.rejected_at = timezone.now()
        
        if not application.reviewed_by:
            application.reviewed_by = reviewer
        
        application.save()
        
        return application
    
    @staticmethod
    @transaction.atomic
    def disburse_application(
        application: LoanApplication,
        notes=None
    ) -> LoanApplication:
        """Desembolsar solicitud aprobada"""
        if not application.can_be_disbursed:
            raise ValueError('La solicitud no puede ser desembolsada')
        
        application.status = LoanApplication.Status.DISBURSED
        application.disbursed_at = timezone.now()
        
        if notes:
            application.notes = notes
        
        application.save()
        
        return application
    
    @staticmethod
    @transaction.atomic
    def cancel_application(
        application: LoanApplication,
        reason: str
    ) -> LoanApplication:
        """Cancelar solicitud"""
        if application.status in [
            LoanApplication.Status.DISBURSED,
            LoanApplication.Status.CANCELLED
        ]:
            raise ValueError('La solicitud no puede ser cancelada')
        
        application.status = LoanApplication.Status.CANCELLED
        application.rejection_reason = f"Cancelada: {reason}"
        application.save()
        
        return application
    
    @staticmethod
    def calculate_score(application: LoanApplication) -> int:
        """
        Calcula un score básico de crédito
        Este es un algoritmo simplificado - en producción usar un modelo más sofisticado
        """
        score = 500  # Score base
        
        client = application.client
        
        # Factor 1: Ingreso mensual vs monto solicitado (30%)
        if client.monthly_income:
            income_ratio = float(application.requested_amount) / float(client.monthly_income)
            if income_ratio < 2:
                score += 150
            elif income_ratio < 3:
                score += 100
            elif income_ratio < 5:
                score += 50
            else:
                score -= 50
        
        # Factor 2: Estado de empleo (20%)
        if client.employment_status == 'EMPLOYED':
            score += 100
        elif client.employment_status == 'SELF_EMPLOYED':
            score += 75
        elif client.employment_status == 'RETIRED':
            score += 50
        else:
            score -= 50
        
        # Factor 3: Cliente verificado (15%)
        if client.kyc_status == 'VERIFIED':
            score += 75
        elif client.kyc_status == 'PENDING':
            score += 25
        
        # Factor 4: Plazo solicitado (10%)
        if application.term_months <= 12:
            score += 50
        elif application.term_months <= 24:
            score += 25
        elif application.term_months > 60:
            score -= 25
        
        # Factor 5: Tipo de producto (10%)
        product_type = application.product.product_type
        if product_type in ['PERSONAL', 'MICROEMPRESA']:
            score += 50
        elif product_type in ['VEHICULAR', 'PYME']:
            score += 25
        
        # Factor 6: Historial previo (15%)
        # Contar solicitudes previas aprobadas
        previous_approved = LoanApplication.objects.filter(
            client=client,
            status=LoanApplication.Status.DISBURSED,
            institution=application.institution
        ).count()
        
        if previous_approved > 0:
            score += 75
        
        # Contar solicitudes previas rechazadas
        previous_rejected = LoanApplication.objects.filter(
            client=client,
            status=LoanApplication.Status.REJECTED,
            institution=application.institution
        ).count()
        
        if previous_rejected > 0:
            score -= 50 * previous_rejected
        
        # Asegurar que el score esté en el rango 0-1000
        score = max(0, min(1000, score))
        
        return score
    
    @staticmethod
    def determine_risk_level(score: int) -> str:
        """Determina el nivel de riesgo basado en el score"""
        if score >= 750:
            return LoanApplication.RiskLevel.LOW
        elif score >= 600:
            return LoanApplication.RiskLevel.MEDIUM
        elif score >= 450:
            return LoanApplication.RiskLevel.HIGH
        else:
            return LoanApplication.RiskLevel.VERY_HIGH
    
    @staticmethod
    def calculate_debt_to_income_ratio(application: LoanApplication) -> float:
        """Calcula el ratio deuda/ingreso"""
        if not application.client.monthly_income:
            return 0.0
        
        monthly_payment = application.calculate_monthly_payment()
        if not monthly_payment:
            return 0.0
        
        ratio = (float(monthly_payment) / float(application.client.monthly_income)) * 100
        return round(ratio, 2)
