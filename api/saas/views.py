"""
Vistas para el panel de administración SaaS.

Estos endpoints están disponibles solo para superadmins SaaS
y permiten gestionar todas las instituciones de la plataforma.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db.models import Count, Q

from api.models import FinancialInstitution, Role, UserRole
from .serializers import (
    InstitutionListSerializer,
    InstitutionDetailSerializer,
    TenantStatsSerializer
)

User = get_user_model()


class SaaSAdminRequiredMixin:
    """Mixin que verifica que el usuario sea superadmin SaaS."""
    
    def check_saas_admin(self, request):
        """
        Verifica que el usuario sea superadmin SaaS.
        
        Returns:
            Response con error 403 si no es superadmin, None si es válido
        """
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Autenticación requerida'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not hasattr(request.user, 'profile'):
            return Response(
                {'error': 'Perfil de usuario no encontrado'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not request.user.profile.is_saas_admin():
            return Response(
                {'error': 'Acceso denegado. Solo superadmins SaaS pueden acceder.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return None


class TenantListAPIView(SaaSAdminRequiredMixin, APIView):
    """
    Vista para listar todas las instituciones (tenants).
    
    Solo accesible para superadmins SaaS.
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Lista todas las instituciones con estadísticas básicas.
        
        Query params:
            - is_active: Filtrar por estado (true/false)
            - institution_type: Filtrar por tipo
            - search: Buscar por nombre o slug
        
        Response (200 OK):
            [
                {
                    "id": 1,
                    "name": "Banco Alpha",
                    "slug": "banco-alpha",
                    "institution_type": "banking",
                    "is_active": true,
                    "created_at": "2026-03-30T10:00:00Z",
                    "users_count": 15,
                    "roles_count": 6,
                    "active_users_count": 12
                }
            ]
        """
        # Verificar que sea superadmin
        error_response = self.check_saas_admin(request)
        if error_response:
            return error_response
        
        # Obtener todas las instituciones
        institutions = FinancialInstitution.objects.all()
        
        # Filtros opcionales
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            is_active_bool = is_active.lower() == 'true'
            institutions = institutions.filter(is_active=is_active_bool)
        
        institution_type = request.query_params.get('institution_type')
        if institution_type:
            institutions = institutions.filter(institution_type=institution_type)
        
        search = request.query_params.get('search')
        if search:
            institutions = institutions.filter(
                Q(name__icontains=search) | Q(slug__icontains=search)
            )
        
        # Ordenar por fecha de creación (más recientes primero)
        institutions = institutions.order_by('-created_at')
        
        serializer = InstitutionListSerializer(institutions, many=True)
        return Response(serializer.data)


class TenantDetailAPIView(SaaSAdminRequiredMixin, APIView):
    """
    Vista para obtener detalles de una institución específica.
    
    Solo accesible para superadmins SaaS.
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, tenant_id: int):
        """
        Obtiene detalles completos de una institución.
        
        Response (200 OK):
            {
                "id": 1,
                "name": "Banco Alpha",
                "slug": "banco-alpha",
                "institution_type": "banking",
                "is_active": true,
                "created_at": "2026-03-30T10:00:00Z",
                "updated_at": "2026-03-30T12:00:00Z",
                "created_by": {
                    "id": 1,
                    "email": "admin@alpha.com",
                    "full_name": "Juan Pérez"
                },
                "stats": {
                    "total_users": 15,
                    "users_with_roles": 12,
                    "users_without_roles": 3,
                    "total_roles": 6,
                    "active_roles": 6,
                    "inactive_roles": 0
                },
                "recent_users": [...]
            }
        """
        # Verificar que sea superadmin
        error_response = self.check_saas_admin(request)
        if error_response:
            return error_response
        
        institution = get_object_or_404(FinancialInstitution, id=tenant_id)
        serializer = InstitutionDetailSerializer(institution)
        return Response(serializer.data)


