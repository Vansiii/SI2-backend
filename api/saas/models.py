"""
Modelos para gestión de suscripciones SaaS.
"""

from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from datetime import date, timedelta
from api.core.models import TimeStampedModel


class SubscriptionPlan(TimeStampedModel):
    """
    Planes de suscripción para el sistema SaaS.
    
    Define los diferentes niveles de servicio que las instituciones
    financieras pueden contratar.
    """
    
    BILLING_CYCLE_CHOICES = [
        ('MONTHLY', 'Mensual'),
        ('QUARTERLY', 'Trimestral'),
        ('ANNUAL', 'Anual'),
    ]
    
    # ============================================================
    # INFORMACIÓN BÁSICA
    # ============================================================
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Nombre del Plan',
        help_text='Ej: Básico, Profesional, Empresarial'
    )
    
    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name='Slug',
        help_text='Identificador único en URL'
    )
    
    description = models.TextField(
        verbose_name='Descripción',
        help_text='Descripción detallada del plan'
    )
    
    # ============================================================
    # PRECIO Y FACTURACIÓN
    # ============================================================
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Precio (Bs)',
        help_text='Precio del plan en Bolivianos'
    )
    
    billing_cycle = models.CharField(
        max_length=10,
        choices=BILLING_CYCLE_CHOICES,
        default='MONTHLY',
        verbose_name='Ciclo de Facturación'
    )
    
    trial_days = models.IntegerField(
        default=30,
        validators=[MinValueValidator(0)],
        verbose_name='Días de Prueba',
        help_text='Días de prueba gratuita'
    )
    
    setup_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Costo de Configuración (Bs)',
        help_text='Costo único de configuración inicial'
    )
    
    # ============================================================
    # LÍMITES DE USO
    # ============================================================
    max_users = models.IntegerField(
        default=10,
        validators=[MinValueValidator(1)],
        verbose_name='Máximo de Usuarios',
        help_text='Número máximo de usuarios del sistema'
    )
    
    max_branches = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name='Máximo de Sucursales',
        help_text='Número máximo de sucursales'
    )
    
    max_products = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1)],
        verbose_name='Máximo de Productos',
        help_text='Número máximo de productos crediticios'
    )
    
    max_loans_per_month = models.IntegerField(
        default=100,
        validators=[MinValueValidator(1)],
        verbose_name='Máximo de Créditos por Mes',
        help_text='Número máximo de solicitudes de crédito por mes'
    )
    
    max_storage_gb = models.IntegerField(
        default=10,
        validators=[MinValueValidator(1)],
        verbose_name='Almacenamiento Máximo (GB)',
        help_text='Espacio de almacenamiento para documentos'
    )
    
    # ============================================================
    # CARACTERÍSTICAS (FEATURES)
    # ============================================================
    has_ai_scoring = models.BooleanField(
        default=False,
        verbose_name='Scoring con IA',
        help_text='Evaluación crediticia con inteligencia artificial'
    )
    
    has_workflows = models.BooleanField(
        default=False,
        verbose_name='Workflows Configurables',
        help_text='Flujos de trabajo personalizables'
    )
    
    has_reporting = models.BooleanField(
        default=True,
        verbose_name='Reportes y Analítica',
        help_text='Dashboards y reportes avanzados'
    )
    
    has_mobile_app = models.BooleanField(
        default=True,
        verbose_name='App Móvil',
        help_text='Acceso a aplicación móvil para prestatarios'
    )
    
    has_api_access = models.BooleanField(
        default=False,
        verbose_name='Acceso API',
        help_text='Acceso a API REST para integraciones'
    )
    
    has_white_label = models.BooleanField(
        default=False,
        verbose_name='White Label',
        help_text='Personalización de marca'
    )
    
    has_priority_support = models.BooleanField(
        default=False,
        verbose_name='Soporte Prioritario',
        help_text='Soporte técnico prioritario'
    )
    
    has_custom_integrations = models.BooleanField(
        default=False,
        verbose_name='Integraciones Personalizadas',
        help_text='Integraciones con sistemas externos'
    )
    
    # ============================================================
    # CONFIGURACIÓN
    # ============================================================
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activo',
        help_text='Plan disponible para contratación'
    )
    
    is_featured = models.BooleanField(
        default=False,
        verbose_name='Destacado',
        help_text='Mostrar como plan recomendado'
    )
    
    display_order = models.IntegerField(
        default=0,
        verbose_name='Orden de Visualización',
        help_text='Orden en que se muestra (menor primero)'
    )
    
    features_list = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Lista de Características',
        help_text='Lista de características para mostrar en UI'
    )
    
    class Meta:
        verbose_name = 'Plan de Suscripción'
        verbose_name_plural = 'Planes de Suscripción'
        ordering = ['display_order', 'price']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['slug']),
        ]
    
    def __str__(self):
        return f"{self.name} - Bs {self.price}/{self.get_billing_cycle_display()}"
    
    def get_price_per_month(self):
        """Calcula el precio mensual equivalente."""
        if self.billing_cycle == 'MONTHLY':
            return self.price
        elif self.billing_cycle == 'QUARTERLY':
            return self.price / 3
        elif self.billing_cycle == 'ANNUAL':
            return self.price / 12
        return self.price


