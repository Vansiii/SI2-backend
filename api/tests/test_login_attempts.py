"""
Tests para protección contra brute force (LoginAttempt).
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from api.models import FinancialInstitution, FinancialInstitutionMembership, LoginAttempt


class LoginAttemptModelTestCase(TestCase):
    """Tests para el modelo LoginAttempt."""

    def setUp(self):
        """Configurar datos de prueba."""
        User = get_user_model()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@ejemplo.com',
            password='TestPassword123!',
        )

    def test_get_recent_failures(self):
        """Test obtener intentos fallidos recientes."""
        # Crear 3 intentos fallidos
        for i in range(3):
            LoginAttempt.objects.create(
                user=self.user,
                email_attempted='test@ejemplo.com',
                ip_address='127.0.0.1',
                was_successful=False,
            )

        failures = LoginAttempt.get_recent_failures('test@ejemplo.com')
        self.assertEqual(failures, 3)

    def test_get_recent_failures_case_insensitive(self):
        """Test que get_recent_failures sea case-insensitive."""
        LoginAttempt.objects.create(
            user=self.user,
            email_attempted='test@ejemplo.com',
            ip_address='127.0.0.1',
            was_successful=False,
        )

        failures = LoginAttempt.get_recent_failures('TEST@EJEMPLO.COM')
        self.assertEqual(failures, 1)

    def test_is_blocked_with_max_attempts(self):
        """Test que is_blocked retorne True después de 5 intentos."""
        # Crear 5 intentos fallidos
        for i in range(5):
            LoginAttempt.objects.create(
                user=self.user,
                email_attempted='test@ejemplo.com',
                ip_address='127.0.0.1',
                was_successful=False,
            )

        is_blocked, remaining = LoginAttempt.is_blocked('test@ejemplo.com')
        self.assertTrue(is_blocked)
        self.assertGreater(remaining, 0)

    def test_is_not_blocked_with_few_attempts(self):
        """Test que is_blocked retorne False con pocos intentos."""
        # Crear 3 intentos fallidos
        for i in range(3):
            LoginAttempt.objects.create(
                user=self.user,
                email_attempted='test@ejemplo.com',
                ip_address='127.0.0.1',
                was_successful=False,
            )

        is_blocked, remaining = LoginAttempt.is_blocked('test@ejemplo.com')
        self.assertFalse(is_blocked)
        self.assertEqual(remaining, 0)

    def test_is_not_blocked_after_time_window(self):
        """Test que is_blocked retorne False después de expirar la ventana de tiempo."""
        # Crear 5 intentos fallidos hace 6 minutos (más que la ventana de 5 minutos)
        old_time = timezone.now() - timezone.timedelta(minutes=6)
        for i in range(5):
            attempt = LoginAttempt.objects.create(
                user=self.user,
                email_attempted='test@ejemplo.com',
                ip_address='127.0.0.1',
                was_successful=False,
            )
            # Modificar manualmente el timestamp
            LoginAttempt.objects.filter(id=attempt.id).update(attempted_at=old_time)

        is_blocked, remaining = LoginAttempt.is_blocked('test@ejemplo.com')
        self.assertFalse(is_blocked)

    def test_clear_failed_attempts(self):
        """Test limpiar intentos fallidos."""
        # Crear 3 intentos fallidos
        for i in range(3):
            LoginAttempt.objects.create(
                user=self.user,
                email_attempted='test@ejemplo.com',
                ip_address='127.0.0.1',
                was_successful=False,
            )

        LoginAttempt.clear_failed_attempts('test@ejemplo.com')
        
        failures = LoginAttempt.get_recent_failures('test@ejemplo.com')
        self.assertEqual(failures, 0)


class BruteForceProtectionTestCase(TestCase):
    """Tests para protección contra brute force en login."""

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

    def test_login_records_successful_attempt(self):
        """Test que el login exitoso registre el intento."""
        response = self.client.post(
            '/api/auth/login/',
            {
                'email': 'test@ejemplo.com',
                'password': 'TestPassword123!',
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar que se registró el intento exitoso
        attempt = LoginAttempt.objects.filter(
            email_attempted='test@ejemplo.com',
            was_successful=True
        ).first()
        self.assertIsNotNone(attempt)

    def test_login_records_failed_attempt(self):
        """Test que el login fallido registre el intento."""
        response = self.client.post(
            '/api/auth/login/',
            {
                'email': 'test@ejemplo.com',
                'password': 'WrongPassword',
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Verificar que se registró el intento fallido
        attempt = LoginAttempt.objects.filter(
            email_attempted='test@ejemplo.com',
            was_successful=False
        ).first()
        self.assertIsNotNone(attempt)

    def test_account_blocked_after_5_failed_attempts(self):
        """Test que la cuenta se bloquee después de 5 intentos fallidos."""
        # Hacer 5 intentos fallidos
        for i in range(5):
            self.client.post(
                '/api/auth/login/',
                {
                    'email': 'test@ejemplo.com',
                    'password': 'WrongPassword',
                },
                format='json'
            )

        # El 6to intento debe estar bloqueado
        response = self.client.post(
            '/api/auth/login/',
            {
                'email': 'test@ejemplo.com',
                'password': 'TestPassword123!',  # Incluso con password correcta
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('bloqueada temporalmente', response.data['detail'])

    def test_successful_login_clears_failed_attempts(self):
        """Test que un login exitoso limpie los intentos fallidos."""
        # Hacer 3 intentos fallidos
        for i in range(3):
            self.client.post(
                '/api/auth/login/',
                {
                    'email': 'test@ejemplo.com',
                    'password': 'WrongPassword',
                },
                format='json'
            )

        # Verificar que hay intentos fallidos
        failures_before = LoginAttempt.get_recent_failures('test@ejemplo.com')
        self.assertEqual(failures_before, 3)

        # Login exitoso
        response = self.client.post(
            '/api/auth/login/',
            {
                'email': 'test@ejemplo.com',
                'password': 'TestPassword123!',
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verificar que se limpiaron los intentos fallidos
        failures_after = LoginAttempt.get_recent_failures('test@ejemplo.com')
        self.assertEqual(failures_after, 0)

    def test_failed_attempts_recorded_with_ip_and_user_agent(self):
        """Test que los intentos fallidos registren IP y user agent."""
        response = self.client.post(
            '/api/auth/login/',
            {
                'email': 'test@ejemplo.com',
                'password': 'WrongPassword',
            },
            format='json',
            HTTP_USER_AGENT='TestBrowser/1.0'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Verificar que se registró IP y user agent
        attempt = LoginAttempt.objects.filter(
            email_attempted='test@ejemplo.com',
            was_successful=False
        ).first()
        
        self.assertIsNotNone(attempt)
        self.assertIsNotNone(attempt.ip_address)
        self.assertEqual(attempt.user_agent, 'TestBrowser/1.0')
