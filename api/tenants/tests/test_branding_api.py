"""
Tests para la API de personalización visual white-label del tenant.
"""

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from api.models import FinancialInstitution, FinancialInstitutionMembership, UserProfile, Role, Permission, UserRole, TenantBranding

User = get_user_model()


class TenantBrandingApiTestCase(TestCase):
	"""Tests de la API de branding white-label."""

	def setUp(self):
		self.client = APIClient()

		self.institution = FinancialInstitution.objects.create(
			name='Banco Alpha',
			slug='banco-alpha',
			institution_type='banking',
		)
		self.other_institution = FinancialInstitution.objects.create(
			name='Banco Beta',
			slug='banco-beta',
			institution_type='microfinance',
		)

		self.admin_user = User.objects.create_user(
			username='admin@alpha.com',
			email='admin@alpha.com',
			password='admin12345',
			first_name='Admin',
			last_name='Alpha',
		)
		self.admin_profile = UserProfile.objects.get(user=self.admin_user)
		self.admin_profile.user_type = 'tenant_user'
		self.admin_profile.save()
		FinancialInstitutionMembership.objects.create(
			user=self.admin_user,
			institution=self.institution,
			is_active=True,
		)

		self.other_user = User.objects.create_user(
			username='user@beta.com',
			email='user@beta.com',
			password='user12345',
			first_name='User',
			last_name='Beta',
		)
		other_profile = UserProfile.objects.get(user=self.other_user)
		other_profile.user_type = 'tenant_user'
		other_profile.save()
		FinancialInstitutionMembership.objects.create(
			user=self.other_user,
			institution=self.other_institution,
			is_active=True,
		)

		self.permission = Permission.objects.create(
			code='institution.edit',
			name='Editar Institución',
			description='Permite editar la institución',
			is_active=True,
		)
		self.role = Role.objects.create(
			institution=self.institution,
			name='Administrador de Institución',
			description='Rol administrador',
			is_active=True,
		)
		self.role.permissions.add(self.permission)
		UserRole.objects.create(
			user=self.admin_user,
			role=self.role,
			institution=self.institution,
			is_active=True,
		)

		self.client.force_authenticate(user=self.admin_user)

	def test_get_initial_branding_uses_defaults(self):
		response = self.client.get('/api/tenant/branding/')

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertTrue(response.data['success'])
		self.assertEqual(response.data['branding']['display_name'], self.institution.name)
		self.assertEqual(response.data['branding']['primary_color'], '#2563EB')
		self.assertIsNone(response.data['branding']['logo_url'])

	def test_save_branding_with_valid_payload(self):
		logo = SimpleUploadedFile(
			'logo.png',
			b'fake-image-bytes',
			content_type='image/png',
		)
		payload = {
			'display_name': 'Banco Alpha White Label',
			'primary_color': '#1D4ED8',
			'secondary_color': '#0F172A',
			'accent_color': '#F97316',
			'background_color': '#F8FAFC',
			'text_color': '#111827',
			'is_active': True,
			'logo': logo,
		}

		response = self.client.put('/api/tenant/branding/', payload, format='multipart')

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data['branding']['display_name'], 'Banco Alpha White Label')
		self.assertEqual(response.data['branding']['primary_color'], '#1D4ED8')
		self.assertTrue(TenantBranding.objects.filter(institution=self.institution).exists())

	def test_rejects_invalid_hex_color(self):
		payload = {
			'display_name': 'Banco Alpha',
			'primary_color': 'not-a-color',
			'secondary_color': '#0F172A',
			'accent_color': '#F97316',
			'background_color': '#F8FAFC',
			'text_color': '#111827',
		}

		response = self.client.put('/api/tenant/branding/', payload, format='multipart')

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn('primary_color', response.data)

	def test_rejects_invalid_logo_format(self):
		logo = SimpleUploadedFile(
			'logo.gif',
			b'fake-gif',
			content_type='image/gif',
		)
		payload = {
			'display_name': 'Banco Alpha',
			'primary_color': '#1D4ED8',
			'secondary_color': '#0F172A',
			'accent_color': '#F97316',
			'background_color': '#F8FAFC',
			'text_color': '#111827',
			'logo': logo,
		}

		response = self.client.put('/api/tenant/branding/', payload, format='multipart')

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn('logo', response.data)

	def test_rejects_logo_too_large(self):
		logo = SimpleUploadedFile(
			'logo.png',
			b'0' * (5 * 1024 * 1024 + 1),
			content_type='image/png',
		)
		payload = {
			'display_name': 'Banco Alpha',
			'primary_color': '#1D4ED8',
			'secondary_color': '#0F172A',
			'accent_color': '#F97316',
			'background_color': '#F8FAFC',
			'text_color': '#111827',
			'logo': logo,
		}

		response = self.client.put('/api/tenant/branding/', payload, format='multipart')

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn('logo', response.data)

	def test_tenant_isolation(self):
		TenantBranding.objects.create(
			institution=self.other_institution,
			display_name='Banco Beta Brand',
			primary_color='#000000',
			secondary_color='#111111',
			accent_color='#222222',
			background_color='#FFFFFF',
			text_color='#000000',
		)

		response = self.client.get('/api/tenant/branding/')
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertNotEqual(response.data['branding']['display_name'], 'Banco Beta Brand')

	def test_permission_denied_for_other_tenant_user(self):
		self.client.force_authenticate(user=self.other_user)
		response = self.client.get('/api/tenant/branding/')
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_reset_branding_restores_defaults(self):
		TenantBranding.objects.create(
			institution=self.institution,
			display_name='Custom Name',
			primary_color='#111111',
			secondary_color='#222222',
			accent_color='#333333',
			background_color='#444444',
			text_color='#555555',
		)

		response = self.client.post('/api/tenant/branding/reset/')

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data['branding']['display_name'], self.institution.name)
		self.assertEqual(response.data['branding']['primary_color'], '#2563EB')
