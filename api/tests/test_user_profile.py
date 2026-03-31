"""
Tests para el modelo UserProfile.

Verifica la creación automática de perfiles, tipos de usuario,
y métodos de verificación de permisos.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase

from api.models import (
    FinancialInstitution,
    Permission,
    Role,
    UserProfile,
    UserRole,
)

User = get_user_model()


class UserProfileModelTest(TestCase):
    """Tests para el modelo UserProfile."""
    
    def setUp(self):
        """Configuración inicial para los tests."""
        self.user = User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        self.institution = FinancialInstitution.objects.create(
            name='Test Bank',
            slug='test-bank',
            institution_type='banking'
        )
    
    def test_user_profile_auto_created_on_user_creation(self):
        """Verifica que UserProfile se crea automáticamente al crear un User."""
        new_user = User.objects.create_user(
            username='newuser@example.com',
            email='newuser@example.com',
            password='testpass123'
        )
        
        self.assertTrue(hasattr(new_user, 'profile'))
        self.assertIsInstance(new_user.profile, UserProfile)
        self.assertEqual(new_user.profile.user, new_user)
    
    def test_user_profile_default_user_type_is_tenant_user(self):
        """Verifica que el tipo de usuario por defecto es tenant_user."""
        self.assertEqual(self.user.profile.user_type, 'tenant_user')
    
    def test_user_profile_can_be_saas_admin(self):
        """Verifica que se puede crear un perfil de tipo saas_admin."""
        admin_user = User.objects.create_user(
            username='admin@example.com',
            email='admin@example.com',
            password='adminpass123'
        )
        admin_user.profile.user_type = 'saas_admin'
        admin_user.profile.save()
        
        self.assertEqual(admin_user.profile.user_type, 'saas_admin')
    
    def test_is_saas_admin_returns_true_for_saas_admin(self):
        """Verifica que is_saas_admin() retorna True para superadmin."""
        self.user.profile.user_type = 'saas_admin'
        self.user.profile.save()
        
        self.assertTrue(self.user.profile.is_saas_admin())
    
    def test_is_saas_admin_returns_false_for_tenant_user(self):
        """Verifica que is_saas_admin() retorna False para usuario de tenant."""
        self.assertFalse(self.user.profile.is_saas_admin())
    
    def test_has_permission_returns_true_for_saas_admin(self):
        """Verifica que superadmin tiene todos los permisos."""
        self.user.profile.user_type = 'saas_admin'
        self.user.profile.save()
        
        self.assertTrue(
            self.user.profile.has_permission('any.permission', self.institution)
        )
    
    def test_has_permission_returns_true_when_user_has_permission(self):
        """Verifica que has_permission() retorna True cuando el usuario tiene el permiso."""
        # Crear permiso
        permission = Permission.objects.create(
            code='users.view',
            name='Ver usuarios',
            is_active=True
        )
        
        # Crear rol con el permiso
        role = Role.objects.create(
            institution=self.institution,
            name='Admin',
            is_active=True
        )
        role.permissions.add(permission)
        
        # Asignar rol al usuario
        UserRole.objects.create(
            user=self.user,
            role=role,
            institution=self.institution,
            is_active=True
        )
        
        self.assertTrue(
            self.user.profile.has_permission('users.view', self.institution)
        )
    
    def test_has_permission_returns_false_when_user_lacks_permission(self):
        """Verifica que has_permission() retorna False cuando el usuario no tiene el permiso."""
        # Crear permiso que el usuario NO tiene
        Permission.objects.create(
            code='users.delete',
            name='Eliminar usuarios',
            is_active=True
        )
        
        self.assertFalse(
            self.user.profile.has_permission('users.delete', self.institution)
        )
    
    def test_get_permissions_in_institution_returns_all_for_saas_admin(self):
        """Verifica que superadmin obtiene todos los permisos."""
        self.user.profile.user_type = 'saas_admin'
        self.user.profile.save()
        
        # Crear algunos permisos
        Permission.objects.create(code='perm1', name='Permission 1', is_active=True)
        Permission.objects.create(code='perm2', name='Permission 2', is_active=True)
        
        permissions = self.user.profile.get_permissions_in_institution(self.institution)
        self.assertEqual(permissions.count(), 2)
    
    def test_get_permissions_in_institution_returns_user_permissions(self):
        """Verifica que se obtienen solo los permisos del usuario en la institución."""
        # Crear permisos
        perm1 = Permission.objects.create(code='perm1', name='Permission 1', is_active=True)
        perm2 = Permission.objects.create(code='perm2', name='Permission 2', is_active=True)
        perm3 = Permission.objects.create(code='perm3', name='Permission 3', is_active=True)
        
        # Crear rol con perm1 y perm2
        role = Role.objects.create(
            institution=self.institution,
            name='Test Role',
            is_active=True
        )
        role.permissions.add(perm1, perm2)
        
        # Asignar rol al usuario
        UserRole.objects.create(
            user=self.user,
            role=role,
            institution=self.institution,
            is_active=True
        )
        
        permissions = self.user.profile.get_permissions_in_institution(self.institution)
        self.assertEqual(permissions.count(), 2)
        self.assertIn(perm1, permissions)
        self.assertIn(perm2, permissions)
        self.assertNotIn(perm3, permissions)
    
    def test_user_profile_str_representation(self):
        """Verifica la representación en string del perfil."""
        expected = f'Profile: {self.user.email} (tenant_user)'
        self.assertEqual(str(self.user.profile), expected)
    
    def test_user_profile_optional_fields(self):
        """Verifica que los campos opcionales funcionan correctamente."""
        profile = self.user.profile
        profile.phone = '+591 12345678'
        profile.position = 'Gerente'
        profile.department = 'Créditos'
        profile.timezone = 'America/La_Paz'
        profile.language = 'es'
        profile.save()
        
        profile.refresh_from_db()
        self.assertEqual(profile.phone, '+591 12345678')
        self.assertEqual(profile.position, 'Gerente')
        self.assertEqual(profile.department, 'Créditos')
        self.assertEqual(profile.timezone, 'America/La_Paz')
        self.assertEqual(profile.language, 'es')
