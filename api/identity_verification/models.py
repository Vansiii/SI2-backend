"""
Modelos para verificación de identidad con Didit
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import URLValidator
from django.utils import timezone
from decimal import Decimal
from api.core.models import TenantModel

User = get_user_model()


class IdentityVerification(TenantModel):
	"""
	Modelo para registrar verificaciones de identidad de prestatarios.
	
	Asocia un usuario/prestatario con un proveedor externo (Didit) y registra
	el estado y resultado de la verificación.
	
	Relaciones:
	- institution (heredado de TenantModel): Institución financiera propietaria
	- user: Usuario prestatario que se verifica
	- credit_application: Solicitud de crédito asociada (opcional)
	- branch: Sucursal donde se origina la solicitud (opcional)
	
	Estados:
	- PENDING: Sesión creada, usuario aún no inicia
	- IN_PROGRESS: Usuario inició el flujo en Didit
	- APPROVED: Identidad validada exitosamente
	- DECLINED: Identidad rechazada
	- MANUAL_REVIEW: Requiere revisión manual
	- EXPIRED: Sesión expirada
	- ERROR: Error técnico
	"""
	
	class Provider(models.TextChoices):
		DIDIT = 'DIDIT', 'Didit'
	
	class Status(models.TextChoices):
		PENDING = 'PENDING', 'Pendiente'
		IN_PROGRESS = 'IN_PROGRESS', 'En Progreso'
		APPROVED = 'APPROVED', 'Aprobada'
		DECLINED = 'DECLINED', 'Rechazada'
		MANUAL_REVIEW = 'MANUAL_REVIEW', 'Revisión Manual'
		EXPIRED = 'EXPIRED', 'Expirada'
		ERROR = 'ERROR', 'Error'
	
	class Decision(models.TextChoices):
		APPROVED = 'APPROVED', 'Aprobado'
		DECLINED = 'DECLINED', 'Rechazado'
		PENDING = 'PENDING', 'Pendiente'
		MANUAL_REVIEW = 'MANUAL_REVIEW', 'Revisión Manual'
	
	# Identidad de la verificación
	user = models.ForeignKey(
		User,
		on_delete=models.PROTECT,
		related_name='identity_verifications',
		help_text='Usuario prestatario siendo verificado'
	)
	credit_application = models.ForeignKey(
		'loans.LoanApplication',
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='identity_verifications',
		help_text='Solicitud de crédito asociada (opcional)'
	)
	branch = models.ForeignKey(
		'branches.Branch',
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='identity_verifications',
		help_text='Sucursal donde se originó la solicitud'
	)
	
	# Información del proveedor
	provider = models.CharField(
		max_length=50,
		choices=Provider.choices,
		default=Provider.DIDIT,
		db_index=True,
		help_text='Proveedor de verificación de identidad'
	)
	provider_session_id = models.CharField(
		max_length=255,
		unique=True,
		null=True,
		blank=True,
		db_index=True,
		help_text='ID único de sesión en el proveedor (e.g., Didit session_id)'
	)
	provider_session_token = models.CharField(
		max_length=500,
		null=True,
		blank=True,
		help_text='Token de sesión del proveedor (si aplica y es necesario). SENSIBLE.'
	)
	
	# URL de verificación
	verification_url = models.URLField(
		null=True,
		blank=True,
		help_text='URL del hosting Didit o similar donde el usuario completa la verificación'
	)
	
	# Estado de la verificación
	status = models.CharField(
		max_length=20,
		choices=Status.choices,
		default=Status.PENDING,
		db_index=True,
		help_text='Estado actual de la verificación'
	)
	decision = models.CharField(
		max_length=20,
		choices=Decision.choices,
		default=Decision.PENDING,
		db_index=True,
		help_text='Decisión de aprobación/rechazo'
	)
	
	# Datos extraídos/confirmados
	document_type = models.CharField(
		max_length=50,
		blank=True,
		help_text='Tipo de documento (e.g., PASSPORT, NATIONAL_ID, DRIVER_LICENSE)'
	)
	document_number = models.CharField(
		max_length=50,
		blank=True,
		db_index=True,
		help_text='Número de documento identificado'
	)
	full_name = models.CharField(
		max_length=255,
		blank=True,
		help_text='Nombre completo confirmado en la verificación'
	)
	date_of_birth = models.DateField(
		null=True,
		blank=True,
		help_text='Fecha de nacimiento confirmada'
	)
	country = models.CharField(
		max_length=2,
		blank=True,
		help_text='Código de país ISO 3166-1 alpha-2'
	)
	
	# Resultado y errores
	error_message = models.TextField(
		blank=True,
		help_text='Mensaje de error si la verificación falló o tuvo problemas'
	)
	
	# Respuesta del proveedor (JSON, filtrada de datos sensibles)
	raw_response = models.JSONField(
		default=dict,
		blank=True,
		help_text='Respuesta del proveedor (solo campos no-sensibles y útiles para auditoría)'
	)
	
	# Fechas de control
	started_at = models.DateTimeField(
		auto_now_add=True,
		help_text='Cuando se creó la sesión de verificación'
	)
	completed_at = models.DateTimeField(
		null=True,
		blank=True,
		db_index=True,
		help_text='Cuando se completó/resolvió la verificación'
	)
	expires_at = models.DateTimeField(
		null=True,
		blank=True,
		db_index=True,
		help_text='Cuando expira la sesión (si aplica)'
	)
	webhook_received_at = models.DateTimeField(
		null=True,
		blank=True,
		help_text='Último webhook recibido del proveedor'
	)
	
	class Meta:
		db_table = 'identity_verifications'
		verbose_name = 'Verificación de Identidad'
		verbose_name_plural = 'Verificaciones de Identidad'
		ordering = ['-created_at']
		indexes = [
			models.Index(fields=['institution', 'user']),
			models.Index(fields=['institution', 'status']),
			models.Index(fields=['user', '-created_at']),
			models.Index(fields=['provider_session_id', 'provider']),
			models.Index(fields=['credit_application', 'status']),
		]
		unique_together = [
			# No permitir múltiples verificaciones activas para la misma app de crédito
			# Se validará a nivel de servicio, no de BD para permitir reintentos
		]
	
	def __str__(self) -> str:
		return f'IdentityVerification #{self.id} ({self.user.email}) - {self.get_status_display()}'
	
	@property
	def is_active(self) -> bool:
		"""Determina si la verificación aún está en proceso"""
		return self.status in [self.Status.PENDING, self.Status.IN_PROGRESS]
	
	@property
	def is_expired(self) -> bool:
		"""Determina si la sesión ha expirado"""
		if self.expires_at:
			return timezone.now() > self.expires_at
		return False
	
	@property
	def is_approved(self) -> bool:
		"""Determina si fue aprobada"""
		return self.status == self.Status.APPROVED and self.decision == self.Decision.APPROVED
	
	@property
	def is_declined(self) -> bool:
		"""Determina si fue rechazada"""
		return self.status == self.Status.DECLINED and self.decision == self.Decision.DECLINED
	
	def mark_approved(self, data: dict = None) -> None:
		"""Marca la verificación como aprobada"""
		self.status = self.Status.APPROVED
		self.decision = self.Decision.APPROVED
		self.completed_at = timezone.now()
		if data:
			# Extraer campos del resultado sin datos sensibles
			self.full_name = data.get('full_name') or self.full_name
			if not self.full_name and (data.get('first_name') or data.get('last_name')):
				self.full_name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
			
			self.document_type = data.get('document_type', self.document_type)
			self.document_number = data.get('document_number', self.document_number)
			self.date_of_birth = data.get('date_of_birth', self.date_of_birth)
			self.country = data.get('country', self.country)
		self.save()
	
	def mark_declined(self, reason: str = '') -> None:
		"""Marca la verificación como rechazada"""
		self.status = self.Status.DECLINED
		self.decision = self.Decision.DECLINED
		self.completed_at = timezone.now()
		self.error_message = reason or 'Verificación rechazada por el proveedor'
		self.save()
	
	def mark_error(self, error: str) -> None:
		"""Marca la verificación como error"""
		self.status = self.Status.ERROR
		self.error_message = error
		self.save()
	
	def mark_expired(self) -> None:
		"""Marca la verificación como expirada"""
		self.status = self.Status.EXPIRED
		self.error_message = 'Sesión expirada'
		self.completed_at = timezone.now()
		self.save()


class IdentityVerificationWebhook(models.Model):
	"""
	Modelo para registrar webhooks recibidos del proveedor.
	
	Útil para:
	- Auditar y debuggear eventos
	- Implementar idempotencia (no procesar dos veces el mismo evento)
	- Rastrear qué eventos llegaron y en qué orden
	"""
	
	class Status(models.TextChoices):
		PENDING = 'PENDING', 'Pendiente'
		PROCESSED = 'PROCESSED', 'Procesado'
		FAILED = 'FAILED', 'Fallido'
		DUPLICATE = 'DUPLICATE', 'Duplicado'
	
	# Identidad del evento
	provider = models.CharField(
		max_length=50,
		db_index=True,
		help_text='Proveedor que envió el webhook'
	)
	provider_event_id = models.CharField(
		max_length=255,
		unique=True,
		db_index=True,
		help_text='ID único del evento en el proveedor'
	)
	provider_session_id = models.CharField(
		max_length=255,
		db_index=True,
		help_text='ID de sesión a la que corresponde el evento'
	)
	
	# Payload y control
	payload = models.JSONField(
		help_text='Payload completo del webhook recibido'
	)
	status = models.CharField(
		max_length=20,
		choices=Status.choices,
		default=Status.PENDING,
		help_text='Estado del procesamiento del webhook'
	)
	error_message = models.TextField(
		blank=True,
		help_text='Mensaje de error si el procesamiento falló'
	)
	
	# Verificación asociada (una vez procesada)
	identity_verification = models.ForeignKey(
		IdentityVerification,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='webhooks',
		help_text='Verificación de identidad asociada'
	)
	
	# Fechas
	received_at = models.DateTimeField(
		auto_now_add=True,
		help_text='Cuándo se recibió el webhook'
	)
	processed_at = models.DateTimeField(
		null=True,
		blank=True,
		help_text='Cuándo se procesó'
	)
	
	class Meta:
		db_table = 'identity_verification_webhooks'
		verbose_name = 'Webhook de Verificación de Identidad'
		verbose_name_plural = 'Webhooks de Verificación de Identidad'
		ordering = ['-received_at']
		indexes = [
			models.Index(fields=['provider', 'provider_event_id']),
			models.Index(fields=['provider_session_id', 'status']),
			models.Index(fields=['-received_at']),
		]
	
	def __str__(self) -> str:
		return f'Webhook {self.provider_event_id} - {self.get_status_display()}'
	
	def mark_processed(self, verification: IdentityVerification = None) -> None:
		"""Marca el webhook como procesado"""
		self.status = self.Status.PROCESSED
		self.processed_at = timezone.now()
		if verification:
			self.identity_verification = verification
		self.save()
	
	def mark_failed(self, error: str) -> None:
		"""Marca el webhook como fallido"""
		self.status = self.Status.FAILED
		self.error_message = error
		self.processed_at = timezone.now()
		self.save()
	
	def mark_duplicate(self) -> None:
		"""Marca el webhook como duplicado"""
		self.status = self.Status.DUPLICATE
		self.processed_at = timezone.now()
		self.save()
