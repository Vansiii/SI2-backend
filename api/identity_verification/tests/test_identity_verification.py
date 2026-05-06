"""
Tests para verificación de identidad
"""
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import datetime, timedelta

from api.identity_verification.models import IdentityVerification, IdentityVerificationWebhook
from api.identity_verification.services.identity_verification_service import (
	IdentityVerificationService,
	StartVerificationInput
)
from api.identity_verification.services.didit_client import DiditClient
from api.tenants.models import FinancialInstitution, FinancialInstitutionMembership
from api.loans.models import LoanApplication
from api.clients.models import Client as ClientModel
from api.products.models import CreditProduct

User = get_user_model()


class DiditClientTestCase(TestCase):
	"""Tests para el cliente de Didit"""
	
	def setUp(self):
		self.client = DiditClient()
		self.client.API_KEY = 'test-api-key'
		self.client.WORKFLOW_ID = 'workflow-test-123'
	
	@patch('requests.post')
	def test_create_verification_session_success(self, mock_post):
		"""Debe crear una sesión exitosamente"""
		mock_response = MagicMock()
		mock_response.status_code = 200
		mock_response.json.return_value = {
			'session_id': 'sess_123abc',
			'url': 'https://didit.com/sessions/sess_123abc',
			'session_token': 'token_xyz',
		}
		mock_post.return_value = mock_response
		
		result = self.client.create_verification_session(
			workflow_id='workflow-test-123',
			return_url='https://example.com/callback',
			metadata={'test': 'value'}
		)
		
		self.assertTrue(result.success)
		self.assertEqual(result.session_id, 'sess_123abc')
		self.assertEqual(result.verification_url, 'https://didit.com/sessions/sess_123abc')
	
	@patch('requests.post')
	def test_create_verification_session_auth_error(self, mock_post):
		"""Debe manejar error de autenticación"""
		mock_response = MagicMock()
		mock_response.status_code = 401
		mock_response.json.return_value = {'error': 'Unauthorized'}
		mock_post.return_value = mock_response
		
		result = self.client.create_verification_session(
			workflow_id='workflow-test-123',
			return_url='https://example.com/callback'
		)
		
		self.assertFalse(result.success)
		self.assertEqual(result.error_code, 'UNAUTHORIZED')
	
	@patch('requests.get')
	def test_retrieve_verification_session_success(self, mock_get):
		"""Debe consultar estado de sesión exitosamente"""
		mock_response = MagicMock()
		mock_response.status_code = 200
		mock_response.json.return_value = {
			'session_id': 'sess_123abc',
			'status': 'COMPLETED',
			'decision': 'APPROVED',
			'result': {
				'full_name': 'John Doe',
				'document_type': 'PASSPORT',
				'document_number': '12345678',
				'date_of_birth': '1990-01-01',
				'country': 'US',
			}
		}
		mock_get.return_value = mock_response
		
		result = self.client.retrieve_verification_session('sess_123abc')
		
		self.assertTrue(result.success)
		self.assertEqual(result.status, 'COMPLETED')
		self.assertEqual(result.decision, 'APPROVED')
	
	def test_normalize_didit_status(self):
		"""Debe normalizar estados de Didit correctamente"""
		test_cases = [
			('PENDING', 'PENDING'),
			('COMPLETED', 'APPROVED'),
			('FAILED', 'ERROR'),
			('EXPIRED', 'EXPIRED'),
		]
		
		for didit_status, expected in test_cases:
			result = DiditClient.normalize_didit_status(didit_status)
			self.assertEqual(result, expected)
	
	def test_filter_sensitive_data(self):
		"""Debe filtrar datos sensibles"""
		data = {
			'session_id': 'sess_123',
			'status': 'COMPLETED',
			'secret_token': 'SHOULD_BE_REMOVED',
			'result': {
				'full_name': 'John Doe',
				'document_number': '12345',
				'sensitive_image': 'base64_encoded_image_SHOULD_BE_REMOVED'
			}
		}
		
		filtered = DiditClient._filter_sensitive_data(data)
		
		self.assertIn('session_id', filtered)
		self.assertIn('result', filtered)
		self.assertNotIn('secret_token', filtered)
		self.assertNotIn('sensitive_image', filtered.get('result', {}))


