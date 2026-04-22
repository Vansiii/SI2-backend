from django.urls import include, path

from .views import health_check
from .utils.debug_views import DebugPermissionsView

urlpatterns = [
    path('health/', health_check, name='health-check'),
    path('debug/permissions/', DebugPermissionsView.as_view(), name='debug-permissions'),
    path('', include('api.registration.urls')),
    path('', include('api.authentication.urls')),
    # Parte erick sprint 0
    path('', include('api.roles.urls')),
    # Sprint 3: Gestión de usuarios
    path('users/', include('api.users.urls')),
    # Sprint 6: Panel de administración SaaS
    path('saas/', include('api.saas.urls')),
    # Sprint 1: Gestión de clientes/prestatarios
    path('clients/', include('api.clients.urls')),
    # Sprint 2: Gestión de sucursales
    path('branches/', include('api.branches.urls')),
    # Sprint 2: Gestión de productos crediticios
    path('products/', include('api.products.urls')),
    # Sprint 3: Gestión de solicitudes de crédito
    path('loans/', include('api.loans.urls')),
    # Auditoría y seguridad (solo SaaS admin)
    path('', include('api.audit.urls')),
]