class TenantStatsAPIView(SaaSAdminRequiredMixin, APIView):
    """
    Vista para obtener estadísticas globales de la plataforma.
    
    Solo accesible para superadmins SaaS.
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Obtiene estadísticas globales de todos los tenants.
        
        Response (200 OK):
            {
                "total_institutions": 10,
                "active_institutions": 8,
                "inactive_institutions": 2,
                "total_users": 150,
                "total_roles": 60,
                "institutions_by_type": {
                    "banking": 5,
                    "microfinance": 3,
                    "cooperative": 1,
                    "fintech": 1
                }
            }
        """
        # Verificar que sea superadmin
        error_response = self.check_saas_admin(request)
        if error_response:
            return error_response
        
        # Estadísticas de instituciones
        total_institutions = FinancialInstitution.objects.count()
        active_institutions = FinancialInstitution.objects.filter(is_active=True).count()
        inactive_institutions = total_institutions - active_institutions
        
        # Estadísticas de usuarios
        total_users = User.objects.filter(
            institution_memberships__is_active=True
        ).distinct().count()
        
        # Estadísticas de roles
        total_roles = Role.all_objects.count()
        
        # Instituciones por tipo
        institutions_by_type = {}
        type_counts = FinancialInstitution.objects.values('institution_type').annotate(
            count=Count('id')
        )
        for item in type_counts:
            institutions_by_type[item['institution_type']] = item['count']
        
        stats = {
            'total_institutions': total_institutions,
            'active_institutions': active_institutions,
            'inactive_institutions': inactive_institutions,
            'total_users': total_users,
            'total_roles': total_roles,
            'institutions_by_type': institutions_by_type,
        }
        
        serializer = TenantStatsSerializer(stats)
        return Response(serializer.data)


