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
    # Clients
    'Client',
    'ClientDocument',
    # SaaS
    'SubscriptionPlan',
    'Subscription',
]
