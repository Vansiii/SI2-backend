"""
Modelos relacionados con instituciones financieras (tenants).
"""
from django.conf import settings
from django.db import models
from api.core.models import TimeStampedModel


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
