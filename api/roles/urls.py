from django.urls import path

from .views import (
    PermissionListAPIView,
    RoleDetailAPIView,
    RoleListCreateAPIView,
    RolePermissionAssignmentAPIView,
    RolePermissionDetailAPIView,
)

# Parte erick sprint 0
urlpatterns = [
    path('roles/', RoleListCreateAPIView.as_view(), name='role-list-create'),
    path('roles/<int:role_id>/', RoleDetailAPIView.as_view(), name='role-detail'),
    path('roles/<int:role_id>/permissions/', RolePermissionAssignmentAPIView.as_view(), name='role-assign-permissions'),
    path(
        'roles/<int:role_id>/permissions/<int:permission_id>/',
        RolePermissionDetailAPIView.as_view(),
        name='role-remove-permission',
    ),
    path('permissions/', PermissionListAPIView.as_view(), name='permission-list'),
]
