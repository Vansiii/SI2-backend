"""
Modelos para gestión de solicitudes de crédito
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from api.core.models import TenantModel


class LoanApplication(TenantModel):
    """
    Modelo para solicitudes de crédito (CU-11: Gestionar Originación de Créditos)
    """
    
    # Estados de la solicitud
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Borrador'
        SUBMITTED = 'SUBMITTED', 'Enviada'
        IN_REVIEW = 'IN_REVIEW', 'En Revisión'
        OBSERVED = 'OBSERVED', 'Observada'
        UNDER_REVIEW = 'UNDER_REVIEW', 'En Revisión Interna'  # Para compatibilidad
        APPROVED = 'APPROVED', 'Aprobada'
        REJECTED = 'REJECTED', 'Rechazada'
        DISBURSED = 'DISBURSED', 'Desembolsada'
        CANCELLED = 'CANCELLED', 'Cancelada'
    
    # Niveles de riesgo
    class RiskLevel(models.TextChoices):
        LOW = 'LOW', 'Bajo'
        MEDIUM = 'MEDIUM', 'Medio'
        HIGH = 'HIGH', 'Alto'
        VERY_HIGH = 'VERY_HIGH', 'Muy Alto'
    
    # Tipos de empleo
    class EmploymentType(models.TextChoices):
        EMPLOYED = 'EMPLOYED', 'Empleado en relación de dependencia'
        SELF_EMPLOYED = 'SELF_EMPLOYED', 'Trabajador independiente'
        BUSINESS_OWNER = 'BUSINESS_OWNER', 'Propietario de negocio'
        RETIRED = 'RETIRED', 'Jubilado'
        UNEMPLOYED = 'UNEMPLOYED', 'Desempleado'
        STUDENT = 'STUDENT', 'Estudiante'
        OTHER = 'OTHER', 'Otro'
    
    # Estados de identidad verificada
    class IdentityVerificationStatus(models.TextChoices):
        NOT_VERIFIED = 'NOT_VERIFIED', 'No Verificada'
        PENDING = 'PENDING', 'Pendiente'
        IN_PROGRESS = 'IN_PROGRESS', 'En Progreso'
        APPROVED = 'APPROVED', 'Aprobada'
        DECLINED = 'DECLINED', 'Rechazada'
        MANUAL_REVIEW = 'MANUAL_REVIEW', 'Revisión Manual'
    
    # Estados de documentos
    class DocumentsStatus(models.TextChoices):
        NOT_REQUIRED = 'NOT_REQUIRED', 'No Requerida'
        PENDING = 'PENDING', 'Pendiente'
        COMPLETE = 'COMPLETE', 'Completa'
        OBSERVED = 'OBSERVED', 'Observada'
    
    # Relaciones
    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.PROTECT,
        related_name='loan_applications',
        verbose_name='Cliente/Prestatario'
    )
    product = models.ForeignKey(
        'products.CreditProduct',
        on_delete=models.PROTECT,
        related_name='loan_applications',
        verbose_name='Producto Crediticio'
    )
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='loan_applications',
        verbose_name='Sucursal'
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_loan_applications',
        verbose_name='Asignado a',
        help_text='Personal interno asignado para revisar la solicitud'
    )
    
    # Información de la solicitud
    application_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Número de Solicitud',
        help_text='Número único de identificación de la solicitud'
    )
    requested_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Monto Solicitado'
    )
    term_months = models.PositiveIntegerField(
        verbose_name='Plazo en Meses',
        validators=[MinValueValidator(1), MaxValueValidator(360)]
    )
    purpose = models.TextField(
        verbose_name='Propósito del Crédito',
        blank=True
    )
    
    # Información económica y laboral (CU-11)
    monthly_income = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Ingreso Mensual Aproximado'
    )
    employment_type = models.CharField(
        max_length=30,
        choices=EmploymentType.choices,
        null=True,
        blank=True,
        verbose_name='Tipo de Empleo'
    )
    employment_description = models.TextField(
        blank=True,
        verbose_name='Descripción Laboral/Económica',
        help_text='Detalles de la actividad laboral o económica'
    )
    additional_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Datos Adicionales',
        help_text='Información adicional en formato JSON'
    )
    
    # Estado y fechas
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name='Estado',
        db_index=True
    )
    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Envío'
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Revisión'
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Aprobación'
    )
    rejected_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Rechazo'
    )
    disbursed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Desembolso'
    )
    
    # Verificación de identidad (CU-13 integration)
    identity_verification_status = models.CharField(
        max_length=20,
        choices=IdentityVerificationStatus.choices,
        default=IdentityVerificationStatus.NOT_VERIFIED,
        verbose_name='Estado de Verificación de Identidad',
        db_index=True
    )
    
    # Estado de documentos (preparación para CU-12)
    documents_status = models.CharField(
        max_length=20,
        choices=DocumentsStatus.choices,
        default=DocumentsStatus.NOT_REQUIRED,
        verbose_name='Estado de Documentos'
    )
    
    # Evaluación y scoring
    credit_score = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1000)],
        verbose_name='Score de Crédito',
        help_text='Score calculado (0-1000)'
    )
    risk_level = models.CharField(
        max_length=20,
        choices=RiskLevel.choices,
        null=True,
        blank=True,
        verbose_name='Nivel de Riesgo'
    )
    debt_to_income_ratio = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Ratio Deuda/Ingreso',
        help_text='Porcentaje de deuda sobre ingreso'
    )
    
    # Términos aprobados (pueden diferir de los solicitados)
    approved_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Monto Aprobado'
    )
    approved_term_months = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Plazo Aprobado (meses)'
    )
    approved_interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Tasa de Interés Aprobada',
        help_text='Tasa anual en porcentaje'
    )
    monthly_payment = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Cuota Mensual'
    )
    
    # Usuarios responsables
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_applications',
        verbose_name='Revisado Por'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_applications',
        verbose_name='Aprobado Por'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_loan_applications',
        verbose_name='Creado Por'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_loan_applications',
        verbose_name='Actualizado Por'
    )
    
    # Notas y comentarios
    notes = models.TextField(
        blank=True,
        verbose_name='Notas Internas'
    )
    internal_notes = models.TextField(
        blank=True,
        verbose_name='Notas Internas Adicionales'
    )
    observation_reason = models.TextField(
        blank=True,
        verbose_name='Motivo de Observación',
        help_text='Razón por la cual la solicitud fue observada'
    )
    rejection_reason = models.TextField(
        blank=True,
        verbose_name='Motivo de Rechazo'
    )
    
    # Metadata
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    
    class Meta:
        verbose_name = 'Solicitud de Crédito'
        verbose_name_plural = 'Solicitudes de Crédito'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['institution', 'status']),
            models.Index(fields=['institution', 'client']),
            models.Index(fields=['institution', 'product']),
            models.Index(fields=['application_number']),
            models.Index(fields=['submitted_at']),
        ]
    
    def __str__(self):
        return f"{self.application_number} - {self.client.full_name} - ${self.requested_amount}"
    
    def save(self, *args, **kwargs):
        # Generar número de solicitud si no existe
        if not self.application_number:
            self.application_number = self.generate_application_number()
        super().save(*args, **kwargs)
    
    def generate_application_number(self):
        """Genera un número único de solicitud"""
        from django.utils import timezone
        import random
        
        year = timezone.now().year
        # Contar solicitudes del año actual
        count = LoanApplication.objects.filter(
            institution=self.institution,
            created_at__year=year
        ).count() + 1
        
        # Formato: INST-YEAR-COUNT-RANDOM
        random_suffix = random.randint(1000, 9999)
        return f"LOAN-{self.institution.id}-{year}-{count:04d}-{random_suffix}"
    
    @property
    def is_pending(self):
        """Verifica si la solicitud está pendiente de revisión"""
        return self.status in [self.Status.SUBMITTED, self.Status.UNDER_REVIEW]
    
    @property
    def can_be_edited(self):
        """Verifica si la solicitud puede ser editada"""
        return self.status == self.Status.DRAFT
    
    @property
    def can_be_submitted(self):
        """Verifica si la solicitud puede ser enviada"""
        return self.status == self.Status.DRAFT and self.requested_amount > 0
    
    @property
    def can_be_approved(self):
        """Verifica si la solicitud puede ser aprobada"""
        return self.status == self.Status.UNDER_REVIEW
    
    @property
    def can_be_rejected(self):
        """Verifica si la solicitud puede ser rechazada"""
        return self.status in [self.Status.SUBMITTED, self.Status.UNDER_REVIEW]
    
    @property
    def can_be_disbursed(self):
        """Verifica si la solicitud puede ser desembolsada"""
        return self.status == self.Status.APPROVED
    
    def calculate_monthly_payment(self):
        """Calcula la cuota mensual basada en los términos aprobados"""
        if not all([self.approved_amount, self.approved_term_months, self.approved_interest_rate]):
            return None
        
        # Usar el método del producto si está disponible
        if self.product:
            return self.product.calculate_monthly_payment(
                float(self.approved_amount),
                self.approved_term_months
            )
        
        # Cálculo básico con sistema francés
        amount = float(self.approved_amount)
        months = self.approved_term_months
        annual_rate = float(self.approved_interest_rate) / 100
        monthly_rate = annual_rate / 12
        
        if monthly_rate == 0:
            return Decimal(str(amount / months))
        
        payment = amount * (monthly_rate * (1 + monthly_rate) ** months) / \
                  ((1 + monthly_rate) ** months - 1)
        
        return Decimal(str(round(payment, 2)))


class LoanApplicationDocument(TenantModel):
    """
    Documentos adjuntos a una solicitud de crédito
    """
    
    class DocumentType(models.TextChoices):
        ID_DOCUMENT = 'ID_DOCUMENT', 'Documento de Identidad'
        INCOME_PROOF = 'INCOME_PROOF', 'Comprobante de Ingresos'
        BANK_STATEMENT = 'BANK_STATEMENT', 'Estado de Cuenta'
        EMPLOYMENT_LETTER = 'EMPLOYMENT_LETTER', 'Carta de Trabajo'
        TAX_RETURN = 'TAX_RETURN', 'Declaración de Impuestos'
        PROPERTY_DEED = 'PROPERTY_DEED', 'Escritura de Propiedad'
        OTHER = 'OTHER', 'Otro'
    
    application = models.ForeignKey(
        LoanApplication,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name='Solicitud'
    )
    document_type = models.CharField(
        max_length=30,
        choices=DocumentType.choices,
        verbose_name='Tipo de Documento'
    )
    file = models.FileField(
        upload_to='loan_applications/%Y/%m/',
        verbose_name='Archivo'
    )
    file_name = models.CharField(
        max_length=255,
        verbose_name='Nombre del Archivo'
    )
    file_size = models.PositiveIntegerField(
        verbose_name='Tamaño (bytes)',
        help_text='Tamaño del archivo en bytes'
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Descripción'
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_loan_documents',
        verbose_name='Subido Por'
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name='Verificado'
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_loan_documents',
        verbose_name='Verificado Por'
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Verificación'
    )
    
    class Meta:
        verbose_name = 'Documento de Solicitud'
        verbose_name_plural = 'Documentos de Solicitud'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_document_type_display()} - {self.file_name}"


class LoanApplicationComment(TenantModel):
    """
    Comentarios y notas sobre una solicitud de crédito
    """
    
    application = models.ForeignKey(
        LoanApplication,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Solicitud'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='loan_comments',
        verbose_name='Usuario'
    )
    comment = models.TextField(
        verbose_name='Comentario'
    )
    is_internal = models.BooleanField(
        default=True,
        verbose_name='Comentario Interno',
        help_text='Si es interno, solo lo ven los empleados'
    )
    
    class Meta:
        verbose_name = 'Comentario de Solicitud'
        verbose_name_plural = 'Comentarios de Solicitud'
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comentario de {self.user} en {self.application.application_number}"


class LoanApplicationStatusHistory(TenantModel):
    """
    Historial de cambios de estado de una solicitud de crédito (CU-11: Timeline)
    
    Registra cada cambio de estado de la solicitud con detalles del actor,
    motivo y metadata adicional. Permite generar un timeline visible al prestatario
    e internamente para auditoría.
    """
    
    application = models.ForeignKey(
        LoanApplication,
        on_delete=models.CASCADE,
        related_name='status_history',
        verbose_name='Solicitud'
    )
    previous_status = models.CharField(
        max_length=20,
        verbose_name='Estado Anterior',
        help_text='Estado anterior de la solicitud'
    )
    new_status = models.CharField(
        max_length=20,
        verbose_name='Nuevo Estado',
        help_text='Nuevo estado de la solicitud'
    )
    title = models.CharField(
        max_length=255,
        verbose_name='Título del Evento',
        help_text='Título visible para el prestatario y staff'
    )
    description = models.TextField(
        verbose_name='Descripción',
        blank=True,
        help_text='Descripción detallada del cambio de estado'
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='status_changes_made',
        verbose_name='Actor',
        help_text='Usuario que realizó el cambio de estado'
    )
    actor_role = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Rol del Actor',
        help_text='Rol del usuario que hizo el cambio'
    )
    is_visible_to_borrower = models.BooleanField(
        default=True,
        verbose_name='Visible para Prestatario',
        help_text='Si el evento es visible en el timeline del prestatario'
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Metadata',
        help_text='Información adicional en formato JSON'
    )
    
    class Meta:
        verbose_name = 'Historial de Estado de Solicitud'
        verbose_name_plural = 'Historiales de Estados de Solicitudes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['institution', 'application']),
            models.Index(fields=['institution', 'created_at']),
            models.Index(fields=['application', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.application.application_number}: {self.previous_status} → {self.new_status}"

