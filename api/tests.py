from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import FinancialInstitution, FinancialInstitutionMembership


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
		self.assertEqual(membership.role, FinancialInstitutionMembership.Role.ADMIN)

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