class Subscription(TimeStampedModel):
    """
    Suscripción de una institución financiera a un plan.
    
    Gestiona el estado de la suscripción, límites de uso y facturación.
    """
    
    STATUS_CHOICES = [
        ('TRIAL', 'Período de Prueba'),
        ('ACTIVE', 'Activa'),
        ('SUSPENDED', 'Suspendida'),
        ('CANCELLED', 'Cancelada'),
        ('EXPIRED', 'Expirada'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('PAID', 'Pagado'),
        ('OVERDUE', 'Vencido'),
        ('FAILED', 'Fallido'),
    ]
    
    # ============================================================
    # RELACIONES
    # ============================================================
    institution = models.OneToOneField(
        'tenants.FinancialInstitution',
        on_delete=models.CASCADE,
        related_name='subscription',
        verbose_name='Institución Financiera'
    )
    
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name='subscriptions',
        verbose_name='Plan'
    )
    
    # ============================================================
    # ESTADO Y FECHAS
    # ============================================================
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='TRIAL',
        verbose_name='Estado'
    )
    
    start_date = models.DateField(
        verbose_name='Fecha de Inicio'
    )
    
    end_date = models.DateField(
        blank=True,
        null=True,
        verbose_name='Fecha de Fin',
        help_text='Fecha de finalización de la suscripción'
    )
    
    trial_end_date = models.DateField(
        blank=True,
        null=True,
        verbose_name='Fin del Período de Prueba'
    )
    
    next_billing_date = models.DateField(
        blank=True,
        null=True,
        verbose_name='Próxima Fecha de Facturación'
    )
    
    last_billing_date = models.DateField(
        blank=True,
        null=True,
        verbose_name='Última Fecha de Facturación'
    )
    
    # ============================================================
    # FACTURACIÓN
    # ============================================================
    payment_status = models.CharField(
        max_length=10,
        choices=PAYMENT_STATUS_CHOICES,
        default='PENDING',
        verbose_name='Estado de Pago'
    )
    
    amount_due = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Monto Adeudado (Bs)'
    )
    
    total_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Total Pagado (Bs)',
        help_text='Total acumulado pagado'
    )
    
    # ============================================================
    # USO ACTUAL (CONTADORES)
    # ============================================================
    current_users = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Usuarios Actuales'
    )
    
    current_branches = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Sucursales Actuales'
    )
    
    current_products = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Productos Actuales'
    )
    
    current_month_loans = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Créditos del Mes Actual'
    )
    
    current_storage_gb = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Almacenamiento Usado (GB)'
    )
    
    # ============================================================
    # NOTAS Y METADATA
    # ============================================================
    cancellation_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name='Motivo de Cancelación'
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name='Notas Internas'
    )
    
    class Meta:
        verbose_name = 'Suscripción'
        verbose_name_plural = 'Suscripciones'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['next_billing_date']),
        ]
    
    def __str__(self):
        return f"{self.institution.name} - {self.plan.name} ({self.get_status_display()})"
    
    def is_within_limits(self):
        """Verifica si la institución está dentro de los límites del plan."""
        return (
            self.current_users <= self.plan.max_users and
            self.current_branches <= self.plan.max_branches and
            self.current_products <= self.plan.max_products and
            self.current_month_loans <= self.plan.max_loans_per_month and
            self.current_storage_gb <= self.plan.max_storage_gb
        )
    
    def get_usage_percentage(self):
        """Calcula el porcentaje de uso de los límites."""
        return {
            'users': (self.current_users / self.plan.max_users * 100) if self.plan.max_users > 0 else 0,
            'branches': (self.current_branches / self.plan.max_branches * 100) if self.plan.max_branches > 0 else 0,
            'products': (self.current_products / self.plan.max_products * 100) if self.plan.max_products > 0 else 0,
            'loans': (self.current_month_loans / self.plan.max_loans_per_month * 100) if self.plan.max_loans_per_month > 0 else 0,
            'storage': (float(self.current_storage_gb) / self.plan.max_storage_gb * 100) if self.plan.max_storage_gb > 0 else 0,
        }
    
    def is_trial(self):
        """Verifica si está en período de prueba."""
        return self.status == 'TRIAL' and self.trial_end_date and self.trial_end_date >= date.today()
    
    def is_active_subscription(self):
        """Verifica si la suscripción está activa."""
        return self.status in ['TRIAL', 'ACTIVE']
    
    def days_until_renewal(self):
        """Calcula días hasta la próxima renovación."""
        if self.next_billing_date:
            delta = self.next_billing_date - date.today()
            return delta.days
        return None
    
    def activate_trial(self):
        """Activa el período de prueba."""
        self.status = 'TRIAL'
        self.start_date = date.today()
        self.trial_end_date = date.today() + timedelta(days=self.plan.trial_days)
        self.next_billing_date = self.trial_end_date
        self.save()
    
    def activate_subscription(self):
        """Activa la suscripción después del trial."""
        self.status = 'ACTIVE'
        self.payment_status = 'PAID'
        
        # Calcular próxima fecha de facturación
        if self.plan.billing_cycle == 'MONTHLY':
            self.next_billing_date = date.today() + timedelta(days=30)
        elif self.plan.billing_cycle == 'QUARTERLY':
            self.next_billing_date = date.today() + timedelta(days=90)
        elif self.plan.billing_cycle == 'ANNUAL':
            self.next_billing_date = date.today() + timedelta(days=365)
        
        self.save()
    
    def suspend_subscription(self, reason=None):
        """Suspende la suscripción."""
        self.status = 'SUSPENDED'
        if reason:
            self.notes = f"{self.notes}\n\nSuspendida: {reason}" if self.notes else f"Suspendida: {reason}"
        self.save()
    
    def cancel_subscription(self, reason=None):
        """Cancela la suscripción."""
        self.status = 'CANCELLED'
        self.end_date = date.today()
        self.cancellation_reason = reason
        self.save()
    
    def reset_monthly_counters(self):
        """Resetea los contadores mensuales."""
        self.current_month_loans = 0
        self.save()
