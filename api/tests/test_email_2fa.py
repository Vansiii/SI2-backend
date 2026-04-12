"""
Tests para autenticación de dos factores por email.
"""
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from rest_framework.test import APIClient

from api.models import (
    FinancialInstitution,
    FinancialInstitutionMembership,
    TwoFactorAuth,
    EmailTwoFactorCode,
    AuthChallenge,
)


class EmailTwoFactorSendServiceTestCase(TestCase):
    """Tests para EmailTwoFactorSendService."""

    def setUp(self):
        """Configurar datos de prueba."""
        User = get_user_model()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@ejemplo.com',
            password='TestPassword123!',
        )

    @patch('api.services.email_service.EmailService')
    def test_send_code_success(self, mock_email_service):
        """Test enviar código exitosamente."""
        from api.authentication.email_two_factor_service import (
            EmailTwoFactorSendInput,
            EmailTwoFactorSendService,
        )
        
        # Mock del servicio de email
        mock_email_service.return_value.execute.return_value = MagicMock(success=True)
        
        service = EmailTwoFactorSendService()
        result = service.execute(
            EmailTwoFactorSendInput(
                user=self.user,
                challenge_token='test_token_123',
                purpose='login',
                ip_address='127.0.0.1',
                user_agent='Test Agent',
            )
        )
        
        # Verificar resultado
        self.assertEqual(result.challenge_token, 'test_token_123')
        self.assertEqual(result.expires_in_minutes, 5)
        self.assertIn('Código enviado', result.message)
        
        # Verificar que se creó el código en BD
        code = EmailTwoFactorCode.objects.get(challenge_token='test_token_123')
        self.assertEqual(code.user, self.user)
        self.assertEqual(code.purpose, 'login')
        self.assertFalse(code.is_used)
        self.assertEqual(code.attempts, 0)
        self.assertEqual(code.max_attempts, 3)

    @patch('api.services.email_service.EmailService')
    def test_send_code_invalidates_previous(self, mock_email_service):
        """Test que enviar código invalida códigos anteriores."""
        from api.authentication.email_two_factor_service import (
            EmailTwoFactorSendInput,
            EmailTwoFactorSendService,
        )
        
        mock_email_service.return_value.execute.return_value = MagicMock(success=True)
        
        # Crear código anterior
        EmailTwoFactorCode.objects.create(
            user=self.user,
            code_hash='old_hash',
            challenge_token='old_token',
            purpose='login',
            expires_at=timezone.now() + timedelta(minutes=5),
            is_used=False,
            user_agent='',
        )
        
        # Enviar nuevo código
        service = EmailTwoFactorSendService()
        service.execute(
            EmailTwoFactorSendInput(
                user=self.user,
                challenge_token='new_token',
                purpose='login',
                user_agent='Test Agent',
            )
        )
        
        # Verificar que el código anterior fue invalidado
        old_code = EmailTwoFactorCode.objects.get(challenge_token='old_token')
        self.assertTrue(old_code.is_used)

    @patch('api.services.email_service.EmailService')
    def test_send_code_email_failure(self, mock_email_service):
        """Test que fallo en envío de email invalida el código."""
        from api.authentication.email_two_factor_service import (
            EmailTwoFactorSendInput,
            EmailTwoFactorSendService,
        )
        from rest_framework import serializers
        
        # Mock que falla
        mock_email_service.return_value.execute.side_effect = Exception('Email failed')
        
        service = EmailTwoFactorSendService()
        
        with self.assertRaises(serializers.ValidationError):
            service.execute(
                EmailTwoFactorSendInput(
                    user=self.user,
                    challenge_token='test_token',
                    purpose='login',
                    user_agent='Test Agent',
                )
            )
        
        # Verificar que el código fue marcado como usado
        code = EmailTwoFactorCode.objects.get(challenge_token='test_token')
        self.assertTrue(code.is_used)

    @patch('api.services.email_service.EmailService')
    def test_send_code_email_result_unsuccessful(self, mock_email_service):
        """Test que resultado success=False del email también falla e invalida el código."""
        from api.authentication.email_two_factor_service import (
            EmailTwoFactorSendInput,
            EmailTwoFactorSendService,
        )
        from rest_framework import serializers

        mock_email_service.return_value.execute.return_value = MagicMock(success=False)

        service = EmailTwoFactorSendService()

        with self.assertRaises(serializers.ValidationError):
            service.execute(
                EmailTwoFactorSendInput(
                    user=self.user,
                    challenge_token='test_token_unsuccessful',
                    purpose='login',
                    user_agent='Test Agent',
                )
            )

        code = EmailTwoFactorCode.objects.get(challenge_token='test_token_unsuccessful')
        self.assertTrue(code.is_used)


