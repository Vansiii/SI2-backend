from django.urls import include, path

from .views import health_check
from .debug_views import DebugPermissionsView

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
]
