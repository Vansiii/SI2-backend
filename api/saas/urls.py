"""
URLs para gestión de suscripciones SaaS.
"""

from django.urls import path
from .views import (
    # Planes
    SubscriptionPlanListCreateAPIView,
    SubscriptionPlanDetailAPIView,
    # Suscripciones
    SubscriptionListCreateAPIView,
    SubscriptionDetailAPIView,
    ActivateSubscriptionAPIView,
    SuspendSubscriptionAPIView,
    CancelSubscriptionAPIView,
    MySubscriptionAPIView,
    ChangeMySubscriptionPlanAPIView,
    # Admin SaaS
    SaaSStatsAPIView,
    TenantListAPIView,
    TenantDetailAPIView,
    TenantToggleActiveAPIView,
    PermissionListAPIView,
    PermissionDetailAPIView,
    PermissionCreateAPIView,
    PermissionSyncAPIView,
    PermissionCoverageAPIView,
    SaaSUserListAPIView,
    SaaSRoleListAPIView,
)

app_name = 'saas'

urlpatterns = [
    # ============================================================
    # PLANES DE SUSCRIPCIÓN
    # ============================================================
    path(
        'plans/',
        SubscriptionPlanListCreateAPIView.as_view(),
        name='plan-list-create'
    ),
    path(
        'plans/<int:id>/',
        SubscriptionPlanDetailAPIView.as_view(),
        name='plan-detail'
    ),
    
    # ============================================================
    # SUSCRIPCIONES
    # ============================================================
    path(
        'subscriptions/',
        SubscriptionListCreateAPIView.as_view(),
        name='subscription-list-create'
    ),
    path(
        'subscriptions/<int:id>/',
        SubscriptionDetailAPIView.as_view(),
        name='subscription-detail'
    ),
    path(
        'subscriptions/<int:id>/activate/',
        ActivateSubscriptionAPIView.as_view(),
        name='subscription-activate'
    ),
    path(
        'subscriptions/<int:id>/suspend/',
        SuspendSubscriptionAPIView.as_view(),
        name='subscription-suspend'
    ),
    path(
        'subscriptions/<int:id>/cancel/',
        CancelSubscriptionAPIView.as_view(),
        name='subscription-cancel'
    ),
    
    # ============================================================
    # MI SUSCRIPCIÓN (Para instituciones)
    # ============================================================
    path(
        'my-subscription/',
        MySubscriptionAPIView.as_view(),
        name='my-subscription'
    ),
    path(
        'my-subscription/change-plan/',
        ChangeMySubscriptionPlanAPIView.as_view(),
        name='change-my-subscription-plan'
    ),
    
    # ============================================================
    # ADMINISTRACIÓN SAAS
    # ============================================================
    path(
        'stats/',
        SaaSStatsAPIView.as_view(),
        name='saas-stats'
    ),
    path(
        'tenants/',
        TenantListAPIView.as_view(),
        name='tenant-list'
    ),
    path(
        'tenants/<int:id>/',
        TenantDetailAPIView.as_view(),
        name='tenant-detail'
    ),
    path(
        'tenants/<int:id>/toggle-active/',
        TenantToggleActiveAPIView.as_view(),
        name='tenant-toggle-active'
    ),
    path(
        'permissions/',
        PermissionListAPIView.as_view(),
        name='permission-list'
    ),
    path(
        'permissions/<int:id>/',
        PermissionDetailAPIView.as_view(),
        name='permission-detail'
    ),
    path(
        'permissions/sync/',
        PermissionSyncAPIView.as_view(),
        name='permission-sync'
    ),
    path(
        'permissions/coverage/',
        PermissionCoverageAPIView.as_view(),
        name='permission-coverage'
    ),
    path(
        'users/',
        SaaSUserListAPIView.as_view(),
        name='saas-user-list'
    ),
    path(
        'roles/',
        SaaSRoleListAPIView.as_view(),
        name='saas-role-list'
    ),
]