class EmailTwoFactorVerifyServiceTestCase(TestCase):
    """Tests para EmailTwoFactorVerifyService."""

    def setUp(self):
        """Configurar datos de prueba."""
        User = get_user_model()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@ejemplo.com',
            password='TestPassword123!',
        )
        
        # Crear código de prueba
        import hashlib
        self.test_code = '123456'
        code_hash = hashlib.sha256(self.test_code.encode()).hexdigest()
        
        self.email_code = EmailTwoFactorCode.objects.create(
            user=self.user,
            code_hash=code_hash,
            challenge_token='test_token_123',
            purpose='login',
            expires_at=timezone.now() + timedelta(minutes=5),
            is_used=False,
            attempts=0,
            max_attempts=3,
        )

    def test_verify_valid_code(self):
        """Test verificar código válido."""
        from api.authentication.email_two_factor_service import (
            EmailTwoFactorVerifyInput,
            EmailTwoFactorVerifyService,
        )
        
        service = EmailTwoFactorVerifyService()
        result = service.execute(
            EmailTwoFactorVerifyInput(
                challenge_token='test_token_123',
                code=self.test_code,
            )
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.user, self.user)
        
        # Verificar que el código fue marcado como usado
        self.email_code.refresh_from_db()
        self.assertTrue(self.email_code.is_used)
        self.assertIsNotNone(self.email_code.used_at)

    def test_verify_invalid_code(self):
        """Test verificar código inválido."""
        from api.authentication.email_two_factor_service import (
            EmailTwoFactorVerifyInput,
            EmailTwoFactorVerifyService,
        )
        from rest_framework import serializers
        
        service = EmailTwoFactorVerifyService()
        
        with self.assertRaises(serializers.ValidationError) as context:
            service.execute(
                EmailTwoFactorVerifyInput(
                    challenge_token='test_token_123',
                    code='000000',
                )
            )
        
        self.assertIn('incorrecto', str(context.exception))
        
        # Verificar que se incrementó el contador de intentos
        self.email_code.refresh_from_db()
        self.assertEqual(self.email_code.attempts, 1)

    def test_verify_expired_code(self):
        """Test verificar código expirado."""
        from api.authentication.email_two_factor_service import (
            EmailTwoFactorVerifyInput,
            EmailTwoFactorVerifyService,
        )
        from rest_framework import serializers
        
        # Expirar el código
        self.email_code.expires_at = timezone.now() - timedelta(minutes=1)
        self.email_code.save()
        
        service = EmailTwoFactorVerifyService()
        
        with self.assertRaises(serializers.ValidationError) as context:
            service.execute(
                EmailTwoFactorVerifyInput(
                    challenge_token='test_token_123',
                    code=self.test_code,
                )
            )
        
        self.assertIn('expirado', str(context.exception))

    def test_verify_max_attempts_exceeded(self):
        """Test verificar con intentos máximos excedidos."""
        from api.authentication.email_two_factor_service import (
            EmailTwoFactorVerifyInput,
            EmailTwoFactorVerifyService,
        )
        from rest_framework import serializers
        
        # Establecer intentos al máximo
        self.email_code.attempts = 3
        self.email_code.save()
        
        service = EmailTwoFactorVerifyService()
        
        with self.assertRaises(serializers.ValidationError) as context:
            service.execute(
                EmailTwoFactorVerifyInput(
                    challenge_token='test_token_123',
                    code=self.test_code,
                )
            )
        
        self.assertIn('Demasiados intentos', str(context.exception))

    def test_verify_already_used_code(self):
        """Test verificar código ya usado."""
        from api.authentication.email_two_factor_service import (
            EmailTwoFactorVerifyInput,
            EmailTwoFactorVerifyService,
        )
        from rest_framework import serializers
        
        # Marcar código como usado
        self.email_code.is_used = True
        self.email_code.save()
        
        service = EmailTwoFactorVerifyService()
        
        with self.assertRaises(serializers.ValidationError) as context:
            service.execute(
                EmailTwoFactorVerifyInput(
                    challenge_token='test_token_123',
                    code=self.test_code,
                )
            )
        
        self.assertIn('inválido o ya usado', str(context.exception))


