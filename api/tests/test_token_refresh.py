"""
Tests para refresh token.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from api.models import FinancialInstitution, FinancialInstitutionMembership


class TokenRefreshAPIViewTestCase(TestCase):
    """Tests para TokenRefreshView."""

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

    def test_refresh_token_success(self):
        """Test refresh token exitoso."""
        response = self.client.post(
            '/api/auth/token/refresh/',
            {'refresh': self.refresh_token},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)  # Rotación habilitada
        self.assertIsInstance(response.data['access'], str)
        self.assertIsInstance(response.data['refresh'], str)

    def test_refresh_token_with_invalid_token(self):
        """Test refresh token con token inválido."""
        response = self.client.post(
            '/api/auth/token/refresh/',
            {'refresh': 'token-invalido'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token_with_empty_token(self):
        """Test refresh token con token vacío."""
        response = self.client.post(
            '/api/auth/token/refresh/',
            {'refresh': ''},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_refresh_token_without_token(self):
        """Test refresh token sin enviar token."""
        response = self.client.post(
            '/api/auth/token/refresh/',
            {},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_refresh_token_rotation(self):
        """Test que el refresh token se rota (genera uno nuevo)."""
        response = self.client.post(
            '/api/auth/token/refresh/',
            {'refresh': self.refresh_token},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # El nuevo refresh token debe ser diferente al original
        new_refresh_token = response.data['refresh']
        self.assertNotEqual(new_refresh_token, self.refresh_token)

    def test_refresh_token_blacklist_after_rotation(self):
        """Test que el refresh token anterior se agrega a blacklist después de rotar."""
        # Primer refresh (exitoso)
        response = self.client.post(
            '/api/auth/token/refresh/',
            {'refresh': self.refresh_token},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Intentar usar el token anterior (debe fallar porque está en blacklist)
        response = self.client.post(
            '/api/auth/token/refresh/',
            {'refresh': self.refresh_token},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token_response_structure(self):
        """Test estructura de respuesta de refresh token."""
        response = self.client.post(
            '/api/auth/token/refresh/',
            {'refresh': self.refresh_token},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, dict)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        
        # Verificar que los tokens no estén vacíos
        self.assertTrue(len(response.data['access']) > 0)
        self.assertTrue(len(response.data['refresh']) > 0)