class TenantToggleActiveAPIView(SaaSAdminRequiredMixin, APIView):
    """
    Vista para activar/desactivar una institución.
    
    Solo accesible para superadmins SaaS.
    """
    
    permission_classes = [IsAuthenticated]
    
    def patch(self, request, tenant_id: int):
        """
        Activa o desactiva una institución.
        
        Request body:
            {
                "is_active": true
            }
        
        Response (200 OK):
            {
                "message": "Institución actualizada exitosamente",
                "institution": {
                    "id": 1,
                    "name": "Banco Alpha",
                    "is_active": true
                }
            }
        """
        # Verificar que sea superadmin
        error_response = self.check_saas_admin(request)
        if error_response:
            return error_response
        
        institution = get_object_or_404(FinancialInstitution, id=tenant_id)
        
        is_active = request.data.get('is_active')
        if is_active is None:
            return Response(
                {'error': 'El campo is_active es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        institution.is_active = is_active
        institution.save()
        
        return Response({
            'message': 'Institución actualizada exitosamente',
            'institution': {
                'id': institution.id,
                'name': institution.name,
                'is_active': institution.is_active,
            }
        })



# ============================================================
# SPRINT 8: Gestión de Permisos y Vistas Multi-Tenant
# ============================================================

from rest_framework import viewsets
from rest_framework.decorators import action
from django.db.models import Q

from api.models import Permission
from api.services.permission_service import PermissionService
from .serializers import (
    PermissionSerializer,
    SaaSUserListSerializer,
    SaaSRoleListSerializer
)


class PermissionManagementViewSet(SaaSAdminRequiredMixin, viewsets.ModelViewSet):
    """
    ViewSet para gestionar permisos globales (solo SaaS Admin).
    
    Endpoints:
        GET    /api/saas/permissions/          - Listar permisos
        POST   /api/saas/permissions/          - Crear permiso
        GET    /api/saas/permissions/{id}/     - Detalle de permiso
        PUT    /api/saas/permissions/{id}/     - Actualizar permiso
        PATCH  /api/saas/permissions/{id}/     - Actualizar parcial
        DELETE /api/saas/permissions/{id}/     - Desactivar permiso
        POST   /api/saas/permissions/sync/     - Sincronizar con admins
        GET    /api/saas/permissions/coverage/ - Reporte de cobertura
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = PermissionSerializer
    queryset = Permission.objects.all().order_by('code')
    
    def list(self, request):
        """Lista todos los permisos globales."""
        error_response = self.check_saas_admin(request)
        if error_response:
            return error_response
        
        queryset = self.get_queryset()
        
        # Filtros opcionales
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(code__icontains=search) |
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def create(self, request):
        """
        Crea un nuevo permiso global.
        
        Body:
        {
            "code": "invoices.export",
            "name": "Exportar Facturas",
            "description": "Permite exportar facturas a PDF",
            "auto_assign_to_admins": true
        }
        """
        error_response = self.check_saas_admin(request)
        if error_response:
            return error_response
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Obtener opción de auto-asignación
        auto_assign = request.data.get('auto_assign_to_admins', True)
        
        # Crear permiso usando el servicio
        service = PermissionService()
        try:
            permission = service.create_permission(
                code=serializer.validated_data['code'],
                name=serializer.validated_data['name'],
                description=serializer.validated_data.get('description', ''),
                auto_assign_to_admins=auto_assign
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        response_serializer = self.get_serializer(permission)
        return Response(
            {
                'message': 'Permiso creado exitosamente',
                'permission': response_serializer.data,
                'auto_assigned': auto_assign
            },
            status=status.HTTP_201_CREATED
        )
    
    def retrieve(self, request, pk=None):
        """Obtiene detalle de un permiso."""
        error_response = self.check_saas_admin(request)
        if error_response:
            return error_response
        
        permission = self.get_object()
        serializer = self.get_serializer(permission)
        return Response(serializer.data)
    
    def update(self, request, pk=None):
        """Actualiza un permiso existente."""
        error_response = self.check_saas_admin(request)
        if error_response:
            return error_response
        
        permission = self.get_object()
        serializer = self.get_serializer(permission, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'message': 'Permiso actualizado exitosamente',
            'permission': serializer.data
        })
    
    def partial_update(self, request, pk=None):
        """Actualiza parcialmente un permiso."""
        error_response = self.check_saas_admin(request)
        if error_response:
            return error_response
        
        permission = self.get_object()
        serializer = self.get_serializer(permission, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'message': 'Permiso actualizado exitosamente',
            'permission': serializer.data
        })
    
    def destroy(self, request, pk=None):
        """
        Desactiva un permiso (no lo elimina físicamente).
        """
        error_response = self.check_saas_admin(request)
        if error_response:
            return error_response
        
        permission = self.get_object()
        permission.is_active = False
        permission.save()
        
        return Response({
            'message': 'Permiso desactivado exitosamente'
        })
    
    @action(detail=False, methods=['post'])
    def sync(self, request):
        """
        Sincroniza todos los permisos con roles de administrador.
        
        Body (opcional):
        {
            "dry_run": false
        }
        """
        error_response = self.check_saas_admin(request)
        if error_response:
            return error_response
        
        dry_run = request.data.get('dry_run', False)
        
        service = PermissionService()
        results = service.sync_all_admin_permissions(dry_run=dry_run)
        
        return Response({
            'message': 'Sincronización completada' if not dry_run else 'Simulación completada',
            'results': results
        })
    
    @action(detail=False, methods=['get'])
    def coverage(self, request):
        """
        Obtiene reporte de cobertura de permisos por tenant.
        """
        error_response = self.check_saas_admin(request)
        if error_response:
            return error_response
        
        service = PermissionService()
        coverage = service.get_permission_coverage()
        
        return Response(coverage)


class SaaSUserListAPIView(SaaSAdminRequiredMixin, APIView):
    """
    Vista para listar usuarios de todos los tenants (Panel SaaS).
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Lista usuarios con filtros por tenant.
        
        Query params:
            - tenant_id: Filtrar por institución
            - tenant_slug: Filtrar por slug de institución
            - is_active: Filtrar por estado
            - user_type: Filtrar por tipo (saas_admin, tenant_user)
            - search: Buscar por email o nombre
        """
        error_response = self.check_saas_admin(request)
        if error_response:
            return error_response
        
        users = User.objects.all()
        
        # Filtro por tenant
        tenant_id = request.query_params.get('tenant_id')
        tenant_slug = request.query_params.get('tenant_slug')
        
        if tenant_id:
            users = users.filter(
                institution_memberships__institution_id=tenant_id,
                institution_memberships__is_active=True
            )
        elif tenant_slug:
            users = users.filter(
                institution_memberships__institution__slug=tenant_slug,
                institution_memberships__is_active=True
            )
        
        # Filtro por estado
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            users = users.filter(is_active=is_active.lower() == 'true')
        
        # Filtro por tipo de usuario
        user_type = request.query_params.get('user_type')
        if user_type:
            users = users.filter(profile__user_type=user_type)
        
        # Búsqueda
        search = request.query_params.get('search')
        if search:
            users = users.filter(
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        
        users = users.distinct().order_by('-date_joined')
        
        serializer = SaaSUserListSerializer(users, many=True)
        return Response(serializer.data)


class SaaSRoleListAPIView(SaaSAdminRequiredMixin, APIView):
    """
    Vista para listar roles de todos los tenants (Panel SaaS).
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Lista roles con filtros por tenant.
        
        Query params:
            - tenant_id: Filtrar por institución
            - tenant_slug: Filtrar por slug de institución
            - is_active: Filtrar por estado
            - search: Buscar por nombre
        """
        error_response = self.check_saas_admin(request)
        if error_response:
            return error_response
        
        roles = Role.all_objects.all()
        
        # Filtro por tenant
        tenant_id = request.query_params.get('tenant_id')
        tenant_slug = request.query_params.get('tenant_slug')
        
        if tenant_id:
            roles = roles.filter(institution_id=tenant_id)
        elif tenant_slug:
            roles = roles.filter(institution__slug=tenant_slug)
        
        # Filtro por estado
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            roles = roles.filter(is_active=is_active.lower() == 'true')
        
        # Búsqueda
        search = request.query_params.get('search')
        if search:
            roles = roles.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        
        roles = roles.order_by('institution__name', 'name')
        
        serializer = SaaSRoleListSerializer(roles, many=True)
        return Response(serializer.data)
