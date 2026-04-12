"""
Servicios para gestión de suscripciones SaaS.
"""
from dataclasses import dataclass
from datetime import date
from django.db import transaction

from .models import SubscriptionPlan, Subscription


@dataclass(frozen=True)
class AssignFreePlanInput:
    """Input para asignar plan gratuito a una institución."""
    institution: object


@dataclass(frozen=True)
class AssignFreePlanResult:
    """Resultado de asignación de plan gratuito."""
    subscription: object
    plan: object
    is_new: bool


class AssignFreePlanService:
    """Servicio para asignar plan gratuito a instituciones nuevas."""

    @transaction.atomic
    def execute(self, payload: AssignFreePlanInput) -> AssignFreePlanResult:
        """
        Asigna el plan gratuito a una institución si no tiene suscripción.
        
        Args:
            payload: AssignFreePlanInput con la institución
            
        Returns:
            AssignFreePlanResult con la suscripción creada o existente
        """
        institution = payload.institution
        
        # Verificar si ya tiene suscripción
        try:
            existing_subscription = Subscription.objects.get(institution=institution)
            return AssignFreePlanResult(
                subscription=existing_subscription,
                plan=existing_subscription.plan,
                is_new=False
            )
        except Subscription.DoesNotExist:
            pass
        
        # Obtener o crear plan gratuito
        free_plan, _ = SubscriptionPlan.objects.get_or_create(
            slug='gratuito',
            defaults={
                'name': 'Plan Gratuito',
                'description': 'Plan gratuito con funcionalidades básicas para empezar',
                'price': 0.00,
                'billing_cycle': 'MONTHLY',
                'trial_days': 0,
                'setup_fee': 0.00,
                
                # Límites básicos pero funcionales
                'max_users': 3,
                'max_branches': 1,
                'max_products': 2,
                'max_loans_per_month': 20,
                'max_storage_gb': 1,
                
                # Características básicas
                'has_ai_scoring': False,
                'has_workflows': False,
                'has_reporting': True,
                'has_mobile_app': True,
                'has_api_access': False,
                'has_white_label': False,
                'has_priority_support': False,
                'has_custom_integrations': False,
                
                'is_active': True,
                'is_featured': False,
                'display_order': -1,
                'features_list': [
                    'Hasta 3 usuarios',
                    'Hasta 2 productos crediticios',
                    'Hasta 20 solicitudes por mes',
                    'App móvil para clientes',
                    'Reportes básicos',
                    '1 GB de almacenamiento',
                    'Soporte por email'
                ]
            }
        )
        
        # Crear suscripción gratuita
        subscription = Subscription.objects.create(
            institution=institution,
            plan=free_plan,
            status='ACTIVE',
            start_date=date.today(),
            payment_status='PAID',
            
            # Contadores iniciales
            current_users=1,
            current_branches=1,
            current_products=0,
            current_month_loans=0,
            current_storage_gb=0,
            
            notes='Suscripción gratuita asignada automáticamente al registrar institución'
        )
        
        return AssignFreePlanResult(
            subscription=subscription,
            plan=free_plan,
            is_new=True
        )


@dataclass(frozen=True)
class CheckSubscriptionLimitsInput:
    """Input para verificar límites de suscripción."""
    institution: object
    action: str  # 'add_user', 'add_product', 'add_loan', etc.


@dataclass(frozen=True)
class CheckSubscriptionLimitsResult:
    """Resultado de verificación de límites."""
    allowed: bool
    current_usage: dict
    limits: dict
    message: str


class CheckSubscriptionLimitsService:
    """Servicio para verificar límites de suscripción."""

    def execute(self, payload: CheckSubscriptionLimitsInput) -> CheckSubscriptionLimitsResult:
        """
        Verifica si una acción está permitida según los límites del plan.
        
        Args:
            payload: CheckSubscriptionLimitsInput con institución y acción
            
        Returns:
            CheckSubscriptionLimitsResult con el resultado de la verificación
        """
        try:
            subscription = Subscription.objects.select_related('plan').get(
                institution=payload.institution,
                status__in=['TRIAL', 'ACTIVE']
            )
        except Subscription.DoesNotExist:
            return CheckSubscriptionLimitsResult(
                allowed=False,
                current_usage={},
                limits={},
                message='No hay suscripción activa para esta institución.'
            )
        
        plan = subscription.plan
        
        # Obtener uso actual y límites
        current_usage = {
            'users': subscription.current_users,
            'branches': subscription.current_branches,
            'products': subscription.current_products,
            'loans_this_month': subscription.current_month_loans,
            'storage_gb': float(subscription.current_storage_gb),
        }
        
        limits = {
            'users': plan.max_users,
            'branches': plan.max_branches,
            'products': plan.max_products,
            'loans_per_month': plan.max_loans_per_month,
            'storage_gb': plan.max_storage_gb,
        }
        
        # Verificar límite según la acción
        allowed = True
        message = 'Acción permitida'
        
        if payload.action == 'add_user':
            if subscription.current_users >= plan.max_users:
                allowed = False
                message = f'Límite de usuarios alcanzado ({plan.max_users}). Actualiza tu plan para agregar más usuarios.'
        
        elif payload.action == 'add_product':
            if subscription.current_products >= plan.max_products:
                allowed = False
                message = f'Límite de productos alcanzado ({plan.max_products}). Actualiza tu plan para agregar más productos.'
        
        elif payload.action == 'add_loan':
            if subscription.current_month_loans >= plan.max_loans_per_month:
                allowed = False
                message = f'Límite de créditos mensuales alcanzado ({plan.max_loans_per_month}). Actualiza tu plan o espera al próximo mes.'
        
        elif payload.action == 'check_storage':
            if subscription.current_storage_gb >= plan.max_storage_gb:
                allowed = False
                message = f'Límite de almacenamiento alcanzado ({plan.max_storage_gb} GB). Actualiza tu plan para más espacio.'
        
        return CheckSubscriptionLimitsResult(
            allowed=allowed,
            current_usage=current_usage,
            limits=limits,
            message=message
        )


@dataclass(frozen=True)
class UpdateUsageCountersInput:
    """Input para actualizar contadores de uso."""
    institution: object
    users_delta: int = 0
    products_delta: int = 0
    loans_delta: int = 0
    storage_delta: float = 0.0


class UpdateUsageCountersService:
    """Servicio para actualizar contadores de uso de suscripción."""

    @transaction.atomic
    def execute(self, payload: UpdateUsageCountersInput) -> bool:
        """
        Actualiza los contadores de uso de la suscripción.
        
        Args:
            payload: UpdateUsageCountersInput con los deltas a aplicar
            
        Returns:
            bool: True si se actualizó correctamente
        """
        try:
            subscription = Subscription.objects.select_for_update().get(
                institution=payload.institution,
                status__in=['TRIAL', 'ACTIVE']
            )
        except Subscription.DoesNotExist:
            return False
        
        # Actualizar contadores
        if payload.users_delta != 0:
            subscription.current_users = max(0, subscription.current_users + payload.users_delta)
        
        if payload.products_delta != 0:
            subscription.current_products = max(0, subscription.current_products + payload.products_delta)
        
        if payload.loans_delta != 0:
            subscription.current_month_loans = max(0, subscription.current_month_loans + payload.loans_delta)
        
        if payload.storage_delta != 0:
            subscription.current_storage_gb = max(0, subscription.current_storage_gb + payload.storage_delta)
        
        subscription.save()
        return True