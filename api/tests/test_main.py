from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import (
	FinancialInstitution,
	FinancialInstitutionMembership,
	Permission,
	Role,
)


class RegisterUserAPITests(APITestCase):
	def setUp(self):
		self.url = reverse('auth-register')
		self.payload = {
			'company_name': 'Banco Futuro S.A.',
			'institution_type': 'banking',
			'first_name': 'Ana',
			'last_name': 'Martinez',
			'email': 'admin@bancofuturo.com',
			'password': 'PwdSegura123*',
			'confirm_password': 'PwdSegura123*',
		}

	def test_register_user_successfully_creates_tenant_admin_and_membership(self):
		response = self.client.post(self.url, self.payload, format='json')

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertIn('institution', response.data)
		self.assertIn('user', response.data)

		user_model = get_user_model()
		user = user_model.objects.get(email='admin@bancofuturo.com')
		self.assertTrue(user.check_password('PwdSegura123*'))
		self.assertEqual(user.first_name, 'Ana')
		self.assertEqual(user.last_name, 'Martinez')

		institution = FinancialInstitution.objects.get(name='Banco Futuro S.A.')
		membership = FinancialInstitutionMembership.objects.get(
			institution=institution,
			user=user,
		)
		# Verificar que se creó el membership
		self.assertTrue(membership.is_active)
		
		# Verificar que se creó el UserRole
		from api.models import UserRole
		user_role = UserRole.objects.filter(user=user, institution=institution, is_active=True).first()
		self.assertIsNotNone(user_role)
		self.assertEqual(user_role.role.name, 'Administrador de Institución')

	def test_register_user_fails_when_email_already_exists(self):
		user_model = get_user_model()
		user_model.objects.create_user(
			username='admin@bancofuturo.com',
			email='admin@bancofuturo.com',
			password='PwdSegura123*',
		)

		response = self.client.post(self.url, self.payload, format='json')

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn('email', response.data)

	def test_register_user_fails_when_password_confirmation_does_not_match(self):
		invalid_payload = {
			**self.payload,
			'confirm_password': 'PwdSegura123+NO',
		}

		response = self.client.post(self.url, invalid_payload, format='json')

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn('confirm_password', response.data)

	def test_register_user_supports_camel_case_payload(self):
		camel_payload = {
			'companyName': 'Banco Vision S.R.L.',
			'institutionType': 'fintech',
			'firstName': 'Luis',
			'lastName': 'Suarez',
			'email': 'admin@vision.com',
			'password': 'PwdSegura123*',
			'confirmPassword': 'PwdSegura123*',
		}

		response = self.client.post(self.url, camel_payload, format='json')

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(response.data['institution']['institution_type'], 'fintech')


# Parte erick sprint 0
class RoleManagementAPITests(APITestCase):
	def setUp(self):
		self.user_model = get_user_model()
		self.admin_user = self.user_model.objects.create_user(
			username='admin@banco.com',
			email='admin@banco.com',
			password='PwdSegura123*',
		)
		self.institution = FinancialInstitution.objects.create(
			name='Banco Futuro',
			slug='banco-futuro',
			institution_type=FinancialInstitution.InstitutionType.BANKING,
			created_by=self.admin_user,
		)
		FinancialInstitutionMembership.objects.create(
			institution=self.institution,
			user=self.admin_user,
		)
		
		# Crear UserProfile y UserRole para el admin
		from api.models import UserProfile, UserRole, Role
		UserProfile.objects.create(
			user=self.admin_user,
			user_type='tenant_user'
		)
		
		# Crear rol de administrador
		admin_role = Role.objects.create(
			institution=self.institution,
			name='Administrador de Institución',
			description='Administrador con acceso completo',
			is_active=True
		)
		
		# Asignar rol al usuario
		UserRole.objects.create(
			user=self.admin_user,
			role=admin_role,
			institution=self.institution,
			assigned_by=self.admin_user,
			is_active=True
		)

		self.permission_view_users = Permission.objects.create(
			code='users.view.test',
			name='Ver usuarios (test)',
			description='Permiso para pruebas de visualizacion de usuarios.',
		)
		self.permission_manage_roles = Permission.objects.create(
			code='roles.manage.test',
			name='Gestionar roles (test)',
			description='Permiso para pruebas de administracion de roles.',
		)

	def test_create_role_with_valid_data(self):
		url = reverse('role-list-create')
		payload = {
			'institution': self.institution.id,
			'name': 'Oficial de Garantias',
			'description': 'Rol encargado de validar garantias.',
		}

		response = self.client.post(url, payload, format='json')

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertTrue(
			Role.objects.filter(
				institution=self.institution,
				name='Oficial de Garantias',
				is_active=True,
			).exists()
		)

	def test_list_roles_returns_registered_roles(self):
		role = Role.objects.create(
			institution=self.institution,
			name='Analista',
			description='Rol de analisis crediticio.',
		)
		url = reverse('role-list-create')

		response = self.client.get(url, format='json')

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(len(response.data), 1)
		self.assertEqual(response.data[0]['id'], role.id)

	def test_update_role_information(self):
		role = Role.objects.create(
			institution=self.institution,
			name='Analista',
			description='Descripcion inicial.',
		)
		url = reverse('role-detail', kwargs={'role_id': role.id})
		payload = {
			'name': 'Analista Senior',
			'description': 'Descripcion actualizada.',
		}

		response = self.client.patch(url, payload, format='json')

		role.refresh_from_db()
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(role.name, 'Analista Senior')
		self.assertEqual(role.description, 'Descripcion actualizada.')

	def test_soft_delete_role(self):
		role = Role.objects.create(
			institution=self.institution,
			name='Gerente de Sucursal',
			description='Rol gerencial',
		)
		url = reverse('role-detail', kwargs={'role_id': role.id})

		response = self.client.delete(url)

		role.refresh_from_db()
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertFalse(role.is_active)

	def test_permission_list_returns_available_permissions(self):
		url = reverse('permission-list')

		response = self.client.get(url, format='json')

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		permission_codes = [item['code'] for item in response.data]
		self.assertIn('users.view.test', permission_codes)
		self.assertIn('roles.manage.test', permission_codes)

	def test_assign_permissions_to_role(self):
		role = Role.objects.create(
			institution=self.institution,
			name='Supervisor',
			description='Supervisa operaciones.',
		)
		url = reverse('role-assign-permissions', kwargs={'role_id': role.id})
		payload = {
			'permission_ids': [self.permission_view_users.id, self.permission_manage_roles.id],
		}

		response = self.client.put(url, payload, format='json')

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		role.refresh_from_db()
		self.assertEqual(role.permissions.count(), 2)

	def test_remove_permission_from_role(self):
		role = Role.objects.create(
			institution=self.institution,
			name='Analista Senior',
			description='Analiza solicitudes complejas.',
		)
		role.permissions.add(self.permission_view_users, self.permission_manage_roles)

		url = reverse(
			'role-remove-permission',
			kwargs={'role_id': role.id, 'permission_id': self.permission_manage_roles.id},
		)

		response = self.client.delete(url)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		role.refresh_from_db()
		self.assertEqual(role.permissions.count(), 1)
		self.assertTrue(role.permissions.filter(id=self.permission_view_users.id).exists())
