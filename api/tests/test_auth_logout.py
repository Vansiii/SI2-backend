"""
Tests para logout de usuario.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from api.models import FinancialInstitution, FinancialInstitutionMembership


class LogoutAPIViewTestCase(TestCase):
    """Tests para LogoutAPIView."""

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

        # Generar tokens
        self.refresh = RefreshToken.for_user(self.user)
        self.access_token = str(self.refresh.access_token)
        self.refresh_token = str(self.refresh)

    def test_logout_success(self):
        """Test logout exitoso con refresh token válido."""
        response = self.client.post(
            '/api/auth/logout/',
            {'refresh': self.refresh_token},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['message'], 'Sesión cerrada exitosamente.')

    def test_logout_with_invalid_token(self):
        """Test logout con token inválido."""
        response = self.client.post(
            '/api/auth/logout/',
            {'refresh': 'token-invalido'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

    def test_logout_with_empty_token(self):
        """Test logout con token vacío."""
        response = self.client.post(
            '/api/auth/logout/',
            {'refresh': ''},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('refresh', response.data)

    def test_logout_without_token(self):
        """Test logout sin enviar token."""
        response = self.client.post(
            '/api/auth/logout/',
            {},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('refresh', response.data)

    def test_logout_with_already_blacklisted_token(self):
        """Test logout con token ya revocado."""
        # Primer logout (exitoso)
        self.client.post(
            '/api/auth/logout/',
            {'refresh': self.refresh_token},
            format='json'
        )

        # Segundo logout con el mismo token (debe fallar)
        response = self.client.post(
            '/api/auth/logout/',
            {'refresh': self.refresh_token},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

    def test_logout_response_structure(self):
        """Test estructura de respuesta de logout exitoso."""
        response = self.client.post(
            '/api/auth/logout/',
            {'refresh': self.refresh_token},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, dict)
        self.assertIn('message', response.data)
        self.assertIsInstance(response.data['message'], str)
