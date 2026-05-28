from django.conf import settings
from django.db import models

# ============================================================
# MODELOS DE GARANTIAS
# ============================================================
from api.garantias.models import (
    Collateral,
    Guarantor,
    CollateralDocument,
    CollateralValuation,
)

# ============================================================
# MODELOS DE AUDITORÍA
# ============================================================
from api.audit.models import (
    AuditLog,
    SecurityEvent,
)


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
	role = models.CharField(
		max_length=20,
		choices=Role.choices,
		default=Role.ANALYST,
	)

	class Meta:
		db_table = 'financial_institution_memberships'
		constraints = [
			models.UniqueConstraint(
				fields=['institution', 'user'],
				name='uniq_institution_user_membership',
			)
		]
		ordering = ['-created_at']
"""
Archivo de compatibilidad para imports de modelos.

Este archivo mantiene la compatibilidad con código existente que importa
modelos desde api.models. Los modelos ahora están organizados en módulos
separados pero se re-exportan aquí para mantener la compatibilidad.

IMPORTANTE: Para código nuevo, importar directamente desde los módulos:
    from api.core.models import TimeStampedModel, TenantModel
    from api.tenants.models import FinancialInstitution
    from api.authentication.models import PasswordResetToken
    etc.
"""

# ============================================================
# MODELOS CORE (base abstractos)
# ============================================================
from api.core.models import (
    TimeStampedModel,
    TenantModel,
)

# ============================================================
# MODELOS DE TENANTS (instituciones financieras)
# ============================================================
from api.tenants.models import (
    FinancialInstitution,
    FinancialInstitutionMembership,
    TenantBranding,
)

# ============================================================
# MODELOS DE AUTENTICACIÓN
# ============================================================
from api.authentication.models import (
    PasswordResetToken,
    LoginAttempt,
    AuthChallenge,
    EmailTwoFactorCode,
    TwoFactorAuth,
)

# ============================================================
# MODELOS DE ROLES Y PERMISOS
# ============================================================
from api.roles.models import (
    Permission,
    Role,
    UserRole,
)

# ============================================================
# MODELOS DE USUARIOS
# ============================================================
from api.users.models import (
    UserProfile,
)

# ============================================================
# MODELOS DE CLIENTES
# ============================================================
from api.clients.models import (
    Client,
    ClientDocument,
)

# ============================================================
# MODELOS DE SUCURSALES
# ============================================================
from api.branches.models import (
    Branch,
)

# ============================================================
# MODELOS DE PRODUCTOS CREDITICIOS
# ============================================================
from api.products.models import (
    CreditProduct,
    ProductRequirement,
)

# ============================================================
# MODELOS DE AUDITORÍA
# ============================================================
from api.audit.models import (
    AuditLog,
    SecurityEvent,
)

# ============================================================
# MODELOS DE SUSCRIPCIONES SAAS
# ============================================================
from api.saas.models import (
    SubscriptionPlan,
    Subscription,
)

# ============================================================
# EXPORTAR TODOS LOS MODELOS
# ============================================================
__all__ = [
    # Core
    'TimeStampedModel',
    'TenantModel',
    # Tenants
    'FinancialInstitution',
    'FinancialInstitutionMembership',
    'TenantBranding',
    # Authentication
    'PasswordResetToken',
    'LoginAttempt',
    'AuthChallenge',
    'EmailTwoFactorCode',
    'TwoFactorAuth',
    # Roles
    'Permission',
    'Role',
    'UserRole',
    # Users
    'UserProfile',
    # Audit
    'AuditLog',
    'SecurityEvent',
    # Products
    'CreditProduct',
    'ProductRequirement',
    # Garantias
    'Collateral',
    'Guarantor',
    'CollateralDocument',
    'CollateralValuation',
    # Clients
    'Client',
    'ClientDocument',
    # Branches
    'Branch',
    # SaaS
    'SubscriptionPlan',
    'Subscription',
]
