"""
Tests para recuperación de contraseña.
"""
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from api.models import FinancialInstitution, FinancialInstitutionMembership, PasswordResetToken


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class PasswordResetRequestAPIViewTestCase(TestCase):
    """Tests para PasswordResetRequestAPIView."""

    def setUp(self):
        """Configurar datos de prueba."""
        self.client = APIClient()
        User = get_user_model()

        # Crear usuario de prueba
        self.user = User.objects.create_user(
            username='testuser',
            email='test@ejemplo.com',
            password='TestPassword123!',
            first_name='Test',
            last_name='User',
        )

        # Crear institución financiera
        self.institution = FinancialInstitution.objects.create(
            name='Banco Test',
            slug='banco-test',
            institution_type='banking',
        )

        # Crear membership
        FinancialInstitutionMembership.objects.create(
            user=self.user,
            institution=self.institution,
            role='admin',
            is_active=True,
        )

    def test_password_reset_request_success(self):
        """Test solicitud de recuperación exitosa."""
        response = self.client.post(
            '/api/auth/password-reset/request/',
            {'email': 'test@ejemplo.com'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        # Verificar que se creó el token
        self.assertTrue(PasswordResetToken.objects.filter(user=self.user).exists())

    def test_password_reset_request_with_nonexistent_email(self):
        """Test solicitud con email que no existe (debe retornar success por seguridad)."""
        response = self.client.post(
            '/api/auth/password-reset/request/',
            {'email': 'noexiste@ejemplo.com'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)

    def test_password_reset_request_with_uppercase_email(self):
        """Test solicitud con email en mayúsculas."""
        response = self.client.post(
            '/api/auth/password-reset/request/',
            {'email': 'TEST@EJEMPLO.COM'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar que se creó el token
        self.assertTrue(PasswordResetToken.objects.filter(user=self.user).exists())

    def test_password_reset_request_with_empty_email(self):
        """Test solicitud con email vacío."""
        response = self.client.post(
            '/api/auth/password-reset/request/',
            {'email': ''},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_password_reset_request_without_email(self):
        """Test solicitud sin email."""
        response = self.client.post(
            '/api/auth/password-reset/request/',
            {},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)


class PasswordResetValidateAPIViewTestCase(TestCase):
    """Tests para PasswordResetValidateAPIView."""

    def setUp(self):
        """Configurar datos de prueba."""
        self.client = APIClient()
        User = get_user_model()

        # Crear usuario de prueba
        self.user = User.objects.create_user(
            username='testuser',
            email='test@ejemplo.com',
            password='TestPassword123!',
        )

        # Crear token válido
        self.valid_token = PasswordResetToken.objects.create(
            user=self.user,
            token='valid-token-123',
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )

        # Crear token expirado
        self.expired_token = PasswordResetToken.objects.create(
            user=self.user,
            token='expired-token-123',
            expires_at=timezone.now() - timezone.timedelta(hours=1),
        )

        # Crear token usado
        self.used_token = PasswordResetToken.objects.create(
            user=self.user,
            token='used-token-123',
            expires_at=timezone.now() + timezone.timedelta(hours=1),
            is_used=True,
        )

    def test_validate_valid_token(self):
        """Test validar token válido."""
        response = self.client.post(
            '/api/auth/password-reset/validate/',
            {'token': 'valid-token-123'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['valid'])

    def test_validate_expired_token(self):
        """Test validar token expirado."""
        response = self.client.post(
            '/api/auth/password-reset/validate/',
            {'token': 'expired-token-123'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['valid'])

    def test_validate_used_token(self):
        """Test validar token ya usado."""
        response = self.client.post(
            '/api/auth/password-reset/validate/',
            {'token': 'used-token-123'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['valid'])

    def test_validate_nonexistent_token(self):
        """Test validar token que no existe."""
        response = self.client.post(
            '/api/auth/password-reset/validate/',
            {'token': 'nonexistent-token'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['valid'])

    def test_validate_empty_token(self):
        """Test validar token vacío."""
        response = self.client.post(
            '/api/auth/password-reset/validate/',
            {'token': ''},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class PasswordResetConfirmAPIViewTestCase(TestCase):
    """Tests para PasswordResetConfirmAPIView."""

    def setUp(self):
        """Configurar datos de prueba."""
        self.client = APIClient()
        User = get_user_model()

        # Crear usuario de prueba
        self.user = User.objects.create_user(
            username='testuser',
            email='test@ejemplo.com',
            password='OldPassword123!',
        )

        # Crear token válido
        self.valid_token = PasswordResetToken.objects.create(
            user=self.user,
            token='valid-token-123',
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )

    def test_confirm_password_reset_success(self):
        """Test confirmar cambio de contraseña exitoso."""
        response = self.client.post(
            '/api/auth/password-reset/confirm/',
            {
                'token': 'valid-token-123',
                'new_password': 'NewPassword123!',
                'confirm_password': 'NewPassword123!',
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        # Verificar que el token se marcó como usado
        self.valid_token.refresh_from_db()
        self.assertTrue(self.valid_token.is_used)
        
        # Verificar que la contraseña cambió
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPassword123!'))

    def test_confirm_password_reset_with_invalid_token(self):
        """Test confirmar con token inválido."""
        response = self.client.post(
            '/api/auth/password-reset/confirm/',
            {
                'token': 'invalid-token',
                'new_password': 'NewPassword123!',
                'confirm_password': 'NewPassword123!',
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_confirm_password_reset_with_mismatched_passwords(self):
        """Test confirmar con contraseñas que no coinciden."""
        response = self.client.post(
            '/api/auth/password-reset/confirm/',
            {
                'token': 'valid-token-123',
                'new_password': 'NewPassword123!',
                'confirm_password': 'DifferentPassword123!',
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('confirm_password', response.data)

    def test_confirm_password_reset_with_weak_password(self):
        """Test confirmar con contraseña débil."""
        response = self.client.post(
            '/api/auth/password-reset/confirm/',
            {
                'token': 'valid-token-123',
                'new_password': '123',
                'confirm_password': '123',
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('new_password', response.data)

    def test_confirm_password_reset_with_empty_password(self):
        """Test confirmar con contraseña vacía."""
        response = self.client.post(
            '/api/auth/password-reset/confirm/',
            {
                'token': 'valid-token-123',
                'new_password': '',
                'confirm_password': '',
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
