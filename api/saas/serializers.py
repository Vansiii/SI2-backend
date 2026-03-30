"""
Serializers para el panel de administración SaaS.

Estos serializers son usados por los endpoints de gestión de tenants
disponibles solo para superadmins SaaS.
"""

from rest_framework import serializers
from api.models import FinancialInstitution, Role, UserRole
from django.contrib.auth import get_user_model

User = get_user_model()


class InstitutionListSerializer(serializers.ModelSerializer):
    """Serializer para lista de instituciones."""
    
    users_count = serializers.SerializerMethodField()
    roles_count = serializers.SerializerMethodField()
    active_users_count = serializers.SerializerMethodField()
    
    class Meta:
        model = FinancialInstitution
        fields = [
            'id',
            'name',
            'slug',
            'institution_type',
            'is_active',
            'created_at',
            'users_count',
            'roles_count',
            'active_users_count',
        ]
    
    def get_users_count(self, obj):
        """Cuenta total de usuarios de la institución."""
        return obj.memberships.filter(is_active=True).count()
    
    def get_roles_count(self, obj):
        """Cuenta total de roles de la institución."""
        return Role.all_objects.filter(institution=obj).count()
    
    def get_active_users_count(self, obj):
        """Cuenta de usuarios activos con roles asignados."""
        return UserRole.objects.filter(
            institution=obj,
            is_active=True
        ).values('user').distinct().count()


class InstitutionDetailSerializer(serializers.ModelSerializer):
    """Serializer detallado para una institución."""
    
    created_by = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()
    recent_users = serializers.SerializerMethodField()
    
    class Meta:
        model = FinancialInstitution
        fields = [
            'id',
            'name',
            'slug',
            'institution_type',
            'is_active',
            'created_at',
            'updated_at',
            'created_by',
            'stats',
            'recent_users',
        ]
    
    def get_created_by(self, obj):
        """Información del usuario que creó la institución."""
        if obj.created_by:
            return {
                'id': obj.created_by.id,
                'email': obj.created_by.email,
                'full_name': f'{obj.created_by.first_name} {obj.created_by.last_name}',
            }
        return None
    
    def get_stats(self, obj):
        """Estadísticas de la institución."""
        # Total de usuarios
        total_users = obj.memberships.filter(is_active=True).count()
        
        # Usuarios con roles asignados
        users_with_roles = UserRole.objects.filter(
            institution=obj,
            is_active=True
        ).values('user').distinct().count()
        
        # Total de roles
        total_roles = Role.all_objects.filter(institution=obj).count()
        
        # Roles activos
        active_roles = Role.all_objects.filter(
            institution=obj,
            is_active=True
        ).count()
        
        return {
            'total_users': total_users,
            'users_with_roles': users_with_roles,
            'users_without_roles': total_users - users_with_roles,
            'total_roles': total_roles,
            'active_roles': active_roles,
            'inactive_roles': total_roles - active_roles,
        }
    
    def get_recent_users(self, obj):
        """Últimos 5 usuarios registrados."""
        recent_memberships = obj.memberships.filter(
            is_active=True
        ).select_related('user').order_by('-created_at')[:5]
        
        return [
            {
                'id': m.user.id,
                'email': m.user.email,
                'full_name': f'{m.user.first_name} {m.user.last_name}',
                'joined_at': m.created_at,
            }
            for m in recent_memberships
        ]


class TenantStatsSerializer(serializers.Serializer):
    """Serializer para estadísticas globales de tenants."""
    
    total_institutions = serializers.IntegerField()
    active_institutions = serializers.IntegerField()
    inactive_institutions = serializers.IntegerField()
    total_users = serializers.IntegerField()
    total_roles = serializers.IntegerField()
    institutions_by_type = serializers.DictField()



# ============================================================
# SPRINT 8: Gestión de Permisos y Vistas Multi-Tenant
# ============================================================

from api.models import Permission


class PermissionSerializer(serializers.ModelSerializer):
    """Serializer para permisos globales."""
    
    assigned_roles_count = serializers.SerializerMethodField()
    module = serializers.SerializerMethodField()
    
    class Meta:
        model = Permission
        fields = [
            'id', 'code', 'name', 'description', 'module', 'is_active',
            'created_at', 'updated_at', 'assigned_roles_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_assigned_roles_count(self, obj):
        """Cuenta cuántos roles tienen este permiso."""
        return obj.roles.filter(is_active=True).count()
    
    def get_module(self, obj):
        """Extrae el módulo del código del permiso (ej: 'users.view' -> 'users')."""
        if '.' in obj.code:
            return obj.code.split('.')[0]
        return 'general'


class SaaSUserListSerializer(serializers.ModelSerializer):
    """Serializer para listar usuarios en panel SaaS."""
    
    institution_name = serializers.SerializerMethodField()
    institution_slug = serializers.SerializerMethodField()
    roles_count = serializers.SerializerMethodField()
    user_type = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'is_active', 'date_joined', 'last_login',
            'institution_name', 'institution_slug',
            'roles_count', 'user_type'
        ]
    
    def get_full_name(self, obj):
        """Obtiene el nombre completo del usuario."""
        return f'{obj.first_name} {obj.last_name}'.strip()
    
    def get_institution_name(self, obj):
        """Obtiene el nombre de la institución principal del usuario."""
        membership = obj.institution_memberships.filter(is_active=True).first()
        return membership.institution.name if membership else None
    
    def get_institution_slug(self, obj):
        """Obtiene el slug de la institución principal del usuario."""
        membership = obj.institution_memberships.filter(is_active=True).first()
        return membership.institution.slug if membership else None
    
    def get_roles_count(self, obj):
        """Cuenta los roles activos del usuario."""
        return obj.user_roles.filter(is_active=True).count()
    
    def get_user_type(self, obj):
        """Obtiene el tipo de usuario."""
        if hasattr(obj, 'profile'):
            return obj.profile.user_type
        return None


class SaaSRoleListSerializer(serializers.ModelSerializer):
    """Serializer para listar roles en panel SaaS."""
    
    institution_name = serializers.CharField(source='institution.name', read_only=True)
    institution_slug = serializers.CharField(source='institution.slug', read_only=True)
    permissions_count = serializers.SerializerMethodField()
    users_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Role
        fields = [
            'id', 'name', 'description', 'is_active',
            'institution_name', 'institution_slug',
            'permissions_count', 'users_count',
            'created_at', 'updated_at'
        ]
    
    def get_permissions_count(self, obj):
        """Cuenta los permisos del rol."""
        return obj.permissions.filter(is_active=True).count()
    
    def get_users_count(self, obj):
        """Cuenta los usuarios con este rol."""
        return obj.user_assignments.filter(is_active=True).count()
