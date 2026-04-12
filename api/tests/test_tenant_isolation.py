"""
Tests de aislamiento multi-tenant.

Verifica que el TenantManager filtra correctamente los queries
y que no hay fugas de datos entre tenants.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from api.models import (
    FinancialInstitution,
    Role,
    Permission,
    UserProfile,
    UserRole
)
from api.core.managers import set_current_tenant, clear_current_tenant, get_current_tenant

User = get_user_model()


class TenantManagerTestCase(TestCase):
    """Tests del TenantManager y aislamiento por tenant."""
    
    def setUp(self):
        """Configurar datos de prueba."""
        # Crear dos instituciones
        self.institution1 = FinancialInstitution.objects.create(
            name='Banco Alpha',
            slug='banco-alpha',
            institution_type='banking'
        )
        
        self.institution2 = FinancialInstitution.objects.create(
            name='Banco Beta',
            slug='banco-beta',
            institution_type='banking'
        )
        
        # Crear permisos
        self.permission1 = Permission.objects.create(
            code='test.permission1',
            name='Test Permission 1'
        )
        
        self.permission2 = Permission.objects.create(
            code='test.permission2',
            name='Test Permission 2'
        )
        
        # Crear roles para cada institución
        self.role1_inst1 = Role.all_objects.create(
            institution=self.institution1,
            name='Admin',
            description='Administrador de Banco Alpha'
        )
        self.role1_inst1.permissions.add(self.permission1)
        
        self.role2_inst1 = Role.all_objects.create(
            institution=self.institution1,
            name='Analyst',
            description='Analista de Banco Alpha'
        )
        
        self.role1_inst2 = Role.all_objects.create(
            institution=self.institution2,
            name='Admin',
            description='Administrador de Banco Beta'
        )
        self.role1_inst2.permissions.add(self.permission2)
        
        self.role2_inst2 = Role.all_objects.create(
            institution=self.institution2,
            name='Manager',
            description='Gerente de Banco Beta'
        )
        
        # Limpiar tenant al inicio
        clear_current_tenant()
    
    def tearDown(self):
        """Limpiar tenant después de cada test."""
        clear_current_tenant()
    
    def test_tenant_manager_filters_by_current_tenant(self):
        """Verifica que TenantManager filtra por el tenant actual."""
        # Sin tenant establecido - debe retornar todos
        roles = Role.objects.all()
        self.assertEqual(roles.count(), 4)
        
        # Establecer tenant 1
        set_current_tenant(self.institution1)
        roles = Role.objects.all()
        self.assertEqual(roles.count(), 2)
        self.assertTrue(all(r.institution == self.institution1 for r in roles))
        
        # Establecer tenant 2
        set_current_tenant(self.institution2)
        roles = Role.objects.all()
        self.assertEqual(roles.count(), 2)
        self.assertTrue(all(r.institution == self.institution2 for r in roles))
    
    def test_all_objects_manager_returns_all_tenants(self):
        """Verifica que all_objects retorna objetos de todos los tenants."""
        # Establecer tenant 1
        set_current_tenant(self.institution1)
        
        # objects debe filtrar
        roles_filtered = Role.objects.all()
        self.assertEqual(roles_filtered.count(), 2)
        
        # all_objects NO debe filtrar
        roles_all = Role.all_objects.all()
        self.assertEqual(roles_all.count(), 4)
    
    def test_tenant_manager_filters_get_queries(self):
        """Verifica que TenantManager filtra queries get()."""
        set_current_tenant(self.institution1)
        
        # Debe encontrar el rol de institution1
        role = Role.objects.get(name='Admin')
        self.assertEqual(role.institution, self.institution1)
        
        # No debe encontrar el rol de institution2
        with self.assertRaises(Role.DoesNotExist):
            Role.objects.get(name='Manager')
    
    def test_tenant_manager_filters_filter_queries(self):
        """Verifica que TenantManager filtra queries filter()."""
        set_current_tenant(self.institution1)
        
        # Filtrar por nombre
        roles = Role.objects.filter(name='Admin')
        self.assertEqual(roles.count(), 1)
        self.assertEqual(roles.first().institution, self.institution1)
    
    def test_tenant_manager_create_assigns_current_tenant(self):
        """Verifica que create() asigna automáticamente el tenant actual."""
        set_current_tenant(self.institution1)
        
        # Crear sin especificar institution
        role = Role.objects.create(
            name='New Role',
            description='Test role'
        )
        
        # Debe tener asignado el tenant actual
        self.assertEqual(role.institution, self.institution1)
    
    def test_no_data_leakage_between_tenants(self):
        """Verifica que no hay fuga de datos entre tenants."""
        # Establecer tenant 1
        set_current_tenant(self.institution1)
        roles_tenant1 = list(Role.objects.all())
        
        # Establecer tenant 2
        set_current_tenant(self.institution2)
        roles_tenant2 = list(Role.objects.all())
        
        # No debe haber intersección
        tenant1_ids = {r.id for r in roles_tenant1}
        tenant2_ids = {r.id for r in roles_tenant2}
        self.assertEqual(tenant1_ids & tenant2_ids, set())
    
    def test_superadmin_can_access_all_tenants(self):
        """Verifica que superadmin (sin tenant) puede acceder a todo."""
        # Sin tenant (superadmin)
        clear_current_tenant()
        
        roles = Role.objects.all()
        self.assertEqual(roles.count(), 4)
        
        # Debe poder acceder a roles de ambos tenants
        inst1_roles = [r for r in roles if r.institution == self.institution1]
        inst2_roles = [r for r in roles if r.institution == self.institution2]
        self.assertEqual(len(inst1_roles), 2)
        self.assertEqual(len(inst2_roles), 2)
    
    def test_get_current_tenant_returns_correct_tenant(self):
        """Verifica que get_current_tenant() retorna el tenant correcto."""
        # Sin tenant
        self.assertIsNone(get_current_tenant())
        
        # Con tenant 1
        set_current_tenant(self.institution1)
        self.assertEqual(get_current_tenant(), self.institution1)
        
        # Con tenant 2
        set_current_tenant(self.institution2)
        self.assertEqual(get_current_tenant(), self.institution2)
        
        # Limpiar
        clear_current_tenant()
        self.assertIsNone(get_current_tenant())
    
    def test_tenant_isolation_with_related_objects(self):
        """Verifica aislamiento con objetos relacionados (permisos)."""
        set_current_tenant(self.institution1)
        
        # Obtener rol de tenant 1
        role = Role.objects.get(name='Admin')
        
        # Verificar permisos
        permissions = role.permissions.all()
        self.assertEqual(permissions.count(), 1)
        self.assertEqual(permissions.first().code, 'test.permission1')
    
    def test_tenant_manager_with_complex_queries(self):
        """Verifica que TenantManager funciona con queries complejos."""
        set_current_tenant(self.institution1)
        
        # Query con filtros adicionales
        roles = Role.objects.filter(
            name__icontains='admin',
            is_active=True
        )
        self.assertEqual(roles.count(), 1)
        self.assertEqual(roles.first().institution, self.institution1)
        
        # Query con exclude
        roles = Role.objects.exclude(name='Admin')
        self.assertEqual(roles.count(), 1)
        self.assertEqual(roles.first().name, 'Analyst')
    
    def test_tenant_manager_with_ordering(self):
        """Verifica que TenantManager respeta el ordering."""
        set_current_tenant(self.institution1)
        
        roles = Role.objects.all().order_by('name')
        role_names = [r.name for r in roles]
        self.assertEqual(role_names, ['Admin', 'Analyst'])
    
    def test_tenant_manager_count_is_correct(self):
        """Verifica que count() retorna el número correcto."""
        set_current_tenant(self.institution1)
        self.assertEqual(Role.objects.count(), 2)
        
        set_current_tenant(self.institution2)
        self.assertEqual(Role.objects.count(), 2)
        
        clear_current_tenant()
        self.assertEqual(Role.objects.count(), 4)
