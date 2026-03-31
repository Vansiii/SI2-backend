"""
Tests para la gestión de permisos globales (Panel SaaS).
Sprint 8: Gestión de Permisos y Vistas Multi-Tenant
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from api.models import (
    Permission,
    Role,
    UserRole,
    FinancialInstitution,
    FinancialInstitutionMembership,
    UserProfile
)

User = get_user_model()


class PermissionManagementTestCase(TestCase):
    """Tests para gestión de permisos globales (solo SaaS Admin)."""
    
    def setUp(self):
        """Configuración inicial para los tests."""
        self.client = APIClient()
        
        # Crear SaaS Admin
        self.saas_admin = User.objects.create_user(
            username='saas@admin.com',
            email='saas@admin.com',
            password='admin123',
            first_name='SaaS',
            last_name='Admin'
        )
        # Actualizar el perfil creado automáticamente por el signal
        profile = UserProfile.objects.get(user=self.saas_admin)
        profile.user_type = 'saas_admin'
        profile.save()
        # Refrescar el usuario para que tenga el perfil actualizado
        self.saas_admin.refresh_from_db()
        
        # Crear institución y usuario tenant
        self.institution = FinancialInstitution.objects.create(
            name='Banco Test',
            slug='banco-test',
            institution_type='commercial_bank',
            created_by=self.saas_admin
        )
        
        self.tenant_user = User.objects.create_user(
            username='tenant@test.com',
            email='tenant@test.com',
            password='tenant123',
            first_name='Tenant',
            last_name='User'
        )
        # Actualizar el perfil creado automáticamente por el signal
        profile = UserProfile.objects.get(user=self.tenant_user)
        profile.user_type = 'tenant_user'
        profile.save()
        
        FinancialInstitutionMembership.objects.create(
            user=self.tenant_user,
            institution=self.institution
        )
        
        # Crear algunos permisos de prueba
        self.permission1 = Permission.objects.create(
            code='test.view',
            name='Ver Test',
            description='Permiso de prueba',
            is_active=True
        )
        self.permission2 = Permission.objects.create(
            code='test.create',
            name='Crear Test',
            description='Permiso de prueba',
            is_active=True
        )
        
        # Crear rol de administrador
        self.admin_role = Role.objects.create(
            institution=self.institution,
            name='Administrador de Institución',
            description='Admin',
            is_active=True
        )
        self.admin_role.permissions.add(self.permission1)
    
    def test_list_permissions_as_saas_admin(self):
        """SaaS Admin puede listar todos los permisos."""
        self.client.force_authenticate(user=self.saas_admin)
        
        response = self.client.get('/api/saas/permissions/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)
    
    def test_list_permissions_as_tenant_user_forbidden(self):
        """Usuario tenant NO puede listar permisos del panel SaaS."""
        self.client.force_authenticate(user=self.tenant_user)
        
        response = self.client.get('/api/saas/permissions/')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_create_permission_as_saas_admin(self):
        """SaaS Admin puede crear permisos."""
        self.client.force_authenticate(user=self.saas_admin)
        
        data = {
            'code': 'invoices.export',
            'name': 'Exportar Facturas',
            'description': 'Permite exportar facturas',
            'auto_assign_to_admins': False  # No auto-asignar en test
        }
        
        response = self.client.post('/api/saas/permissions/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['permission']['code'], 'invoices.export')
        self.assertFalse(response.data['auto_assigned'])
        
        # Verificar que se creó en la BD
        self.assertTrue(Permission.objects.filter(code='invoices.export').exists())
    
    def test_create_permission_with_auto_assign(self):
        """Crear permiso con auto-asignación a roles de administrador."""
        self.client.force_authenticate(user=self.saas_admin)
        
        # Verificar permisos actuales del rol
        initial_count = self.admin_role.permissions.count()
        
        data = {
            'code': 'auto.assigned',
            'name': 'Auto Asignado',
            'description': 'Test auto-asignación',
            'auto_assign_to_admins': True
        }
        
        response = self.client.post('/api/saas/permissions/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['auto_assigned'])
        
        # Verificar que se asignó al rol de administrador
        self.admin_role.refresh_from_db()
        self.assertEqual(self.admin_role.permissions.count(), initial_count + 1)
        self.assertTrue(
            self.admin_role.permissions.filter(code='auto.assigned').exists()
        )
    
    def test_create_duplicate_permission_fails(self):
        """No se puede crear permiso con código duplicado."""
        self.client.force_authenticate(user=self.saas_admin)
        
        data = {
            'code': 'test.view',  # Ya existe
            'name': 'Duplicado',
            'description': 'Test',
            'auto_assign_to_admins': False
        }
        
        response = self.client.post('/api/saas/permissions/', data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_update_permission(self):
        """SaaS Admin puede actualizar permisos."""
        self.client.force_authenticate(user=self.saas_admin)
        
        data = {
            'name': 'Ver Test Actualizado',
            'description': 'Descripción actualizada'
        }
        
        response = self.client.patch(
            f'/api/saas/permissions/{self.permission1.id}/',
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['permission']['name'], 'Ver Test Actualizado')
        
        # Verificar en BD
        self.permission1.refresh_from_db()
        self.assertEqual(self.permission1.name, 'Ver Test Actualizado')
    
    def test_delete_permission_deactivates(self):
        """Eliminar permiso lo desactiva (no lo borra)."""
        self.client.force_authenticate(user=self.saas_admin)
        
        response = self.client.delete(f'/api/saas/permissions/{self.permission2.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar que se desactivó
        self.permission2.refresh_from_db()
        self.assertFalse(self.permission2.is_active)
    
    def test_sync_permissions(self):
        """Sincronizar permisos con roles de administrador."""
        self.client.force_authenticate(user=self.saas_admin)
        
        # Crear nuevo permiso sin auto-asignar
        new_perm = Permission.objects.create(
            code='sync.test',
            name='Sync Test',
            is_active=True
        )
        
        # Verificar que el rol no lo tiene
        self.assertFalse(
            self.admin_role.permissions.filter(id=new_perm.id).exists()
        )
        
        # Sincronizar
        response = self.client.post('/api/saas/permissions/sync/', {'dry_run': False})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        
        # Verificar que ahora el rol lo tiene
        self.admin_role.refresh_from_db()
        self.assertTrue(
            self.admin_role.permissions.filter(id=new_perm.id).exists()
        )
    
    def test_coverage_report(self):
        """Obtener reporte de cobertura de permisos."""
        self.client.force_authenticate(user=self.saas_admin)
        
        response = self.client.get('/api/saas/permissions/coverage/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_permissions', response.data)
        self.assertIn('tenants', response.data)
        self.assertIsInstance(response.data['tenants'], list)
    
    def test_filter_permissions_by_search(self):
        """Filtrar permisos por búsqueda."""
        self.client.force_authenticate(user=self.saas_admin)
        
        response = self.client.get('/api/saas/permissions/?search=view')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Debe encontrar al menos test.view
        codes = [p['code'] for p in response.data]
        self.assertIn('test.view', codes)
    
    def test_filter_permissions_by_active(self):
        """Filtrar permisos por estado activo."""
        self.client.force_authenticate(user=self.saas_admin)
        
        # Desactivar un permiso
        self.permission2.is_active = False
        self.permission2.save()
        
        # Filtrar solo activos
        response = self.client.get('/api/saas/permissions/?is_active=true')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        codes = [p['code'] for p in response.data]
        self.assertIn('test.view', codes)
        self.assertNotIn('test.create', codes)


class SaaSMultiTenantViewsTestCase(TestCase):
    """Tests para vistas multi-tenant del panel SaaS."""
    
    def setUp(self):
        """Configuración inicial."""
        self.client = APIClient()
        
        # Crear SaaS Admin
        self.saas_admin = User.objects.create_user(
            username='saas@admin.com',
            email='saas@admin.com',
            password='admin123'
        )
        # Actualizar el perfil creado automáticamente por el signal
        profile = UserProfile.objects.get(user=self.saas_admin)
        profile.user_type = 'saas_admin'
        profile.save()
        # Refrescar el usuario para que tenga el perfil actualizado
        self.saas_admin.refresh_from_db()
        
        # Crear dos instituciones
        self.inst1 = FinancialInstitution.objects.create(
            name='Banco A',
            slug='banco-a',
            institution_type='commercial_bank',
            created_by=self.saas_admin
        )
        self.inst2 = FinancialInstitution.objects.create(
            name='Banco B',
            slug='banco-b',
            institution_type='fintech',
            created_by=self.saas_admin
        )
        
        # Crear usuarios en cada institución
        self.user1 = User.objects.create_user(
            username='user1@bancoa.com',
            email='user1@bancoa.com',
            password='pass123',
            first_name='Usuario',
            last_name='Uno'
        )
        # Actualizar el perfil creado automáticamente por el signal
        profile = UserProfile.objects.get(user=self.user1)
        profile.user_type = 'tenant_user'
        profile.save()
        
        FinancialInstitutionMembership.objects.create(
            user=self.user1,
            institution=self.inst1
        )
        
        self.user2 = User.objects.create_user(
            username='user2@bancob.com',
            email='user2@bancob.com',
            password='pass123',
            first_name='Usuario',
            last_name='Dos'
        )
        # Actualizar el perfil creado automáticamente por el signal
        profile = UserProfile.objects.get(user=self.user2)
        profile.user_type = 'tenant_user'
        profile.save()
        
        FinancialInstitutionMembership.objects.create(
            user=self.user2,
            institution=self.inst2
        )
        
        # Crear roles
        self.role1 = Role.objects.create(
            institution=self.inst1,
            name='Admin A',
            is_active=True
        )
        self.role2 = Role.objects.create(
            institution=self.inst2,
            name='Admin B',
            is_active=True
        )
    
    def test_list_all_users_as_saas_admin(self):
        """SaaS Admin puede ver usuarios de todos los tenants."""
        self.client.force_authenticate(user=self.saas_admin)
        
        response = self.client.get('/api/saas/users/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)
    
    def test_filter_users_by_tenant_id(self):
        """Filtrar usuarios por ID de tenant."""
        self.client.force_authenticate(user=self.saas_admin)
        
        response = self.client.get(f'/api/saas/users/?tenant_id={self.inst1.id}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emails = [u['email'] for u in response.data]
        self.assertIn('user1@bancoa.com', emails)
        self.assertNotIn('user2@bancob.com', emails)
    
    def test_filter_users_by_tenant_slug(self):
        """Filtrar usuarios por slug de tenant."""
        self.client.force_authenticate(user=self.saas_admin)
        
        response = self.client.get('/api/saas/users/?tenant_slug=banco-b')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emails = [u['email'] for u in response.data]
        self.assertIn('user2@bancob.com', emails)
        self.assertNotIn('user1@bancoa.com', emails)
    
    def test_search_users(self):
        """Buscar usuarios por email o nombre."""
        self.client.force_authenticate(user=self.saas_admin)
        
        response = self.client.get('/api/saas/users/?search=Uno')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['last_name'], 'Uno')
    
    def test_list_all_roles_as_saas_admin(self):
        """SaaS Admin puede ver roles de todos los tenants."""
        self.client.force_authenticate(user=self.saas_admin)
        
        response = self.client.get('/api/saas/roles/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)
    
    def test_filter_roles_by_tenant(self):
        """Filtrar roles por tenant."""
        self.client.force_authenticate(user=self.saas_admin)
        
        response = self.client.get(f'/api/saas/roles/?tenant_id={self.inst1.id}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [r['name'] for r in response.data]
        self.assertIn('Admin A', names)
        self.assertNotIn('Admin B', names)
    
    def test_tenant_user_cannot_access_saas_views(self):
        """Usuario tenant NO puede acceder a vistas SaaS."""
        self.client.force_authenticate(user=self.user1)
        
        response_users = self.client.get('/api/saas/users/')
        response_roles = self.client.get('/api/saas/roles/')
        
        self.assertEqual(response_users.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response_roles.status_code, status.HTTP_403_FORBIDDEN)


class RolePermissionAssignmentTestCase(TestCase):
    """Tests para asignación de permisos a roles (Panel Tenant)."""
    
    def setUp(self):
        """Configuración inicial."""
        self.client = APIClient()
        
        # Crear institución
        self.institution = FinancialInstitution.objects.create(
            name='Banco Test',
            slug='banco-test',
            institution_type='commercial_bank'
        )
        
        # Crear usuario admin del tenant
        self.admin_user = User.objects.create_user(
            username='admin@test.com',
            email='admin@test.com',
            password='admin123'
        )
        # Actualizar el perfil creado automáticamente por el signal
        profile = UserProfile.objects.get(user=self.admin_user)
        profile.user_type = 'tenant_user'
        profile.save()
        
        FinancialInstitutionMembership.objects.create(
            user=self.admin_user,
            institution=self.institution
        )
        
        # Crear permisos
        self.perm1 = Permission.objects.create(code='p1', name='P1', is_active=True)
        self.perm2 = Permission.objects.create(code='p2', name='P2', is_active=True)
        self.perm3 = Permission.objects.create(code='p3', name='P3', is_active=True)
        
        # Crear rol con permiso para asignar permisos
        self.admin_role = Role.objects.create(
            institution=self.institution,
            name='Admin',
            is_active=True
        )
        assign_perm = Permission.objects.create(
            code='roles.assign_permissions',
            name='Asignar Permisos',
            is_active=True
        )
        self.admin_role.permissions.add(assign_perm)
        
        # Asignar rol al usuario
        UserRole.objects.create(
            user=self.admin_user,
            role=self.admin_role,
            institution=self.institution,
            assigned_by=self.admin_user,
            is_active=True
        )
        
        # Crear rol de prueba
        self.test_role = Role.objects.create(
            institution=self.institution,
            name='Test Role',
            is_active=True
        )
    
    def test_list_available_permissions(self):
        """Listar permisos disponibles para asignar."""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get('/api/permissions/available/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 3)
    
    def test_list_role_permissions(self):
        """Listar permisos de un rol específico."""
        self.client.force_authenticate(user=self.admin_user)
        self.test_role.permissions.add(self.perm1)
        
        response = self.client.get(f'/api/roles/{self.test_role.id}/permissions/list/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('role', response.data)
        self.assertIn('permissions', response.data)
        self.assertEqual(len(response.data['permissions']), 1)
    
    def test_assign_permissions_to_role(self):
        """Asignar permisos a un rol."""
        self.client.force_authenticate(user=self.admin_user)
        
        data = {
            'permission_ids': [self.perm1.id, self.perm2.id, self.perm3.id]
        }
        
        response = self.client.post(
            f'/api/roles/{self.test_role.id}/permissions/assign/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['role']['permissions_count'], 3)
        
        # Verificar en BD
        self.test_role.refresh_from_db()
        self.assertEqual(self.test_role.permissions.count(), 3)
    
    def test_assign_invalid_permission_fails(self):
        """Asignar permiso inválido falla."""
        self.client.force_authenticate(user=self.admin_user)
        
        data = {
            'permission_ids': [9999]  # ID que no existe
        }
        
        response = self.client.post(
            f'/api/roles/{self.test_role.id}/permissions/assign/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_available_permissions_with_role_context(self):
        """Listar permisos disponibles marcando los asignados a un rol."""
        self.client.force_authenticate(user=self.admin_user)
        self.test_role.permissions.add(self.perm1)
        
        response = self.client.get(
            f'/api/permissions/available/?role_id={self.test_role.id}'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Buscar perm1 en la respuesta
        perm1_data = next(p for p in response.data if p['id'] == self.perm1.id)
        self.assertTrue(perm1_data['is_assigned'])
        
        # perm2 no debe estar asignado
        perm2_data = next(p for p in response.data if p['id'] == self.perm2.id)
        self.assertFalse(perm2_data['is_assigned'])
