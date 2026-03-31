"""
Tests para TenantMiddleware.

Verifica que el middleware inyecta correctamente el tenant y user_type en el request.
"""

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from api.middleware import TenantMiddleware
from api.models import FinancialInstitution, FinancialInstitutionMembership, UserProfile

User = get_user_model()


class TenantMiddlewareTestCase(TestCase):
	"""Tests para TenantMiddleware."""
	
	def setUp(self):
		"""Configuración inicial para los tests."""
		self.factory = RequestFactory()
		self.middleware = TenantMiddleware(get_response=lambda r: None)
		
		# Crear institución
		self.institution = FinancialInstitution.objects.create(
			name='Banco Test',
			slug='banco-test',
			institution_type='banking'
		)
		
		# Crear usuario de tenant
		self.tenant_user = User.objects.create_user(
			username='tenant@test.com',
			email='tenant@test.com',
			password='testpass123'
		)
		
		# Crear perfil de tenant user
		UserProfile.objects.filter(user=self.tenant_user).update(
			user_type='tenant_user'
		)
		
		# Crear membership
		FinancialInstitutionMembership.objects.create(
			user=self.tenant_user,
			institution=self.institution,
			role='admin',
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
	
	def test_middleware_injects_tenant_for_tenant_user(self):
		"""Test que el middleware inyecta tenant para usuario de tenant."""
		request = self.factory.get('/')
		request.user = self.tenant_user
		
		self.middleware(request)
		
		self.assertEqual(request.tenant, self.institution)
		self.assertEqual(request.user_type, 'tenant_user')
	
	def test_middleware_injects_none_for_saas_admin(self):
		"""Test que el middleware inyecta None como tenant para superadmin SaaS."""
		# Refrescar usuario desde la base de datos para obtener el perfil actualizado
		self.saas_admin.refresh_from_db()
		
		request = self.factory.get('/')
		request.user = self.saas_admin
		
		self.middleware(request)
		
		self.assertIsNone(request.tenant)
		self.assertEqual(request.user_type, 'saas_admin')
	
	def test_middleware_injects_none_for_unauthenticated_user(self):
		"""Test que el middleware inyecta None para usuario no autenticado."""
		from django.contrib.auth.models import AnonymousUser
		
		request = self.factory.get('/')
		request.user = AnonymousUser()
		
		self.middleware(request)
		
		self.assertIsNone(request.tenant)
		self.assertIsNone(request.user_type)
	
	def test_middleware_handles_user_without_membership(self):
		"""Test que el middleware maneja usuario sin membership activa."""
		# Crear usuario sin membership
		user_no_membership = User.objects.create_user(
			username='nomembership@test.com',
			email='nomembership@test.com',
			password='testpass123'
		)
		
		request = self.factory.get('/')
		request.user = user_no_membership
		
		self.middleware(request)
		
		self.assertIsNone(request.tenant)
		self.assertEqual(request.user_type, 'tenant_user')
	
	def test_middleware_handles_inactive_membership(self):
		"""Test que el middleware ignora memberships inactivas."""
		# Desactivar membership
		FinancialInstitutionMembership.objects.filter(
			user=self.tenant_user
		).update(is_active=False)
		
		request = self.factory.get('/')
		request.user = self.tenant_user
		
		self.middleware(request)
		
		self.assertIsNone(request.tenant)
		self.assertEqual(request.user_type, 'tenant_user')
	
	def test_middleware_uses_first_active_membership(self):
		"""Test que el middleware usa la primera membership activa."""
		# Crear segunda institución y membership
		institution2 = FinancialInstitution.objects.create(
			name='Banco Test 2',
			slug='banco-test-2',
			institution_type='banking'
		)
		
		FinancialInstitutionMembership.objects.create(
			user=self.tenant_user,
			institution=institution2,
			role='admin',
			is_active=True
		)
		
		request = self.factory.get('/')
		request.user = self.tenant_user
		
		self.middleware(request)
		
		# Debe usar la primera membership (self.institution)
		self.assertIsNotNone(request.tenant)
		self.assertEqual(request.user_type, 'tenant_user')
