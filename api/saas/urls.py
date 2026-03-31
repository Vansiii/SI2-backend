"""
URLs para el panel de administración SaaS.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TenantListAPIView,
    TenantDetailAPIView,
    TenantStatsAPIView,
    TenantToggleActiveAPIView,
    # Sprint 8: Gestión de Permisos y Vistas Multi-Tenant
    PermissionManagementViewSet,
    SaaSUserListAPIView,
    SaaSRoleListAPIView,
)

# Router para ViewSets
router = DefaultRouter()
router.register(r'permissions', PermissionManagementViewSet, basename='saas-permission')

urlpatterns = [
    # Tenants
    path('tenants/', TenantListAPIView.as_view(), name='saas-tenant-list'),
    path('tenants/<int:tenant_id>/', TenantDetailAPIView.as_view(), name='saas-tenant-detail'),
    path('tenants/<int:tenant_id>/toggle-active/', TenantToggleActiveAPIView.as_view(), name='saas-tenant-toggle'),
    
    # Estadísticas globales
    path('stats/', TenantStatsAPIView.as_view(), name='saas-stats'),
    
    # Sprint 8: Usuarios y Roles Multi-Tenant
    path('users/', SaaSUserListAPIView.as_view(), name='saas-users'),
    path('roles/', SaaSRoleListAPIView.as_view(), name='saas-roles'),
    
    # Sprint 8: Gestión de Permisos (ViewSet)
    path('', include(router.urls)),
]
