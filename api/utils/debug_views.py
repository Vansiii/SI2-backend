"""
Vistas de debug para diagnosticar problemas de permisos
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status


class DebugPermissionsView(APIView):
    """Vista para debuggear permisos del usuario actual"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Retorna información de debug sobre permisos del usuario"""
        
        user = request.user
        debug_info = {
            'user': {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'is_authenticated': user.is_authenticated,
                'is_active': user.is_active,
            },
            'profile': None,
            'tenant': None,
            'user_type': None,
            'memberships': [],
            'roles': [],
            'permissions': [],
            'has_users_view': False,
        }
        
        # Verificar perfil
        if hasattr(user, 'profile'):
            profile = user.profile
            debug_info['profile'] = {
                'exists': True,
                'user_type': profile.user_type,
                'is_saas_admin': profile.is_saas_admin(),
            }
            debug_info['user_type'] = profile.user_type
            
            # Verificar tenant
            if hasattr(request, 'tenant') and request.tenant:
                debug_info['tenant'] = {
                    'id': request.tenant.id,
                    'name': request.tenant.name,
                    'slug': request.tenant.slug,
                }
                
                # Obtener permisos en la institución
                permissions = profile.get_permissions_in_institution(request.tenant)
                debug_info['permissions'] = list(permissions.values_list('code', flat=True))
                debug_info['permissions_count'] = permissions.count()
                
                # Verificar permiso específico
                debug_info['has_users_view'] = profile.has_permission('users.view', request.tenant)
            else:
                debug_info['tenant'] = None
                debug_info['tenant_error'] = 'request.tenant is None'
        else:
            debug_info['profile'] = {
                'exists': False,
                'error': 'User has no profile'
            }
        
        # Obtener memberships
        memberships = user.institution_memberships.filter(is_active=True)
        debug_info['memberships'] = [
            {
                'institution': m.institution.name,
                'institution_id': m.institution.id,
                'is_active': m.is_active,
            }
            for m in memberships
        ]
        
        # Obtener roles
        from api.models import UserRole
        user_roles = UserRole.objects.filter(user=user, is_active=True).select_related('role', 'institution')
        debug_info['roles'] = [
            {
                'role': ur.role.name,
                'institution': ur.institution.name,
                'permissions_in_role': ur.role.permissions.count(),
            }
            for ur in user_roles
        ]
        
        return Response(debug_info, status=status.HTTP_200_OK)
