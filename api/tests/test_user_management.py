"""
Tests de integración para gestión de usuarios internos.

Verifica que los endpoints de usuarios funcionan correctamente con autorización
y filtrado por tenant.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from api.models import (
    FinancialInstitution,
    FinancialInstitutionMembership,
    Permission,
    Role,
    UserProfile,
    UserRole,
)

User = get_user_model()


class UserManagementTestCase(TestCase):
	"""Tests para gestión de usuarios."""
	
	def setUp(self):
		"""Configuración inicial para los tests."""
		self.client = APIClient()
		
		# Crear instituciones
		self.institution1 = FinancialInstitution.objects.create(
			name='Banco Test 1',
			slug='banco-test-1',
			institution_type='banking'
		)
		
		self.institution2 = FinancialInstitution.objects.create(
			name='Banco Test 2',
			slug='banco-test-2',
			institution_type='banking'
		)
		
		# Crear permisos
		self.perm_view, _ = Permission.objects.get_or_create(
			code='users.view',
			defaults={'name': 'Ver Usuarios', 'is_active': True}
		)
		self.perm_create, _ = Permission.objects.get_or_create(
			code='users.create',
			defaults={'name': 'Crear Usuarios', 'is_active': True}
		)
		self.perm_edit, _ = Permission.objects.get_or_create(
			code='users.edit',
			defaults={'name': 'Editar Usuarios', 'is_active': True}
		)
		self.perm_deactivate, _ = Permission.objects.get_or_create(
			code='users.deactivate',
			defaults={'name': 'Desactivar Usuarios', 'is_active': True}
		)
		self.perm_assign_roles, _ = Permission.objects.get_or_create(
			code='users.assign_roles',
			defaults={'name': 'Asignar Roles', 'is_active': True}
		)
		
		# Crear rol de administrador con todos los permisos
		self.admin_role = Role.objects.create(
			institution=self.institution1,
			name='Administrador',
			is_active=True
		)
		self.admin_role.permissions.add(
			self.perm_view,
			self.perm_create,
			self.perm_edit,
			self.perm_deactivate,
			self.perm_assign_roles
		)
		
		# Crear rol de visor (solo ver)
		self.viewer_role = Role.objects.create(
			institution=self.institution1,
			name='Visor',
			is_active=True
		)
		self.viewer_role.permissions.add(self.perm_view)
		
		# Crear usuario administrador
		self.admin_user = User.objects.create_user(
			username='admin@test.com',
			email='admin@test.com',
			password='testpass123',
			first_name='Admin',
			last_name='User'
		)
		
		profile = UserProfile.objects.get(user=self.admin_user)
		profile.user_type = 'tenant_user'
		profile.save()
		
		FinancialInstitutionMembership.objects.create(
			user=self.admin_user,
			institution=self.institution1,
			role='admin',
			is_active=True
		)
		
		UserRole.objects.create(
			user=self.admin_user,
			role=self.admin_role,
			institution=self.institution1,
			is_active=True
		)
		
		# Crear usuario visor
		self.viewer_user = User.objects.create_user(
			username='viewer@test.com',
			email='viewer@test.com',
			password='testpass123',
			first_name='Viewer',
			last_name='User'
		)
		
		profile = UserProfile.objects.get(user=self.viewer_user)
		profile.user_type = 'tenant_user'
		profile.save()
		
		FinancialInstitutionMembership.objects.create(
			user=self.viewer_user,
			institution=self.institution1,
			role='analyst',
			is_active=True
		)
		
		UserRole.objects.create(
			user=self.viewer_user,
			role=self.viewer_role,
			institution=self.institution1,
			is_active=True
		)
		
		# Crear superadmin SaaS
		self.saas_admin = User.objects.create_user(
			username='saas@admin.com',
			email='saas@admin.com',
			password='testpass123',
			first_name='SaaS',
			last_name='Admin'
		)
		
		profile = UserProfile.objects.get(user=self.saas_admin)
		profile.user_type = 'saas_admin'
		profile.save()
	
	def test_list_users_as_admin(self):
		"""Test que administrador puede listar usuarios de su institución."""
		self.client.force_authenticate(user=self.admin_user)
		
		response = self.client.get('/users/')
		
		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.data), 2)  # admin_user y viewer_user
	
	def test_list_users_as_saas_admin(self):
		"""Test que superadmin SaaS puede listar todos los usuarios."""
		self.client.force_authenticate(user=self.saas_admin)
		
		response = self.client.get('/users/')
		
		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.data), 3)  # Todos los usuarios
	
	def test_create_user_as_admin(self):
		"""Test que administrador puede crear usuarios."""
		self.client.force_authenticate(user=self.admin_user)
		
		data = {
			'email': 'nuevo@test.com',
			'first_name': 'Nuevo',
			'last_name': 'Usuario',
			'password': 'testpass123',
			'role_ids': [self.viewer_role.id],
			'phone': '+591 12345678',
			'position': 'Analista',
			'department': 'Créditos'
		}
		
		response = self.client.post('/users/', data, format='json')
		
		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data['email'], 'nuevo@test.com')
		self.assertEqual(response.data['first_name'], 'Nuevo')
		
		# Verificar que el usuario fue creado
		user = User.objects.get(email='nuevo@test.com')
		self.assertTrue(user.is_active)
		
		# Verificar que tiene el rol asignado
		self.assertTrue(
			UserRole.objects.filter(
				user=user,
				role=self.viewer_role,
				institution=self.institution1,
				is_active=True
			).exists()
		)
	
	def test_create_user_as_viewer_fails(self):
		"""Test que visor no puede crear usuarios."""
		self.client.force_authenticate(user=self.viewer_user)
		
		data = {
			'email': 'nuevo@test.com',
			'first_name': 'Nuevo',
			'last_name': 'Usuario',
			'password': 'testpass123',
			'role_ids': [self.viewer_role.id]
		}
		
		response = self.client.post('/users/', data, format='json')
		
		self.assertEqual(response.status_code, 403)
	
	def test_update_user_as_admin(self):
		"""Test que administrador puede actualizar usuarios."""
		self.client.force_authenticate(user=self.admin_user)
		
		data = {
			'first_name': 'Nombre Actualizado',
			'phone': '+591 87654321'
		}
		
		response = self.client.patch(f'/users/{self.viewer_user.id}/', data, format='json')
		
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['first_name'], 'Nombre Actualizado')
		
		# Verificar que el usuario fue actualizado
		self.viewer_user.refresh_from_db()
		self.assertEqual(self.viewer_user.first_name, 'Nombre Actualizado')
	
	def test_update_user_as_viewer_fails(self):
		"""Test que visor no puede actualizar usuarios."""
		self.client.force_authenticate(user=self.viewer_user)
		
		data = {
			'first_name': 'Nombre Actualizado'
		}
		
		response = self.client.patch(f'/users/{self.admin_user.id}/', data, format='json')
		
		self.assertEqual(response.status_code, 403)
	
	def test_deactivate_user_as_admin(self):
		"""Test que administrador puede desactivar usuarios."""
		self.client.force_authenticate(user=self.admin_user)
		
		response = self.client.delete(f'/users/{self.viewer_user.id}/')
		
		self.assertEqual(response.status_code, 204)
		
		# Verificar que el usuario fue desactivado
		self.viewer_user.refresh_from_db()
		self.assertFalse(self.viewer_user.is_active)
	
	def test_deactivate_user_as_viewer_fails(self):
		"""Test que visor no puede desactivar usuarios."""
		self.client.force_authenticate(user=self.viewer_user)
		
		response = self.client.delete(f'/users/{self.admin_user.id}/')
		
		self.assertEqual(response.status_code, 403)
	
	def test_assign_roles_as_admin(self):
		"""Test que administrador puede asignar roles."""
		self.client.force_authenticate(user=self.admin_user)
		
		data = {
			'role_ids': [self.admin_role.id]
		}
		
		response = self.client.put(f'/users/{self.viewer_user.id}/roles/', data, format='json')
		
		self.assertEqual(response.status_code, 200)
		
		# Verificar que el rol fue asignado
		self.assertTrue(
			UserRole.objects.filter(
				user=self.viewer_user,
				role=self.admin_role,
				institution=self.institution1,
				is_active=True
			).exists()
		)
		
		# Verificar que el rol anterior fue desactivado
		old_role = UserRole.objects.get(
			user=self.viewer_user,
			role=self.viewer_role,
			institution=self.institution1
		)
		self.assertFalse(old_role.is_active)
	
	def test_assign_roles_as_viewer_fails(self):
		"""Test que visor no puede asignar roles."""
		self.client.force_authenticate(user=self.viewer_user)
		
		data = {
			'role_ids': [self.admin_role.id]
		}
		
		response = self.client.put(f'/users/{self.admin_user.id}/roles/', data, format='json')
		
		self.assertEqual(response.status_code, 403)
	
	def test_cannot_access_users_from_other_institution(self):
		"""Test que usuarios no pueden acceder a usuarios de otra institución."""
		# Crear usuario en institución 2
		user_inst2 = User.objects.create_user(
			username='user@inst2.com',
			email='user@inst2.com',
			password='testpass123'
		)
		
		FinancialInstitutionMembership.objects.create(
			user=user_inst2,
			institution=self.institution2,
			role='admin',
			is_active=True
		)
		
		# Intentar acceder desde institución 1
		self.client.force_authenticate(user=self.admin_user)
		
		response = self.client.get(f'/users/{user_inst2.id}/')
		
		self.assertEqual(response.status_code, 404)
	
	def test_saas_admin_can_access_all_users(self):
		"""Test que superadmin SaaS puede acceder a usuarios de cualquier institución."""
		# Crear usuario en institución 2
		user_inst2 = User.objects.create_user(
			username='user@inst2.com',
			email='user@inst2.com',
			password='testpass123'
		)
		
		FinancialInstitutionMembership.objects.create(
			user=user_inst2,
			institution=self.institution2,
			role='admin',
			is_active=True
		)
		
		# Acceder como superadmin
		self.client.force_authenticate(user=self.saas_admin)
		
		response = self.client.get(f'/users/{user_inst2.id}/')
		
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['email'], 'user@inst2.com')