class EmailTwoFactorResendServiceTestCase(TestCase):
    """Tests para EmailTwoFactorResendService."""

    def setUp(self):
        """Configurar datos de prueba."""
        User = get_user_model()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@ejemplo.com',
            password='TestPassword123!',
        )
        
        # Crear código anterior
        import hashlib
        code_hash = hashlib.sha256('123456'.encode()).hexdigest()
        
        self.old_code = EmailTwoFactorCode.objects.create(
            user=self.user,
            code_hash=code_hash,
            challenge_token='old_token_123',
            purpose='login',
            expires_at=timezone.now() + timedelta(minutes=5),
            is_used=False,
            user_agent='',
        )

    @patch('api.services.email_service.EmailService')
    def test_resend_code_success(self, mock_email_service):
        """Test reenviar código exitosamente."""
        from api.authentication.email_two_factor_service import (
            EmailTwoFactorResendInput,
            EmailTwoFactorResendService,
        )
        
        mock_email_service.return_value.execute.return_value = MagicMock(success=True)
        
        service = EmailTwoFactorResendService()
        result = service.execute(
            EmailTwoFactorResendInput(
                challenge_token='old_token_123',
                ip_address='127.0.0.1',
                user_agent='Test Agent',
            )
        )
        
        # El servicio ahora genera un nuevo challenge_token único
        self.assertIsNotNone(result.challenge_token)
        self.assertNotEqual(result.challenge_token, 'old_token_123')
        self.assertEqual(result.expires_in_minutes, 5)
        
        # Verificar que el código anterior fue invalidado
        self.old_code.refresh_from_db()
        self.assertTrue(self.old_code.is_used)
        
        # Verificar que se creó un nuevo código con el nuevo token
        new_code = EmailTwoFactorCode.objects.filter(
            challenge_token=result.challenge_token,
            is_used=False
        ).first()
        self.assertIsNotNone(new_code)

    def test_resend_invalid_token(self):
        """Test reenviar con token inválido."""
        from api.authentication.email_two_factor_service import (
            EmailTwoFactorResendInput,
            EmailTwoFactorResendService,
        )
        from rest_framework import serializers
        
        service = EmailTwoFactorResendService()
        
        with self.assertRaises(serializers.ValidationError):
            service.execute(
                EmailTwoFactorResendInput(
                    challenge_token='invalid_token',
                )
            )


