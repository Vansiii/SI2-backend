from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework_simplejwt.tokens import RefreshToken


class JWTConfigTestCase(TestCase):
    """Tests para verificar configuración de JWT."""

    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            username='testuser@ejemplo.com',
            email='testuser@ejemplo.com',
            password='TestPassword123!',
        )

    def test_generate_jwt_tokens(self):
        """Test generación de tokens JWT."""
        # Generar tokens
        refresh = RefreshToken.for_user(self.user)
        access = str(refresh.access_token)
        refresh_token = str(refresh)

        # Verificar que los tokens se generaron
        self.assertIsNotNone(access)
        self.assertIsNotNone(refresh_token)
        self.assertGreater(len(access), 50)
        self.assertGreater(len(refresh_token), 50)

    def test_jwt_token_contains_user_id(self):
        """Test que el token contiene el user_id."""
        # Generar token
        refresh = RefreshToken.for_user(self.user)
        
        # Verificar que contiene el user_id (como string en el token)
        self.assertEqual(str(refresh['user_id']), str(self.user.id))

    def test_access_token_lifetime(self):
        """Test que el access token tiene el lifetime correcto."""
        from django.conf import settings
        
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        
        # Verificar que el token tiene expiración
        self.assertIn('exp', access_token)
        
        # El lifetime debe ser 15 minutos (configurado en settings)
        expected_lifetime = settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']
        self.assertEqual(expected_lifetime.total_seconds(), 15 * 60)

    def test_refresh_token_lifetime(self):
        """Test que el refresh token tiene el lifetime correcto."""
        from django.conf import settings
        
        refresh = RefreshToken.for_user(self.user)
        
        # Verificar que el token tiene expiración
        self.assertIn('exp', refresh)
        
        # El lifetime debe ser 7 días (configurado en settings)
        expected_lifetime = settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']
        self.assertEqual(expected_lifetime.total_seconds(), 7 * 24 * 60 * 60)
