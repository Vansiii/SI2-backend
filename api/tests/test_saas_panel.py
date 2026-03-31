"""
Tests para el panel de administración SaaS.

Verifica que:
- Solo superadmins SaaS pueden acceder a los endpoints
- Los endpoints retornan datos correctos
- Las estadísticas se calculan correctamente
- Se puede activar/desactivar instituciones
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from api.models import (
    FinancialInstitution,
    FinancialInstitutionMembership,
    UserProfile,
    Role,
    UserRole
)

User = get_user_model()


class SaaSPanelTestCase(TestCase):
    """Tests para endpoints del panel SaaS."""
    
    def setUp(self):
        """Configuración inicial para cada test."""
        self.client = APIClient()
        
        # Crear superadmin SaaS
        self.saas_admin = User.objects.create_user(
            username='saas@admin.com',
            email='saas@admin.com',
            password='testpass123',
            first_name='SaaS',
            last_name='Admin'
        )
        # El perfil se crea automáticamente por signal, solo actualizamos el tipo
        self.saas_admin.profile.user_type = 'saas_admin'
        self.saas_admin.profile.save()
        
        # Crear usuario normal
        self.normal_user = User.objects.create_user(
            username='user@test.com',
            email='user@test.com',
            password='testpass123',
            first_name='Normal',
            last_name='User'
        )
        # El perfil se crea automáticamente por signal
        
        # Crear instituciones de prueba
        self.inst1 = FinancialInstitution.objects.create(
            name='Banco Alpha',
            slug='banco-alpha',
            institution_type='banking',
            is_active=True
        )
        
        self.inst2 = FinancialInstitution.objects.create(
            name='Microfinanzas Beta',
            slug='micro-beta',
            institution_type='microfinance',
            is_active=True
        )
        
        self.inst3 = FinancialInstitution.objects.create(
            name='Cooperativa Gamma',
            slug='coop-gamma',
            institution_type='cooperative',
            is_active=False
        )
        
        # Crear membresía para usuario normal
        FinancialInstitutionMembership.objects.create(
            user=self.normal_user,
            institution=self.inst1,
            is_active=True
        )
        
        # Crear algunos roles
        self.role1 = Role.objects.create(
            institution=self.inst1,
            name='Admin',
            is_active=True
        )
        self.role2 = Role.objects.create(
            institution=self.inst1,
            name='Analyst',
            is_active=True
        )
        self.role3 = Role.objects.create(
            institution=self.inst2,
            name='Admin',
            is_active=True
        )
        
        # Asignar rol al usuario normal
        UserRole.objects.create(
            user=self.normal_user,
            role=self.role1,
            institution=self.inst1,
            is_active=True
        )
    
    def test_tenant_list_requires_authentication(self):
        """Test que el endpoint requiere autenticación."""
        response = self.client.get('/api/saas/tenants/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_tenant_list_requires_saas_admin(self):
        """Test que solo SaaS admin puede acceder."""
        self.client.force_authenticate(user=self.normal_user)
        response = self.client.get('/api/saas/tenants/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
    
    def test_tenant_list_success(self):
        """Test que SaaS admin puede listar instituciones."""
        self.client.force_authenticate(user=self.saas_admin)
        response = self.client.get('/api/saas/tenants/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        
        # Verificar que incluye datos básicos
        tenant_names = [t['name'] for t in response.data]
        self.assertIn('Banco Alpha', tenant_names)
        self.assertIn('Microfinanzas Beta', tenant_names)
        self.assertIn('Cooperativa Gamma', tenant_names)
    
    def test_tenant_list_filter_by_active(self):
        """Test filtrar instituciones por estado activo."""
        self.client.force_authenticate(user=self.saas_admin)
        
        # Filtrar solo activas
        response = self.client.get('/api/saas/tenants/?is_active=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        # Filtrar solo inactivas
        response = self.client.get('/api/saas/tenants/?is_active=false')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Cooperativa Gamma')
    
    def test_tenant_list_filter_by_type(self):
        """Test filtrar instituciones por tipo."""
        self.client.force_authenticate(user=self.saas_admin)
        
        response = self.client.get('/api/saas/tenants/?institution_type=banking')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Banco Alpha')
    
    def test_tenant_list_search(self):
        """Test buscar instituciones por nombre o slug."""
        self.client.force_authenticate(user=self.saas_admin)
        
        response = self.client.get('/api/saas/tenants/?search=alpha')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Banco Alpha')
    
    def test_tenant_detail_requires_saas_admin(self):
        """Test que solo SaaS admin puede ver detalles."""
        self.client.force_authenticate(user=self.normal_user)
        response = self.client.get(f'/api/saas/tenants/{self.inst1.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_tenant_detail_success(self):
        """Test que SaaS admin puede ver detalles de institución."""
        self.client.force_authenticate(user=self.saas_admin)
        response = self.client.get(f'/api/saas/tenants/{self.inst1.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Banco Alpha')
        self.assertEqual(response.data['slug'], 'banco-alpha')
        
        # Verificar que incluye estadísticas
        self.assertIn('stats', response.data)
        stats = response.data['stats']
        self.assertIn('total_users', stats)
        self.assertIn('total_roles', stats)
        self.assertIn('users_with_roles', stats)
        
        # Verificar estadísticas correctas
        self.assertEqual(stats['total_users'], 1)  # normal_user
        self.assertEqual(stats['total_roles'], 2)  # role1 y role2
        self.assertEqual(stats['users_with_roles'], 1)
    
    def test_tenant_detail_not_found(self):
        """Test que retorna 404 para institución inexistente."""
        self.client.force_authenticate(user=self.saas_admin)
        response = self.client.get('/api/saas/tenants/99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_tenant_stats_requires_saas_admin(self):
        """Test que solo SaaS admin puede ver estadísticas globales."""
        self.client.force_authenticate(user=self.normal_user)
        response = self.client.get('/api/saas/stats/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_tenant_stats_success(self):
        """Test que SaaS admin puede ver estadísticas globales."""
        self.client.force_authenticate(user=self.saas_admin)
        response = self.client.get('/api/saas/stats/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar estructura de datos
        self.assertIn('total_institutions', response.data)
        self.assertIn('active_institutions', response.data)
        self.assertIn('inactive_institutions', response.data)
        self.assertIn('total_users', response.data)
        self.assertIn('total_roles', response.data)
        self.assertIn('institutions_by_type', response.data)
        
        # Verificar valores correctos
        self.assertEqual(response.data['total_institutions'], 3)
        self.assertEqual(response.data['active_institutions'], 2)
        self.assertEqual(response.data['inactive_institutions'], 1)
        self.assertEqual(response.data['total_users'], 1)  # normal_user
        self.assertEqual(response.data['total_roles'], 3)  # 3 roles creados
        
        # Verificar distribución por tipo
        by_type = response.data['institutions_by_type']
        self.assertEqual(by_type.get('banking', 0), 1)
        self.assertEqual(by_type.get('microfinance', 0), 1)
        self.assertEqual(by_type.get('cooperative', 0), 1)
    
    def test_toggle_tenant_active_requires_saas_admin(self):
        """Test que solo SaaS admin puede activar/desactivar."""
        self.client.force_authenticate(user=self.normal_user)
        response = self.client.patch(
            f'/api/saas/tenants/{self.inst1.id}/toggle-active/',
            {'is_active': False}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_toggle_tenant_active_success(self):
        """Test que SaaS admin puede activar/desactivar institución."""
        self.client.force_authenticate(user=self.saas_admin)
        
        # Desactivar institución activa
        response = self.client.patch(
            f'/api/saas/tenants/{self.inst1.id}/toggle-active/',
            {'is_active': False},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertIn('institution', response.data)
        self.assertEqual(response.data['institution']['is_active'], False)
        
        # Verificar en base de datos
        self.inst1.refresh_from_db()
        self.assertFalse(self.inst1.is_active)
        
        # Activar institución inactiva
        response = self.client.patch(
            f'/api/saas/tenants/{self.inst3.id}/toggle-active/',
            {'is_active': True},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['institution']['is_active'], True)
        
        # Verificar en base de datos
        self.inst3.refresh_from_db()
        self.assertTrue(self.inst3.is_active)
    
    def test_toggle_tenant_active_missing_field(self):
        """Test que requiere el campo is_active."""
        self.client.force_authenticate(user=self.saas_admin)
        response = self.client.patch(
            f'/api/saas/tenants/{self.inst1.id}/toggle-active/',
            {},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_user_without_profile_cannot_access(self):
        """Test que usuario sin perfil no puede acceder."""
        # Crear usuario sin perfil
        user_no_profile = User.objects.create_user(
            username='noprofile@test.com',
            email='noprofile@test.com',
            password='testpass123'
        )
        # Eliminar perfil si se creó automáticamente
        if hasattr(user_no_profile, 'profile'):
            user_no_profile.profile.delete()
        
        self.client.force_authenticate(user=user_no_profile)
        response = self.client.get('/api/saas/tenants/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_tenant_detail_includes_recent_users(self):
        """Test que detalles incluyen usuarios recientes."""
        # Crear más usuarios
        user2 = User.objects.create_user(
            username='user2@test.com',
            email='user2@test.com',
            password='testpass123',
            first_name='User',
            last_name='Two'
        )
        # El perfil se crea automáticamente por signal
        FinancialInstitutionMembership.objects.create(
            user=user2,
            institution=self.inst1,
            is_active=True
        )
        
        self.client.force_authenticate(user=self.saas_admin)
        response = self.client.get(f'/api/saas/tenants/{self.inst1.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('recent_users', response.data)
        self.assertGreaterEqual(len(response.data['recent_users']), 1)
        
        # Verificar estructura de usuarios recientes
        if len(response.data['recent_users']) > 0:
            user_data = response.data['recent_users'][0]
            self.assertIn('id', user_data)
            self.assertIn('email', user_data)
            self.assertIn('full_name', user_data)
            self.assertIn('joined_at', user_data)


class SaaSPanelSecurityTestCase(TestCase):
    """Tests de seguridad para el panel SaaS."""
    
    def setUp(self):
        """Configuración inicial."""
        self.client = APIClient()
        
        # Crear dos instituciones
        self.inst1 = FinancialInstitution.objects.create(
            name='Institution 1',
            slug='inst1',
            institution_type='banking',
            is_active=True
        )
        self.inst2 = FinancialInstitution.objects.create(
            name='Institution 2',
            slug='inst2',
            institution_type='microfinance',
            is_active=True
        )
        
        # Crear usuario de inst1
        self.user1 = User.objects.create_user(
            username='user1@inst1.com',
            email='user1@inst1.com',
            password='testpass123'
        )
        # El perfil se crea automáticamente por signal
        FinancialInstitutionMembership.objects.create(
            user=self.user1,
            institution=self.inst1,
            is_active=True
        )
        
        # Crear superadmin
        self.saas_admin = User.objects.create_user(
            username='saas@admin.com',
            email='saas@admin.com',
            password='testpass123'
        )
        # El perfil se crea automáticamente por signal, solo actualizamos el tipo
        self.saas_admin.profile.user_type = 'saas_admin'
        self.saas_admin.profile.save()
    
    def test_tenant_user_cannot_see_other_institutions(self):
        """Test que usuario de tenant no puede ver otras instituciones."""
        self.client.force_authenticate(user=self.user1)
        
        # Intentar acceder a lista de instituciones
        response = self.client.get('/api/saas/tenants/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Intentar acceder a detalles de otra institución
        response = self.client.get(f'/api/saas/tenants/{self.inst2.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_saas_admin_can_see_all_institutions(self):
        """Test que SaaS admin puede ver todas las instituciones."""
        self.client.force_authenticate(user=self.saas_admin)
        
        response = self.client.get('/api/saas/tenants/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        # Puede ver detalles de cualquier institución
        response = self.client.get(f'/api/saas/tenants/{self.inst1.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response = self.client.get(f'/api/saas/tenants/{self.inst2.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_tenant_user_cannot_toggle_institution_status(self):
        """Test que usuario normal no puede activar/desactivar instituciones."""
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.patch(
            f'/api/saas/tenants/{self.inst1.id}/toggle-active/',
            {'is_active': False},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Verificar que no se modificó
        self.inst1.refresh_from_db()
        self.assertTrue(self.inst1.is_active)
