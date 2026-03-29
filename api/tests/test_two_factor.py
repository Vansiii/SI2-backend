"""
Tests para autenticación de dos factores (2FA).
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from api.models import FinancialInstitution, FinancialInstitutionMembership, TwoFactorAuth


class TwoFactorEnableAPIViewTestCase(TestCase):
    """Tests para habilitar 2FA."""

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

        # Crear institución y membership
        self.institution = FinancialInstitution.objects.create(
            name='Banco Test',
            slug='banco-test',
            institution_type='banking',
        )
        FinancialInstitutionMembership.objects.create(
            user=self.user,
            institution=self.institution,
            role='admin',
            is_active=True,
        )

        # Autenticar usuario
        self.client.force_authenticate(user=self.user)

    def test_enable_2fa_success(self):
        """Test habilitar 2FA exitosamente."""
        response = self.client.post('/api/auth/2fa/enable/', format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('secret', response.data)
        self.assertIn('qr_code', response.data)
        self.assertIn('backup_codes', response.data)
        self.assertEqual(len(response.data['backup_codes']), 10)

    def test_enable_2fa_creates_twofactor_record(self):
        """Test que habilitar 2FA cree el registro."""
        self.client.post('/api/auth/2fa/enable/', format='json')

        # Verificar que se creó el registro
        self.assertTrue(TwoFactorAuth.objects.filter(user=self.user).exists())
        
        # Verificar que NO está habilitado aún
        two_factor = TwoFactorAuth.objects.get(user=self.user)
        self.assertFalse(two_factor.is_enabled)

    def test_enable_2fa_requires_authentication(self):
        """Test que habilitar 2FA requiera autenticación."""
        self.client.force_authenticate(user=None)
        
        response = self.client.post('/api/auth/2fa/enable/', format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TwoFactorVerifyAPIViewTestCase(TestCase):
    """Tests para verificar y activar 2FA."""

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

        # Autenticar usuario
        self.client.force_authenticate(user=self.user)

        # Habilitar 2FA
        response = self.client.post('/api/auth/2fa/enable/', format='json')
        self.secret = response.data['secret']

    def test_verify_2fa_with_valid_token(self):
        """Test verificar 2FA con token válido."""
        import pyotp
        
        # Generar token válido
        totp = pyotp.TOTP(self.secret)
        token = totp.now()

        response = self.client.post(
            '/api/auth/2fa/verify/',
            {'token': token},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar que 2FA está habilitado
        two_factor = TwoFactorAuth.objects.get(user=self.user)
        self.assertTrue(two_factor.is_enabled)

    def test_verify_2fa_with_invalid_token(self):
        """Test verificar 2FA con token inválido."""
        response = self.client.post(
            '/api/auth/2fa/verify/',
            {'token': '000000'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_2fa_with_non_numeric_token(self):
        """Test verificar 2FA con token no numérico."""
        response = self.client.post(
            '/api/auth/2fa/verify/',
            {'token': 'ABCDEF'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TwoFactorDisableAPIViewTestCase(TestCase):
    """Tests para deshabilitar 2FA."""

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

        # Autenticar usuario
        self.client.force_authenticate(user=self.user)

        # Habilitar y activar 2FA
        response = self.client.post('/api/auth/2fa/enable/', format='json')
        secret = response.data['secret']
        
        import pyotp
        totp = pyotp.TOTP(secret)
        token = totp.now()
        
        self.client.post('/api/auth/2fa/verify/', {'token': token}, format='json')

    def test_disable_2fa_with_correct_password(self):
        """Test deshabilitar 2FA con contraseña correcta."""
        response = self.client.post(
            '/api/auth/2fa/disable/',
            {'password': 'TestPassword123!'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar que 2FA está deshabilitado
        two_factor = TwoFactorAuth.objects.get(user=self.user)
        self.assertFalse(two_factor.is_enabled)

    def test_disable_2fa_with_incorrect_password(self):
        """Test deshabilitar 2FA con contraseña incorrecta."""
        response = self.client.post(
            '/api/auth/2fa/disable/',
            {'password': 'WrongPassword'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TwoFactorStatusAPIViewTestCase(TestCase):
    """Tests para obtener estado de 2FA."""

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

        # Autenticar usuario
        self.client.force_authenticate(user=self.user)

    def test_status_without_2fa(self):
        """Test obtener estado sin 2FA configurado."""
        response = self.client.get('/api/auth/2fa/status/', format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_enabled'])
        self.assertIsNone(response.data['enabled_at'])
        self.assertEqual(response.data['backup_codes_remaining'], 0)

    def test_status_with_2fa_enabled(self):
        """Test obtener estado con 2FA habilitado."""
        # Habilitar y activar 2FA
        response = self.client.post('/api/auth/2fa/enable/', format='json')
        secret = response.data['secret']
        
        import pyotp
        totp = pyotp.TOTP(secret)
        token = totp.now()
        
        self.client.post('/api/auth/2fa/verify/', {'token': token}, format='json')

        # Obtener estado
        response = self.client.get('/api/auth/2fa/status/', format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_enabled'])
        self.assertIsNotNone(response.data['enabled_at'])
        self.assertEqual(response.data['backup_codes_remaining'], 10)



class TwoFactorLoginIntegrationTestCase(TestCase):
    """Tests para integración de 2FA en login."""

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

        # Crear institución y membership
        self.institution = FinancialInstitution.objects.create(
            name='Banco Test',
            slug='banco-test',
            institution_type='banking',
        )
        FinancialInstitutionMembership.objects.create(
            user=self.user,
            institution=self.institution,
            role='admin',
            is_active=True,
        )

    def test_login_without_2fa_returns_tokens(self):
        """Test login sin 2FA retorna tokens directamente."""
        response = self.client.post(
            '/api/auth/login/',
            {
                'email': 'test@ejemplo.com',
                'password': 'TestPassword123!',
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertFalse(response.data['requires_2fa'])

    def test_login_with_2fa_requires_code(self):
        """Test login con 2FA habilitado requiere código."""
        # Habilitar y activar 2FA
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/auth/2fa/enable/', format='json')
        secret = response.data['secret']
        
        import pyotp
        totp = pyotp.TOTP(secret)
        token = totp.now()
        
        self.client.post('/api/auth/2fa/verify/', {'token': token}, format='json')
        self.client.force_authenticate(user=None)

        # Intentar login
        response = self.client.post(
            '/api/auth/login/',
            {
                'email': 'test@ejemplo.com',
                'password': 'TestPassword123!',
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['requires_2fa'])
        self.assertIn('challenge_token', response.data)
        self.assertIn('expires_in', response.data)
        self.assertEqual(response.data['expires_in'], 300)
        self.assertNotIn('access', response.data)
        self.assertNotIn('refresh', response.data)

    def test_login_with_2fa_and_valid_code(self):
        """Test login con 2FA y código válido retorna tokens."""
        # Habilitar y activar 2FA
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/auth/2fa/enable/', format='json')
        secret = response.data['secret']
        
        import pyotp
        totp = pyotp.TOTP(secret)
        token = totp.now()
        
        self.client.post('/api/auth/2fa/verify/', {'token': token}, format='json')
        self.client.force_authenticate(user=None)

        # Primer paso: Login inicial
        login_response = self.client.post(
            '/api/auth/login/',
            {
                'email': 'test@ejemplo.com',
                'password': 'TestPassword123!',
            },
            format='json'
        )
        
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        challenge_token = login_response.data['challenge_token']

        # Segundo paso: Verificar código 2FA con challenge token
        new_token = totp.now()
        response = self.client.post(
            '/api/auth/login/2fa/',
            {
                'challenge_token': challenge_token,
                'totp_code': new_token,
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_with_2fa_and_invalid_code(self):
        """Test login con 2FA y código inválido falla."""
        # Habilitar y activar 2FA
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/auth/2fa/enable/', format='json')
        secret = response.data['secret']
        
        import pyotp
        totp = pyotp.TOTP(secret)
        token = totp.now()
        
        self.client.post('/api/auth/2fa/verify/', {'token': token}, format='json')
        self.client.force_authenticate(user=None)

        # Primer paso: Login inicial
        login_response = self.client.post(
            '/api/auth/login/',
            {
                'email': 'test@ejemplo.com',
                'password': 'TestPassword123!',
            },
            format='json'
        )
        
        challenge_token = login_response.data['challenge_token']

        # Segundo paso: Verificar con código inválido
        response = self.client.post(
            '/api/auth/login/2fa/',
            {
                'challenge_token': challenge_token,
                'totp_code': '000000',
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_with_2fa_and_backup_code(self):
        """Test login con 2FA usando código de respaldo."""
        # Habilitar y activar 2FA
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/auth/2fa/enable/', format='json')
        secret = response.data['secret']
        backup_codes = response.data['backup_codes']
        
        import pyotp
        totp = pyotp.TOTP(secret)
        token = totp.now()
        
        self.client.post('/api/auth/2fa/verify/', {'token': token}, format='json')
        self.client.force_authenticate(user=None)

        # Primer paso: Login inicial
        login_response = self.client.post(
            '/api/auth/login/',
            {
                'email': 'test@ejemplo.com',
                'password': 'TestPassword123!',
            },
            format='json'
        )
        
        challenge_token = login_response.data['challenge_token']

        # Segundo paso: Verificar con código de respaldo
        response = self.client.post(
            '/api/auth/login/2fa/',
            {
                'challenge_token': challenge_token,
                'totp_code': backup_codes[0],
                'is_backup_code': True,
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

        # Verificar que el código de respaldo fue consumido
        two_factor = TwoFactorAuth.objects.get(user=self.user)
        self.assertEqual(len(two_factor.backup_codes), 9)



class TwoFactorRegenerateBackupCodesTestCase(TestCase):
    """Tests para regeneración de códigos de respaldo."""

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

        # Autenticar usuario
        self.client.force_authenticate(user=self.user)

        # Habilitar y activar 2FA
        response = self.client.post('/api/auth/2fa/enable/', format='json')
        self.secret = response.data['secret']
        self.original_backup_codes = response.data['backup_codes']
        
        import pyotp
        totp = pyotp.TOTP(self.secret)
        token = totp.now()
        
        self.client.post('/api/auth/2fa/verify/', {'token': token}, format='json')

    def test_regenerate_backup_codes_with_correct_password(self):
        """Test regenerar códigos con contraseña correcta."""
        response = self.client.post(
            '/api/auth/2fa/backup-codes/regenerate/',
            {'password': 'TestPassword123!'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('backup_codes', response.data)
        self.assertEqual(len(response.data['backup_codes']), 10)
        
        # Verificar que los códigos son diferentes a los originales
        new_codes = response.data['backup_codes']
        self.assertNotEqual(set(new_codes), set(self.original_backup_codes))

    def test_regenerate_backup_codes_with_incorrect_password(self):
        """Test regenerar códigos con contraseña incorrecta."""
        response = self.client.post(
            '/api/auth/2fa/backup-codes/regenerate/',
            {'password': 'WrongPassword'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_regenerate_backup_codes_without_2fa_enabled(self):
        """Test regenerar códigos sin 2FA habilitado."""
        # Deshabilitar 2FA
        self.client.post(
            '/api/auth/2fa/disable/',
            {'password': 'TestPassword123!'},
            format='json'
        )

        # Intentar regenerar códigos
        response = self.client.post(
            '/api/auth/2fa/backup-codes/regenerate/',
            {'password': 'TestPassword123!'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_regenerate_backup_codes_requires_authentication(self):
        """Test que regenerar códigos requiera autenticación."""
        self.client.force_authenticate(user=None)
        
        response = self.client.post(
            '/api/auth/2fa/backup-codes/regenerate/',
            {'password': 'TestPassword123!'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regenerate_backup_codes_updates_database(self):
        """Test que regenerar códigos actualice la base de datos."""
        response = self.client.post(
            '/api/auth/2fa/backup-codes/regenerate/',
            {'password': 'TestPassword123!'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar que los códigos en la base de datos son los nuevos
        two_factor = TwoFactorAuth.objects.get(user=self.user)
        self.assertEqual(set(two_factor.backup_codes), set(response.data['backup_codes']))
