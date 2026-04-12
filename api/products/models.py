"""
Modelos para gestión de productos crediticios.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from api.core.models import TenantModel, TimeStampedModel


class CreditProduct(TenantModel, TimeStampedModel):
    """
    Modelo de Producto Crediticio.
    
    Define los tipos de crédito que ofrece una institución financiera
    con sus condiciones, tasas, plazos y requisitos.
    """
    
    # Tipos de producto
    PRODUCT_TYPE_CHOICES = [
        ('PERSONAL', 'Crédito Personal/Consumo'),
        ('VEHICULAR', 'Crédito Vehicular'),
        ('HIPOTECARIO', 'Crédito Hipotecario'),
        ('VIVIENDA_SOCIAL', 'Crédito Vivienda Social'),
        ('PYME', 'Crédito PYME'),
        ('EMPRESARIAL', 'Crédito Empresarial'),
        ('AGROPECUARIO', 'Crédito Agropecuario'),
        ('MICROEMPRESA', 'Microcrédito'),
    ]
    
    # Tipo de tasa de interés
    INTEREST_TYPE_CHOICES = [
        ('FIXED', 'Tasa Fija'),
        ('VARIABLE', 'Tasa Variable'),
        ('MIXED', 'Tasa Mixta'),
    ]
    
    # Frecuencia de pago
    PAYMENT_FREQUENCY_CHOICES = [
        ('MONTHLY', 'Mensual'),
        ('BIWEEKLY', 'Quincenal'),
        ('WEEKLY', 'Semanal'),
    ]
    
    # Sistema de amortización
    AMORTIZATION_SYSTEM_CHOICES = [
        ('FRENCH', 'Sistema Francés (Cuota Fija)'),
        ('GERMAN', 'Sistema Alemán (Cuota Decreciente)'),
        ('AMERICAN', 'Sistema Americano (Solo Intereses)'),
    ]
    
    # ============================================================
    # INFORMACIÓN BÁSICA
    # ============================================================
    name = models.CharField(
        max_length=200,
        verbose_name='Nombre del Producto'
    )
    
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Código del Producto',
        help_text='Código único identificador del producto'
    )
    
    product_type = models.CharField(
        max_length=20,
        choices=PRODUCT_TYPE_CHOICES,
        verbose_name='Tipo de Producto'
    )
    
    description = models.TextField(
        verbose_name='Descripción',
        help_text='Descripción detallada del producto crediticio'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activo',
        help_text='Indica si el producto está disponible para solicitudes'
    )
    
    display_order = models.IntegerField(
        default=0,
        verbose_name='Orden de Visualización',
        help_text='Orden en que se muestra el producto (menor primero)'
    )
    
    # ============================================================
    # MONTOS
    # ============================================================
    min_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Monto Mínimo (Bs)',
        help_text='Monto mínimo del crédito en Bolivianos'
    )
    
    max_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Monto Máximo (Bs)',
        help_text='Monto máximo del crédito en Bolivianos'
    )
    
    # ============================================================
    # PLAZOS
    # ============================================================
    min_term_months = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='Plazo Mínimo (meses)',
        help_text='Plazo mínimo del crédito en meses'
    )
    
    max_term_months = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='Plazo Máximo (meses)',
        help_text='Plazo máximo del crédito en meses'
    )
    
    # ============================================================
    # TASAS DE INTERÉS
    # ============================================================
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Tasa de Interés Anual (%)',
        help_text='Tasa de interés anual nominal'
    )
    
    interest_type = models.CharField(
        max_length=10,
        choices=INTEREST_TYPE_CHOICES,
        default='FIXED',
        verbose_name='Tipo de Tasa'
    )
    
    effective_annual_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Tasa Efectiva Anual (%)',
        help_text='TEA - Incluye comisiones y seguros'
    )
    
    # ============================================================
    # COMISIONES Y SEGUROS
    # ============================================================
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Comisión (%)',
        help_text='Comisión sobre el monto del crédito'
    )
    
    insurance_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Seguro de Desgravamen (%)',
        help_text='Porcentaje mensual sobre saldo deudor'
    )
    
    additional_insurance_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Seguro Adicional (%)',
        help_text='Seguro del bien (vehicular/hipotecario)'
    )
    
    # ============================================================
    # SISTEMA DE PAGO
    # ============================================================
    payment_frequency = models.CharField(
        max_length=10,
        choices=PAYMENT_FREQUENCY_CHOICES,
        default='MONTHLY',
        verbose_name='Frecuencia de Pago'
    )
    
    amortization_system = models.CharField(
        max_length=10,
        choices=AMORTIZATION_SYSTEM_CHOICES,
        default='FRENCH',
        verbose_name='Sistema de Amortización'
    )
    
    grace_period_months = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Período de Gracia (meses)',
        help_text='Meses sin pago de capital al inicio'
    )
    
    allows_early_payment = models.BooleanField(
        default=True,
        verbose_name='Permite Pago Anticipado'
    )
    
    early_payment_penalty = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Penalidad Pago Anticipado (%)',
        help_text='Porcentaje sobre el saldo anticipado'
    )
    
    # ============================================================
    # REQUISITOS
    # ============================================================
    min_income_required = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
        verbose_name='Ingreso Mínimo Requerido (Bs)',
        help_text='Ingreso líquido mensual mínimo'
    )
    
    max_debt_to_income_ratio = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=40.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Relación Cuota-Ingreso Máxima (%)',
        help_text='RCI máximo permitido (típicamente 40%)'
    )
    
    min_employment_months = models.IntegerField(
        default=6,
        validators=[MinValueValidator(0)],
        verbose_name='Antigüedad Laboral Mínima (meses)'
    )
    
    requires_guarantor = models.BooleanField(
        default=False,
        verbose_name='Requiere Garante'
    )
    
    requires_collateral = models.BooleanField(
        default=False,
        verbose_name='Requiere Garantía Real',
        help_text='Hipoteca, prenda, etc.'
    )
    
    min_collateral_coverage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100.00,
        validators=[MinValueValidator(0)],
        verbose_name='Cobertura Mínima de Garantía (%)',
        help_text='Valor garantía / Monto crédito (típicamente 125%)'
    )
    
    required_documents = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Documentos Requeridos',
        help_text='Lista de documentos necesarios para solicitar'
    )
    
    # ============================================================
    # SCORING Y APROBACIÓN
    # ============================================================
    min_credit_score = models.IntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Score Crediticio Mínimo',
        help_text='Score mínimo para aprobación automática'
    )
    
    auto_approval_enabled = models.BooleanField(
        default=False,
        verbose_name='Aprobación Automática Habilitada',
        help_text='Permite aprobación sin revisión manual si cumple criterios'
    )
    
    max_auto_approval_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
        verbose_name='Monto Máximo Aprobación Automática (Bs)',
        help_text='Montos superiores requieren revisión manual'
    )
    
    # ============================================================
    # INFORMACIÓN ADICIONAL
    # ============================================================
    target_audience = models.TextField(
        blank=True,
        null=True,
        verbose_name='Público Objetivo',
        help_text='Descripción del perfil de cliente ideal'
    )
    
    benefits = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Beneficios',
        help_text='Lista de beneficios del producto'
    )
    
    terms_and_conditions = models.TextField(
        blank=True,
        null=True,
        verbose_name='Términos y Condiciones'
    )
    
    class Meta:
        verbose_name = 'Producto Crediticio'
        verbose_name_plural = 'Productos Crediticios'
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['product_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['institution', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_product_type_display()})"
    
    def calculate_monthly_payment(self, amount, term_months):
        """
        Calcula la cuota mensual usando el sistema francés.
        
        Args:
            amount: Monto del crédito en Bs
            term_months: Plazo en meses
            
        Returns:
            Decimal: Cuota mensual aproximada
        """
        if term_months <= 0:
            return Decimal('0')
        
        # Tasa mensual
        monthly_rate = self.interest_rate / Decimal('100') / Decimal('12')
        
        if monthly_rate == 0:
            # Sin interés, solo dividir el monto
            return amount / Decimal(str(term_months))
        
        # Fórmula del sistema francés
        # C = P × [i × (1 + i)^n] / [(1 + i)^n – 1]
        factor = (1 + monthly_rate) ** term_months
        monthly_payment = amount * (monthly_rate * factor) / (factor - 1)
        
        return monthly_payment.quantize(Decimal('0.01'))
    
    def calculate_total_cost(self, amount, term_months):
        """
        Calcula el costo total del crédito.
        
        Returns:
            dict: Desglose de costos
        """
        monthly_payment = self.calculate_monthly_payment(amount, term_months)
        total_payments = monthly_payment * term_months
        total_interest = total_payments - amount
        commission = amount * (self.commission_rate / Decimal('100'))
        
        # Seguro de desgravamen aproximado (sobre saldo promedio)
        avg_balance = amount / 2
        insurance_cost = avg_balance * (self.insurance_rate / Decimal('100')) * term_months
        
        return {
            'monthly_payment': monthly_payment,
            'total_payments': total_payments,
            'total_interest': total_interest,
            'commission': commission,
            'insurance_cost': insurance_cost,
            'total_cost': total_interest + commission + insurance_cost,
        }
    
    def is_amount_valid(self, amount):
        """Verifica si el monto está dentro del rango permitido."""
        return self.min_amount <= amount <= self.max_amount
    
    def is_term_valid(self, term_months):
        """Verifica si el plazo está dentro del rango permitido."""
        return self.min_term_months <= term_months <= self.max_term_months


class ProductRequirement(TenantModel, TimeStampedModel):
    """
    Requisitos específicos adicionales para un producto crediticio.
    """
    
    product = models.ForeignKey(
        CreditProduct,
        on_delete=models.CASCADE,
        related_name='additional_requirements',
        verbose_name='Producto'
    )
    
    requirement_name = models.CharField(
        max_length=200,
        verbose_name='Nombre del Requisito'
    )
    
    description = models.TextField(
        verbose_name='Descripción'
    )
    
    is_mandatory = models.BooleanField(
        default=True,
        verbose_name='Obligatorio'
    )
    
    display_order = models.IntegerField(
        default=0,
        verbose_name='Orden'
    )
    
    class Meta:
        verbose_name = 'Requisito de Producto'
        verbose_name_plural = 'Requisitos de Productos'
        ordering = ['display_order', 'requirement_name']
    
    def __str__(self):
        return f"{self.requirement_name} - {self.product.name}"
