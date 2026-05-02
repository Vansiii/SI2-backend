"""
Modelos relacionados con instituciones financieras (tenants).
"""
from uuid import uuid4

from django.conf import settings
from django.db import models

from api.core.models import TimeStampedModel


DEFAULT_TENANT_PRIMARY_COLOR = '#2563EB'
DEFAULT_TENANT_SECONDARY_COLOR = '#0F172A'
DEFAULT_TENANT_ACCENT_COLOR = '#0EA5E9'
DEFAULT_TENANT_BACKGROUND_COLOR = '#F8FAFC'
DEFAULT_TENANT_TEXT_COLOR = '#0F172A'


def tenant_branding_logo_upload_to(instance, filename: str) -> str:
	"""Genera la ruta de almacenamiento del logo por tenant."""
	name_parts = filename.rsplit('.', 1)
	extension = name_parts[1].lower() if len(name_parts) == 2 else 'png'
	allowed_extensions = {'png', 'jpg', 'jpeg', 'webp', 'svg'}
	if extension not in allowed_extensions:
		extension = 'png'

	slug = instance.institution.slug if instance.institution_id else 'tenant'
	return f'tenant-branding/{slug}/logo-{uuid4().hex}.{extension}'


class FinancialInstitution(TimeStampedModel):
	"""
	Modelo de institución financiera (tenant).
	
	Representa una entidad financiera que usa el sistema SaaS.
	Cada institución tiene sus propios datos, usuarios y configuraciones aisladas.
	"""
	
	class InstitutionType(models.TextChoices):
		BANKING = 'banking', 'Banco Comercial'
		MICROFINANCE = 'microfinance', 'Microfinanciera'
		COOPERATIVE = 'cooperative', 'Cooperativa de Credito'
		FINTECH = 'fintech', 'Fintech'

	name = models.CharField(max_length=255, verbose_name='Nombre')
	slug = models.SlugField(max_length=100, unique=True, verbose_name='Slug')
	institution_type = models.CharField(
		max_length=20,
		choices=InstitutionType.choices,
		default=InstitutionType.BANKING,
		verbose_name='Tipo de Institución'
	)
	is_active = models.BooleanField(default=True, verbose_name='Activo')
	created_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='created_financial_institutions',
		verbose_name='Creado por'
	)

	class Meta:
		db_table = 'financial_institutions'
		ordering = ['-created_at']
		verbose_name = 'Institución Financiera'
		verbose_name_plural = 'Instituciones Financieras'

	def __str__(self) -> str:
		return f'{self.name} ({self.slug})'


class FinancialInstitutionMembership(TimeStampedModel):
	"""
	Relación entre usuario e institución financiera.
	
	Representa la membresía de un usuario en una institución específica.
	Un usuario puede pertenecer a múltiples instituciones.
	"""
	
	institution = models.ForeignKey(
		FinancialInstitution,
		on_delete=models.CASCADE,
		related_name='memberships',
		verbose_name='Institución'
	)
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='institution_memberships',
		verbose_name='Usuario'
	)
	is_active = models.BooleanField(default=True, verbose_name='Activo')

	class Meta:
		db_table = 'financial_institution_memberships'
		constraints = [
			models.UniqueConstraint(
				fields=['institution', 'user'],
				name='uniq_institution_user_membership',
			)
		]
		ordering = ['-created_at']
		verbose_name = 'Membresía de Institución'
		verbose_name_plural = 'Membresías de Instituciones'

	def __str__(self) -> str:
		return f'{self.user} -> {self.institution}'


class TenantBranding(TimeStampedModel):
	"""Configuración visual white-label de una institución financiera."""

	institution = models.OneToOneField(
		FinancialInstitution,
		on_delete=models.CASCADE,
		related_name='branding',
		verbose_name='Institución Financiera',
	)
	display_name = models.CharField(
		max_length=255,
		verbose_name='Nombre Visible',
		help_text='Nombre institucional que se mostrará en la interfaz',
	)
	logo = models.FileField(
		upload_to=tenant_branding_logo_upload_to,
		blank=True,
		null=True,
		verbose_name='Logo Principal',
		help_text='Logo principal para la interfaz white-label',
	)
	primary_color = models.CharField(
		max_length=7,
		default=DEFAULT_TENANT_PRIMARY_COLOR,
		verbose_name='Color Primario',
	)
	secondary_color = models.CharField(
		max_length=7,
		default=DEFAULT_TENANT_SECONDARY_COLOR,
		verbose_name='Color Secundario',
	)
	accent_color = models.CharField(
		max_length=7,
		default=DEFAULT_TENANT_ACCENT_COLOR,
		verbose_name='Color de Acento',
	)
	background_color = models.CharField(
		max_length=7,
		default=DEFAULT_TENANT_BACKGROUND_COLOR,
		verbose_name='Color de Fondo',
	)
	text_color = models.CharField(
		max_length=7,
		default=DEFAULT_TENANT_TEXT_COLOR,
		verbose_name='Color de Texto',
	)
	is_active = models.BooleanField(
		default=True,
		verbose_name='Activo',
		help_text='Indica si la personalización está aplicada',
	)

	class Meta:
		db_table = 'tenant_branding'
		ordering = ['institution__name']
		verbose_name = 'Personalización Visual del Tenant'
		verbose_name_plural = 'Personalizaciones Visuales de Tenant'
		indexes = [
			models.Index(fields=['institution']),
			models.Index(fields=['is_active']),
		]

	def __str__(self) -> str:
		return f'{self.institution.name} - Branding'

	@classmethod
	def default_payload(cls, institution: FinancialInstitution) -> dict:
		"""Retorna la configuración por defecto para un tenant."""
		return {
			'id': None,
			'tenant': {
				'id': institution.id,
				'name': institution.name,
				'slug': institution.slug,
			},
			'display_name': institution.name,
			'logo': None,
			'logo_url': None,
			'primary_color': DEFAULT_TENANT_PRIMARY_COLOR,
			'secondary_color': DEFAULT_TENANT_SECONDARY_COLOR,
			'accent_color': DEFAULT_TENANT_ACCENT_COLOR,
			'background_color': DEFAULT_TENANT_BACKGROUND_COLOR,
			'text_color': DEFAULT_TENANT_TEXT_COLOR,
			'is_active': True,
			'created_at': None,
			'updated_at': None,
		}