class IdentityVerificationServiceTestCase(APITestCase):
	"""Tests para el servicio de verificación de identidad"""
	
	def setUp(self):
		"""Configurar datos de prueba"""
		# Crear institución
		self.institution = FinancialInstitution.objects.create(
			name='Test Bank',
			slug='test-bank'
		)
		
		# Crear usuario
		self.user = User.objects.create_user(
			email='user@example.com',
			password='testpass123',
			first_name='John',
			last_name='Doe'
		)
		
		# Asociar usuario a institución
		FinancialInstitutionMembership.objects.create(
			user=self.user,
			institution=self.institution,
			is_active=True
		)
		
		# Crear producto
		self.product = CreditProduct.objects.create(
			institution=self.institution,
			name='Personal Loan',
			slug='personal-loan',
			max_amount=10000,
			min_amount=1000
		)
		
		# Crear cliente
		self.client_user = User.objects.create_user(
			email='client@example.com',
			password='testpass123'
		)
		self.client = ClientModel.objects.create(
			user=self.client_user,
			institution=self.institution,
			document_number='123456789'
		)
		
		self.service = IdentityVerificationService()
	
	@patch.object(DiditClient, 'create_verification_session')
	def test_start_verification_success(self, mock_didit):
		"""Debe iniciar verificación exitosamente"""
		mock_didit.return_value = MagicMock(
			success=True,
			session_id='sess_123abc',
			session_token='token_xyz',
			verification_url='https://didit.com/sess_123abc',
			raw_response={}
		)
		
		payload = StartVerificationInput(
			user=self.user,
			institution_id=self.institution.id
		)
		
		result = self.service.start_verification(payload, request_user=self.user)
		
		self.assertTrue(result.success)
		self.assertIsNotNone(result.verification_id)
		
		# Verificar que se creó el registro
		verification = IdentityVerification.objects.get(id=result.verification_id)
		self.assertEqual(verification.user, self.user)
		self.assertEqual(verification.status, IdentityVerification.Status.PENDING)
	
	@patch.object(DiditClient, 'create_verification_session')
	def test_start_verification_didit_error(self, mock_didit):
		"""Debe manejar error de Didit"""
		mock_didit.return_value = MagicMock(
			success=False,
			error='Didit API error',
			error_code='API_ERROR'
		)
		
		payload = StartVerificationInput(
			user=self.user,
			institution_id=self.institution.id
		)
		
		result = self.service.start_verification(payload, request_user=self.user)
		
		self.assertFalse(result.success)
		self.assertEqual(result.error_code, 'API_ERROR')
	
	def test_start_verification_user_not_in_institution(self):
		"""Debe rechazar si el usuario no pertenece a la institución"""
		other_institution = FinancialInstitution.objects.create(
			name='Other Bank',
			slug='other-bank'
		)
		
		payload = StartVerificationInput(
			user=self.user,
			institution_id=other_institution.id
		)
		
		result = self.service.start_verification(payload, request_user=self.user)
		
		self.assertFalse(result.success)
		self.assertEqual(result.error_code, 'USER_NOT_IN_INSTITUTION')
	
	@patch.object(DiditClient, 'create_verification_session')
	def test_cannot_start_active_verification(self, mock_didit):
		"""No debe permitir verificación activa duplicada"""
		# Crear verificación activa
		IdentityVerification.objects.create(
			user=self.user,
			institution=self.institution,
			provider=IdentityVerification.Provider.DIDIT,
			provider_session_id='existing_sess_id',
			verification_url='https://didit.com/existing',
			status=IdentityVerification.Status.PENDING
		)
		
		payload = StartVerificationInput(
			user=self.user,
			institution_id=self.institution.id
		)
		
		result = self.service.start_verification(payload, request_user=self.user)
		
		self.assertFalse(result.success)
		self.assertEqual(result.error_code, 'ACTIVE_VERIFICATION_EXISTS')
	
	@patch.object(DiditClient, 'retrieve_verification_session')
	def test_refresh_verification_success(self, mock_didit):
		"""Debe actualizar estado consultando Didit"""
		# Crear verificación
		verification = IdentityVerification.objects.create(
			user=self.user,
			institution=self.institution,
			provider=IdentityVerification.Provider.DIDIT,
			provider_session_id='sess_123abc',
			verification_url='https://didit.com/sess_123abc',
			status=IdentityVerification.Status.PENDING
		)
		
		mock_didit.return_value = MagicMock(
			success=True,
			session_id='sess_123abc',
			status='COMPLETED',
			decision='APPROVED',
			verification_result={
				'full_name': 'John Doe',
				'document_number': '12345678'
			}
		)
		
		from api.identity_verification.services.identity_verification_service import (
			RefreshVerificationInput
		)
		
		payload = RefreshVerificationInput(
			verification_id=verification.id,
			institution_id=self.institution.id
		)
		
		result = self.service.refresh_verification(payload, request_user=self.user)
		
		self.assertTrue(result.success)
		self.assertEqual(result.status, 'APPROVED')
		
		# Verificar que se actualizó
		verification.refresh_from_db()
		self.assertEqual(verification.status, IdentityVerification.Status.APPROVED)
	
	def test_process_webhook_success(self):
		"""Debe procesar webhook correctamente"""
		# Crear verificación
		verification = IdentityVerification.objects.create(
			user=self.user,
			institution=self.institution,
			provider=IdentityVerification.Provider.DIDIT,
			provider_session_id='sess_123abc',
			verification_url='https://didit.com/sess_123abc',
			status=IdentityVerification.Status.PENDING
		)
		
		payload = {
			'status': 'COMPLETED',
			'decision': 'APPROVED',
			'result': {
				'full_name': 'John Doe',
				'document_number': '12345678'
			}
		}
		
		success = IdentityVerificationService.process_webhook(
			provider='DIDIT',
			provider_event_id='evt_123',
			provider_session_id='sess_123abc',
			payload=payload
		)
		
		self.assertTrue(success)
		
		# Verificar que se actualizó
		verification.refresh_from_db()
		self.assertEqual(verification.status, IdentityVerification.Status.APPROVED)
		self.assertEqual(verification.decision, IdentityVerification.Decision.APPROVED)
	
	def test_process_webhook_duplicate(self):
		"""Debe manejar webhooks duplicados idempotentemente"""
		# Crear verificación
		verification = IdentityVerification.objects.create(
			user=self.user,
			institution=self.institution,
			provider=IdentityVerification.Provider.DIDIT,
			provider_session_id='sess_123abc',
			verification_url='https://didit.com/sess_123abc',
			status=IdentityVerification.Status.PENDING
		)
		
		payload = {
			'status': 'COMPLETED',
			'decision': 'APPROVED',
			'result': {}
		}
		
		# Procesar dos veces el mismo evento
		success1 = IdentityVerificationService.process_webhook(
			provider='DIDIT',
			provider_event_id='evt_123',
			provider_session_id='sess_123abc',
			payload=payload
		)
		
		success2 = IdentityVerificationService.process_webhook(
			provider='DIDIT',
			provider_event_id='evt_123',
			provider_session_id='sess_123abc',
			payload=payload
		)
		
		self.assertTrue(success1)
		self.assertTrue(success2)  # Debe ser idempotente
		
		# Verificar que el webhook se marcó como duplicado
		webhook_count = IdentityVerificationWebhook.objects.filter(
			provider_event_id='evt_123'
		).count()
		self.assertEqual(webhook_count, 1)


