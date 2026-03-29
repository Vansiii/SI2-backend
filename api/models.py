from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		abstract = True


class FinancialInstitution(TimeStampedModel):
	class InstitutionType(models.TextChoices):
		BANKING = 'banking', 'Banco Comercial'
		MICROFINANCE = 'microfinance', 'Microfinanciera'
		COOPERATIVE = 'cooperative', 'Cooperativa de Credito'
		FINTECH = 'fintech', 'Fintech'

	name = models.CharField(max_length=255)
	slug = models.SlugField(max_length=100, unique=True)
	institution_type = models.CharField(
		max_length=20,
		choices=InstitutionType.choices,
		default=InstitutionType.BANKING,
	)
	is_active = models.BooleanField(default=True)
	created_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='created_financial_institutions',
	)

	class Meta:
		db_table = 'financial_institutions'
		ordering = ['-created_at']

	def __str__(self) -> str:
		return f'{self.name} ({self.slug})'


class FinancialInstitutionMembership(TimeStampedModel):
	class Role(models.TextChoices):
		ADMIN = 'admin', 'Administrador'
		ANALYST = 'analyst', 'Analista de Credito'
		LOAN_OFFICER = 'loan_officer', 'Oficial de Credito'
		MANAGER = 'manager', 'Gerente'

	institution = models.ForeignKey(
		FinancialInstitution,
		on_delete=models.CASCADE,
		related_name='memberships',
	)
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='institution_memberships',
	)
	role = models.CharField(max_length=20, choices=Role.choices, default=Role.ADMIN)
	is_active = models.BooleanField(default=True)

	class Meta:
		db_table = 'financial_institution_memberships'
		constraints = [
			models.UniqueConstraint(
				fields=['institution', 'user'],
				name='uniq_institution_user_membership',
			)
		]
		ordering = ['-created_at']

	def __str__(self) -> str:
		return f'{self.user} -> {self.institution} ({self.role})'


# Parte erick sprint 0
class Permission(TimeStampedModel):
	code = models.CharField(max_length=80, unique=True)
	name = models.CharField(max_length=120)
	description = models.TextField(blank=True)
	is_active = models.BooleanField(default=True)

	class Meta:
		db_table = 'permissions'
		ordering = ['name']

	def __str__(self) -> str:
		return f'{self.code} - {self.name}'


class Role(TimeStampedModel):
	institution = models.ForeignKey(
		FinancialInstitution,
		on_delete=models.CASCADE,
		related_name='roles',
	)
	name = models.CharField(max_length=100)
	description = models.TextField(blank=True)
	is_active = models.BooleanField(default=True)
	permissions = models.ManyToManyField(
		Permission,
		blank=True,
		related_name='roles',
	)

	class Meta:
		db_table = 'roles'
		ordering = ['name']
		constraints = [
			models.UniqueConstraint(
				fields=['institution', 'name'],
				name='uniq_role_name_per_institution',
			)
		]

	def __str__(self) -> str:
		return f'{self.name} ({self.institution.slug})'
