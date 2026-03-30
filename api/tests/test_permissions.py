"""
Tests para clases de permisos personalizadas.

Verifica que HasPermission y require_permission funcionan correctamente.
"""

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from rest_framework.views import APIView

from api.models import (
    FinancialInstitution,
    FinancialInstitutionMembership,
    Permission,
    Role,
    UserProfile,
    UserRole,
)
from api.permissions import HasPermission, require_permission

User = get_user_model()


class HasPermissionTestCase(TestCase):
	"""Tests para HasPermission permission class."""
	
	def setUp(self):
		"""Configuración inicial para los tests."""
		self.factory = RequestFactory()
		
		# Crear institución
		self.institution = FinancialInstitution.objects.create(
			name='Banco Test',
			slug='banco-test',
			institution_type='banking'
		)
		
		# Crear permisos (usar get_or_create para evitar duplicados)
		self.permission_view, _ = Permission.objects.get_or_create(
			code='users.view',
			defaults={
				'name': 'Ver Usuarios',
				'is_active': True
			}
		)
		
		self.permission_create, _ = Permission.objects.get_or_create(
			code='users.create',
			defaults={
				'name': 'Crear Usuarios',
				'is_active': True
			}
		)
		
		# Crear rol con permiso de ver
		self.role = Role.objects.create(
			institution=self.institution,
			name='Visor',
			is_active=True
		)
		self.role.permissions.add(self.permission_view)
		
		# Crear usuario de tenant con rol
		self.tenant_user = User.objects.create_user(
			username='tenant@test.com',
			email='tenant@test.com',
			password='testpass123'
		)
		
		UserProfile.objects.filter(user=self.tenant_user).update(
			user_type='tenant_user'
		)
		
		FinancialInstitutionMembership.objects.create(
			user=self.tenant_user,
			institution=self.institution,
			role='admin',
			is_active=True
		)
		
		UserRole.objects.create(
			user=self.tenant_user,
			role=self.role,
			institution=self.institution,
			is_active=True
		)
		
		# Crear superadmin SaaS
		self.saas_admin = User.objects.create_user(
			username='admin@saas.com',
			email='admin@saas.com',
			password='testpass123'
		)
		
		# Actualizar perfil de superadmin (el signal ya lo creó)
		profile = UserProfile.objects.get(user=self.saas_admin)
		profile.user_type = 'saas_admin'
		profile.save()
	
	def test_has_permission_returns_false_for_unauthenticated(self):
		"""Test que HasPermission retorna False para usuario no autenticado."""
		from django.contrib.auth.models import AnonymousUser
		
		request = self.factory.get('/')
		request.user = AnonymousUser()
		
		permission = HasPermission('users.view')
		result = permission.has_permission(request, None)
		
		self.assertFalse(result)
	
	def test_has_permission_returns_true_for_saas_admin(self):
		"""Test que HasPermission retorna True para superadmin SaaS."""
		# Refrescar usuario desde la base de datos para obtener el perfil actualizado
		self.saas_admin.refresh_from_db()
		
		request = self.factory.get('/')
		request.user = self.saas_admin
		request.tenant = None
		
		permission = HasPermission('users.view')
		result = permission.has_permission(request, None)
		
		self.assertTrue(result)
	
	def test_has_permission_returns_true_when_user_has_permission(self):
		"""Test que HasPermission retorna True cuando usuario tiene el permiso."""
		request = self.factory.get('/')
		request.user = self.tenant_user
		request.tenant = self.institution
		
		permission = HasPermission('users.view')
		result = permission.has_permission(request, None)
		
		self.assertTrue(result)
	
	def test_has_permission_returns_false_when_user_lacks_permission(self):
		"""Test que HasPermission retorna False cuando usuario no tiene el permiso."""
		request = self.factory.get('/')
		request.user = self.tenant_user
		request.tenant = self.institution
		
		permission = HasPermission('users.create')
		result = permission.has_permission(request, None)
		
		self.assertFalse(result)
	
	def test_has_permission_returns_false_when_no_tenant(self):
		"""Test que HasPermission retorna False cuando no hay tenant."""
		request = self.factory.get('/')
		request.user = self.tenant_user
		request.tenant = None
		
		permission = HasPermission('users.view')
		result = permission.has_permission(request, None)
		
		self.assertFalse(result)
	
	def test_has_permission_returns_false_when_user_has_no_profile(self):
		"""Test que HasPermission retorna False cuando usuario no tiene perfil."""
		user_no_profile = User.objects.create_user(
			username='noprofile@test.com',
			email='noprofile@test.com',
			password='testpass123'
		)
		
		# Eliminar perfil
		UserProfile.objects.filter(user=user_no_profile).delete()
		
		request = self.factory.get('/')
		request.user = user_no_profile
		request.tenant = self.institution
		
		permission = HasPermission('users.view')
		result = permission.has_permission(request, None)
		
		self.assertFalse(result)
	
	def test_require_permission_factory_creates_permission_class(self):
		"""Test que require_permission crea una clase de permiso correctamente."""
		PermissionClass = require_permission('users.view')
		
		# Verificar que es una clase
		self.assertTrue(isinstance(PermissionClass, type))
		
		# Verificar que hereda de HasPermission
		self.assertTrue(issubclass(PermissionClass, HasPermission))
		
		# Verificar que tiene nombre descriptivo
		self.assertEqual(PermissionClass.__name__, 'Require_users_view')
	
	def test_require_permission_works_in_view(self):
		"""Test que require_permission funciona en una vista."""
		class TestView(APIView):
			permission_classes = [require_permission('users.view')]
		
		view = TestView()
		
		# Verificar que tiene permission_classes
		self.assertEqual(len(view.permission_classes), 1)
		
		# Verificar que es la clase correcta
		self.assertTrue(issubclass(view.permission_classes[0], HasPermission))
	
	def test_has_permission_with_inactive_role(self):
		"""Test que HasPermission retorna False cuando el rol está inactivo."""
		# Desactivar rol
		UserRole.objects.filter(user=self.tenant_user).update(is_active=False)
		
		request = self.factory.get('/')
		request.user = self.tenant_user
		request.tenant = self.institution
		
		permission = HasPermission('users.view')
		result = permission.has_permission(request, None)
		
		self.assertFalse(result)
	
	def test_has_permission_with_multiple_roles(self):
		"""Test que HasPermission funciona con múltiples roles."""
		# Crear segundo rol con permiso de crear
		role2 = Role.objects.create(
			institution=self.institution,
			name='Creador',
			is_active=True
		)
		role2.permissions.add(self.permission_create)
		
		# Asignar segundo rol al usuario
		UserRole.objects.create(
			user=self.tenant_user,
			role=role2,
			institution=self.institution,
			is_active=True
		)
		
		request = self.factory.get('/')
		request.user = self.tenant_user
		request.tenant = self.institution
		
		# Verificar que tiene ambos permisos
		permission_view = HasPermission('users.view')
		self.assertTrue(permission_view.has_permission(request, None))
		
		permission_create = HasPermission('users.create')
		self.assertTrue(permission_create.has_permission(request, None))