class IdentityVerificationAPITestCase(APITestCase):
	"""Tests para los endpoints REST"""
	
	def setUp(self):
		"""Configurar datos de prueba"""
		self.client_obj = APIClient()
		
		# Crear institución
		self.institution = FinancialInstitution.objects.create(
			name='Test Bank',
			slug='test-bank'
		)
		
		# Crear usuario
		self.user = User.objects.create_user(
			email='user@example.com',
			password='testpass123'
		)
		
		# Asociar usuario a institución
		FinancialInstitutionMembership.objects.create(
			user=self.user,
			institution=self.institution,
			is_active=True
		)
		
		# Obtener token
		self.client_obj.force_authenticate(user=self.user)
	
	@patch.object(IdentityVerificationService, 'start_verification')
	def test_start_verification_endpoint(self, mock_service):
		"""Debe iniciar verificación vía endpoint"""
		mock_service.return_value = MagicMock(
			success=True,
			verification_id=1,
			verification_url='https://didit.com/sess_123',
			provider_session_id='sess_123'
		)
		
		# Crear verificación de prueba
		verification = IdentityVerification.objects.create(
			user=self.user,
			institution=self.institution,
			provider=IdentityVerification.Provider.DIDIT,
			provider_session_id='sess_123',
			verification_url='https://didit.com/sess_123',
			status=IdentityVerification.Status.PENDING
		)
		
		response = self.client_obj.post(
			'/api/identity-verifications/',
			data={'return_url': 'https://example.com/callback'}
		)
		
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
	
	def test_webhook_endpoint_success(self):
		"""Debe procesar webhook de Didit"""
		# Crear verificación
		verification = IdentityVerification.objects.create(
			user=self.user,
			institution=self.institution,
			provider=IdentityVerification.Provider.DIDIT,
			provider_session_id='sess_123abc',
			verification_url='https://didit.com/sess_123abc',
			status=IdentityVerification.Status.PENDING
		)
		
		payload = {
			'event_id': 'evt_123',
			'session_id': 'sess_123abc',
			'status': 'COMPLETED',
			'decision': 'APPROVED',
			'result': {}
		}
		
		response = self.client_obj.post(
			'/api/identity-verifications/webhook/didit/',
			data=payload,
			format='json'
		)
		
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		
		# Verificar que se actualizó
		verification.refresh_from_db()
		self.assertEqual(verification.status, IdentityVerification.Status.APPROVED)
	
	def test_webhook_endpoint_missing_fields(self):
		"""Debe rechazar webhook sin campos requeridos"""
		payload = {
			'event_id': 'evt_123'
			# Falta session_id
		}
		
		response = self.client_obj.post(
			'/api/identity-verifications/webhook/didit/',
			data=payload,
			format='json'
		)
		
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
