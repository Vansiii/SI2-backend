"""
Core permission helpers for the API.
"""

from rest_framework.permissions import BasePermission


def require_permission(permission_code: str):
    """
    Factory that returns a DRF BasePermission class enforcing the given permission code.

    Usage:
        permission_classes = [IsAuthenticated, require_permission('collaterals.view')]
    """

    class _Permission(BasePermission):
        def has_permission(self, request, view):
            if not request.user or not request.user.is_authenticated:
                return False

            # SaaS admins always pass
            if hasattr(request.user, 'profile') and request.user.profile.is_saas_admin():
                return True

            tenant = getattr(request, 'tenant', None)
            if tenant is None:
                return False

            if hasattr(request.user, 'profile'):
                return request.user.profile.has_permission(permission_code, tenant)

            return False

    _Permission.__name__ = f'HasPermission_{permission_code.replace(".", "_")}'
    return _Permission