class EmailTwoFactorLoginIntegrationTestCase(TestCase):
    """Tests de integración para login con 2FA por email."""

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
            is_active=True,
        )

    @patch('api.services.email_service.EmailService')
    def test_login_with_email_2fa_sends_code(self, mock_email_service):
        """Test que login con 2FA email envía código automáticamente."""
        mock_email_service.return_value.execute.return_value = MagicMock(success=True)
        
        # Habilitar 2FA por email
        TwoFactorAuth.objects.create(
            user=self.user,
            secret_key='test_secret',
            is_enabled=True,
            method='email',
        )

        # Login
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
        self.assertEqual(response.data['expires_in'], 300)
        
        # Verificar que se creó el código en BD
        challenge_token = response.data['challenge_token']
        code = EmailTwoFactorCode.objects.filter(
            challenge_token=challenge_token
        ).first()
        self.assertIsNotNone(code)
        self.assertEqual(code.user, self.user)

    @patch('api.services.email_service.EmailService')
    def test_verify_email_2fa_with_valid_code(self, mock_email_service):
        """Test verificar código de email válido."""
        mock_email_service.return_value.execute.return_value = MagicMock(success=True)
        
        # Habilitar 2FA por email
        TwoFactorAuth.objects.create(
            user=self.user,
            secret_key='test_secret',
            is_enabled=True,
            method='email',
        )

        # Login inicial
        login_response = self.client.post(
            '/api/auth/login/',
            {
                'email': 'test@ejemplo.com',
                'password': 'TestPassword123!',
            },
            format='json'
        )
        
        challenge_token = login_response.data['challenge_token']
        
        # Obtener el código de la BD (simular que el usuario lo recibió por email)
        email_code = EmailTwoFactorCode.objects.get(challenge_token=challenge_token)
        
        # Generar el código original (en producción vendría del email)
        # Para testing, necesitamos generar un código que coincida con el hash
        import hashlib
        test_code = '123456'
        email_code.code_hash = hashlib.sha256(test_code.encode()).hexdigest()
        email_code.save()

        # Verificar código
        verify_response = self.client.post(
            '/api/auth/login/2fa/',
            {
                'challenge_token': challenge_token,
                'totp_code': test_code,
            },
            format='json'
        )

        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', verify_response.data)
        self.assertIn('refresh', verify_response.data)

    @patch('api.services.email_service.EmailService')
    def test_verify_email_2fa_with_invalid_code(self, mock_email_service):
        """Test verificar código de email inválido."""
        mock_email_service.return_value.execute.return_value = MagicMock(success=True)
        
        # Habilitar 2FA por email
        TwoFactorAuth.objects.create(
            user=self.user,
            secret_key='test_secret',
            is_enabled=True,
            method='email',
        )

        # Login inicial
        login_response = self.client.post(
            '/api/auth/login/',
            {
                'email': 'test@ejemplo.com',
                'password': 'TestPassword123!',
            },
            format='json'
        )
        
        challenge_token = login_response.data['challenge_token']

        # Verificar con código inválido
        verify_response = self.client.post(
            '/api/auth/login/2fa/',
            {
                'challenge_token': challenge_token,
                'totp_code': '000000',
            },
            format='json'
        )

        self.assertEqual(verify_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', verify_response.data)

    @patch('api.services.email_service.EmailService')
    def test_resend_email_2fa_code(self, mock_email_service):
        """Test reenviar código de email."""
        mock_email_service.return_value.execute.return_value = MagicMock(success=True)
        
        # Habilitar 2FA por email
        TwoFactorAuth.objects.create(
            user=self.user,
            secret_key='test_secret',
            is_enabled=True,
            method='email',
        )

        # Login inicial
        login_response = self.client.post(
            '/api/auth/login/',
            {
                'email': 'test@ejemplo.com',
                'password': 'TestPassword123!',
            },
            format='json'
        )
        
        challenge_token = login_response.data['challenge_token']

        # Reenviar código
        resend_response = self.client.post(
            '/api/auth/2fa/email/resend/',
            {
                'challenge_token': challenge_token,
            },
            format='json'
        )

        self.assertEqual(resend_response.status_code, status.HTTP_200_OK)
        self.assertIn('message', resend_response.data)
        self.assertEqual(resend_response.data['expires_in'], 5)


class TwoFactorMethodManagementTestCase(TestCase):
    """Tests para gestión de métodos de 2FA."""

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

        # Habilitar 2FA TOTP
        self.two_factor = TwoFactorAuth.objects.create(
            user=self.user,
            secret_key='test_secret',
            is_enabled=True,
            method='totp',
        )

    def test_get_current_method(self):
        """Test obtener método actual de 2FA."""
        response = self.client.get('/api/auth/2fa/method/', format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['method'], 'totp')
        self.assertTrue(response.data['is_enabled'])

    def test_change_method_to_email(self):
        """Test cambiar método de TOTP a Email."""
        response = self.client.post(
            '/api/auth/2fa/method/set/',
            {
                'method': 'email',
                'password': 'TestPassword123!',
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['method'], 'email')
        
        # Verificar en BD
        self.two_factor.refresh_from_db()
        self.assertEqual(self.two_factor.method, 'email')

    def test_change_method_with_incorrect_password(self):
        """Test cambiar método con contraseña incorrecta."""
        response = self.client.post(
            '/api/auth/2fa/method/set/',
            {
                'method': 'email',
                'password': 'WrongPassword',
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_method_without_2fa_enabled(self):
        """Test cambiar método sin tener 2FA habilitado."""
        # Deshabilitar 2FA
        self.two_factor.is_enabled = False
        self.two_factor.save()

        response = self.client.post(
            '/api/auth/2fa/method/set/',
            {
                'method': 'email',
                'password': 'TestPassword123!',
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class EmailTwoFactorCodeModelTestCase(TestCase):
    """Tests para el modelo EmailTwoFactorCode."""

    def setUp(self):
        """Configurar datos de prueba."""
        User = get_user_model()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@ejemplo.com',
            password='TestPassword123!',
        )

    def test_create_code(self):
        """Test crear código de email."""
        import hashlib
        code_hash = hashlib.sha256('123456'.encode()).hexdigest()
        
        email_code = EmailTwoFactorCode.objects.create(
            user=self.user,
            code_hash=code_hash,
            challenge_token='test_token',
            purpose='login',
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        self.assertEqual(email_code.user, self.user)
        self.assertEqual(email_code.attempts, 0)
        self.assertEqual(email_code.max_attempts, 3)
        self.assertFalse(email_code.is_used)

    def test_is_valid_method(self):
        """Test método is_valid."""
        import hashlib
        code_hash = hashlib.sha256('123456'.encode()).hexdigest()
        
        email_code = EmailTwoFactorCode.objects.create(
            user=self.user,
            code_hash=code_hash,
            challenge_token='test_token',
            purpose='login',
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        # Código válido
        self.assertTrue(email_code.is_valid())

        # Código usado
        email_code.is_used = True
        self.assertFalse(email_code.is_valid())

        # Código expirado
        email_code.is_used = False
        email_code.expires_at = timezone.now() - timedelta(minutes=1)
        self.assertFalse(email_code.is_valid())

        # Intentos excedidos
        email_code.expires_at = timezone.now() + timedelta(minutes=5)
        email_code.attempts = 3
        self.assertFalse(email_code.is_valid())

    def test_mark_as_used_method(self):
        """Test método mark_as_used."""
        import hashlib
        code_hash = hashlib.sha256('123456'.encode()).hexdigest()
        
        email_code = EmailTwoFactorCode.objects.create(
            user=self.user,
            code_hash=code_hash,
            challenge_token='test_token',
            purpose='login',
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        email_code.mark_as_used()

        self.assertTrue(email_code.is_used)
        self.assertIsNotNone(email_code.used_at)
