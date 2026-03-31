"""
Tests para el modelo UserRole.

Verifica la asignación de roles a usuarios, constraints de unicidad,
y relaciones con instituciones.
"""
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from api.models import (
    FinancialInstitution,
    Permission,
    Role,
    UserRole,
)

User = get_user_model()


class UserRoleModelTest(TestCase):
    """Tests para el modelo UserRole."""
    
    def setUp(self):
        """Configuración inicial para los tests."""
        self.user = User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='testpass123'
        )
        
        self.admin_user = User.objects.create_user(
            username='admin@example.com',
            email='admin@example.com',
            password='adminpass123'
        )
        
        self.institution = FinancialInstitution.objects.create(
            name='Test Bank',
            slug='test-bank',
            institution_type='banking'
        )
        
        self.role = Role.objects.create(
            institution=self.institution,
            name='Analista',
            description='Analista de crédito',
            is_active=True
        )
    
    def test_create_user_role(self):
        """Verifica que se puede crear una asignación de rol."""
        user_role = UserRole.objects.create(
            user=self.user,
            role=self.role,
            institution=self.institution,
            assigned_by=self.admin_user
        )
        
        self.assertEqual(user_role.user, self.user)
        self.assertEqual(user_role.role, self.role)
        self.assertEqual(user_role.institution, self.institution)
        self.assertEqual(user_role.assigned_by, self.admin_user)
        self.assertTrue(user_role.is_active)
    
    def test_user_role_unique_constraint(self):
        """Verifica que no se puede asignar el mismo rol dos veces al mismo usuario en la misma institución."""
        UserRole.objects.create(
            user=self.user,
            role=self.role,
            institution=self.institution
        )
        
        with self.assertRaises(IntegrityError):
            UserRole.objects.create(
                user=self.user,
                role=self.role,
                institution=self.institution
            )
    
    def test_user_role_relationships(self):
        """Verifica que las relaciones ForeignKey funcionan correctamente."""
        user_role = UserRole.objects.create(
            user=self.user,
            role=self.role,
            institution=self.institution
        )
        
        # Verificar relación inversa desde User
        self.assertIn(user_role, self.user.user_roles.all())
        
        # Verificar relación inversa desde Role
        self.assertIn(user_role, self.role.user_assignments.all())
        
        # Verificar relación inversa desde Institution
        self.assertIn(user_role, self.institution.user_role_assignments.all())
    
    def test_user_can_have_multiple_roles(self):
        """Verifica que un usuario puede tener múltiples roles en la misma institución."""
        role2 = Role.objects.create(
            institution=self.institution,
            name='Gerente',
            is_active=True
        )
        
        user_role1 = UserRole.objects.create(
            user=self.user,
            role=self.role,
            institution=self.institution
        )
        
        user_role2 = UserRole.objects.create(
            user=self.user,
            role=role2,
            institution=self.institution
        )
        
        user_roles = self.user.user_roles.filter(institution=self.institution)
        self.assertEqual(user_roles.count(), 2)
        self.assertIn(user_role1, user_roles)
        self.assertIn(user_role2, user_roles)
    
    def test_user_can_have_roles_in_multiple_institutions(self):
        """Verifica que un usuario puede tener roles en diferentes instituciones."""
        institution2 = FinancialInstitution.objects.create(
            name='Another Bank',
            slug='another-bank',
            institution_type='banking'
        )
        
        role2 = Role.objects.create(
            institution=institution2,
            name='Analista',
            is_active=True
        )
        
        user_role1 = UserRole.objects.create(
            user=self.user,
            role=self.role,
            institution=self.institution
        )
        
        user_role2 = UserRole.objects.create(
            user=self.user,
            role=role2,
            institution=institution2
        )
        
        self.assertEqual(self.user.user_roles.count(), 2)
        self.assertEqual(
            self.user.user_roles.filter(institution=self.institution).count(),
            1
        )
        self.assertEqual(
            self.user.user_roles.filter(institution=institution2).count(),
            1
        )
    
    def test_user_role_is_active_default(self):
        """Verifica que is_active es True por defecto."""
        user_role = UserRole.objects.create(
            user=self.user,
            role=self.role,
            institution=self.institution
        )
        
        self.assertTrue(user_role.is_active)
    
    def test_user_role_can_be_deactivated(self):
        """Verifica que se puede desactivar una asignación de rol."""
        user_role = UserRole.objects.create(
            user=self.user,
            role=self.role,
            institution=self.institution
        )
        
        user_role.is_active = False
        user_role.save()
        
        user_role.refresh_from_db()
        self.assertFalse(user_role.is_active)
    
    def test_user_role_str_representation(self):
        """Verifica la representación en string de UserRole."""
        user_role = UserRole.objects.create(
            user=self.user,
            role=self.role,
            institution=self.institution
        )
        
        expected = f'{self.user.email} -> {self.role.name} @ {self.institution.slug}'
        self.assertEqual(str(user_role), expected)
    
    def test_user_role_assigned_by_can_be_null(self):
        """Verifica que assigned_by puede ser null."""
        user_role = UserRole.objects.create(
            user=self.user,
            role=self.role,
            institution=self.institution,
            assigned_by=None
        )
        
        self.assertIsNone(user_role.assigned_by)
    
    def test_user_role_assigned_by_tracks_who_assigned(self):
        """Verifica que se registra quién asignó el rol."""
        user_role = UserRole.objects.create(
            user=self.user,
            role=self.role,
            institution=self.institution,
            assigned_by=self.admin_user
        )
        
        self.assertEqual(user_role.assigned_by, self.admin_user)
        self.assertIn(user_role, self.admin_user.role_assignments_made.all())
    
    def test_filter_active_user_roles(self):
        """Verifica que se pueden filtrar roles activos."""
        active_role = UserRole.objects.create(
            user=self.user,
            role=self.role,
            institution=self.institution,
            is_active=True
        )
        
        role2 = Role.objects.create(
            institution=self.institution,
            name='Gerente',
            is_active=True
        )
        
        inactive_role = UserRole.objects.create(
            user=self.user,
            role=role2,
            institution=self.institution,
            is_active=False
        )
        
        active_roles = self.user.user_roles.filter(is_active=True)
        self.assertEqual(active_roles.count(), 1)
        self.assertIn(active_role, active_roles)
        self.assertNotIn(inactive_role, active_roles)
    
    def test_user_role_with_permissions(self):
        """Verifica que se pueden obtener permisos a través de roles asignados."""
        # Crear permisos
        perm1 = Permission.objects.create(code='users.view', name='Ver usuarios', is_active=True)
        perm2 = Permission.objects.create(code='users.create', name='Crear usuarios', is_active=True)
        
        # Asignar permisos al rol
        self.role.permissions.add(perm1, perm2)
        
        # Asignar rol al usuario
        UserRole.objects.create(
            user=self.user,
            role=self.role,
            institution=self.institution,
            is_active=True
        )
        
        # Obtener permisos del usuario
        user_permissions = Permission.objects.filter(
            roles__user_assignments__user=self.user,
            roles__user_assignments__institution=self.institution,
            roles__user_assignments__is_active=True
        ).distinct()
        
        self.assertEqual(user_permissions.count(), 2)
        self.assertIn(perm1, user_permissions)
        self.assertIn(perm2, user_permissions)
