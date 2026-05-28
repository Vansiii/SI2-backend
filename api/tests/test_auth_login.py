from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from api.models import FinancialInstitution, FinancialInstitutionMembership


class LoginAPITestCase(TestCase):
    """Tests para el endpoint de login."""

    def setUp(self):
        self.client = APIClient()
        self.User = get_user_model()
        
        # Crear usuario de prueba
        self.user = self.User.objects.create_user(
            username='test@ejemplo.com',
            email='test@ejemplo.com',
            password='TestPassword123!',
            first_name='Juan',
            last_name='Pérez',
        )
        
        # Crear institución
        self.institution = FinancialInstitution.objects.create(
            name='Banco Test',
            slug='banco-test',
            institution_type='banking',
            created_by=self.user,
        )
        
        # Crear membership
        self.membership = FinancialInstitutionMembership.objects.create(
            user=self.user,
            institution=self.institution,
            role='admin',
            is_active=True,
        )

    def test_login_success(self):
        """Test login exitoso con credenciales válidas."""
        response = self.client.post('/api/auth/login/', {
            'email': 'test@ejemplo.com',
            'password': 'TestPassword123!',
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertIn('institution', response.data)
        self.assertEqual(response.data['user']['email'], 'test@ejemplo.com')
        self.assertEqual(response.data['role'], 'admin')
        self.assertFalse(response.data['requires_2fa'])

    def test_login_with_uppercase_email(self):
        """Test login con email en mayúsculas (debe normalizar)."""
        response = self.client.post('/api/auth/login/', {
            'email': 'TEST@EJEMPLO.COM',
            'password': 'TestPassword123!',
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['user']['email'], 'test@ejemplo.com')

    def test_login_with_invalid_credentials(self):
        """Test login con contraseña incorrecta."""
        response = self.client.post('/api/auth/login/', {
            'email': 'test@ejemplo.com',
            'password': 'WrongPassword123!',
        })
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('detail', response.data)

    def test_login_with_nonexistent_email(self):
        """Test login con email que no existe."""
        response = self.client.post('/api/auth/login/', {
            'email': 'noexiste@ejemplo.com',
            'password': 'TestPassword123!',
        })
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('detail', response.data)

    def test_login_with_empty_email(self):
        """Test login con email vacío."""
        response = self.client.post('/api/auth/login/', {
            'email': '',
            'password': 'TestPassword123!',
        })
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.data)

    def test_login_with_empty_password(self):
        """Test login con contraseña vacía."""
        response = self.client.post('/api/auth/login/', {
            'email': 'test@ejemplo.com',
            'password': '',
        })
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('password', response.data)

    def test_login_with_invalid_email_format(self):
        """Test login con formato de email inválido."""
        response = self.client.post('/api/auth/login/', {
            'email': 'correo-invalido',
            'password': 'TestPassword123!',
        })
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.data)

    def test_login_with_inactive_user(self):
        """Test login con usuario inactivo."""
        self.user.is_active = False
        self.user.save()
        
        response = self.client.post('/api/auth/login/', {
            'email': 'test@ejemplo.com',
            'password': 'TestPassword123!',
        })
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('detail', response.data)

    def test_login_response_structure(self):
        """Test que la respuesta tenga la estructura correcta."""
        response = self.client.post('/api/auth/login/', {
            'email': 'test@ejemplo.com',
            'password': 'TestPassword123!',
        })
        
        self.assertEqual(response.status_code, 200)
        
        # Verificar estructura de user
        self.assertIn('id', response.data['user'])
        self.assertIn('email', response.data['user'])
        self.assertIn('first_name', response.data['user'])
        self.assertIn('last_name', response.data['user'])
        
        # Verificar estructura de institution
        self.assertIn('id', response.data['institution'])
        self.assertIn('name', response.data['institution'])
        self.assertIn('slug', response.data['institution'])
        self.assertIn('institution_type', response.data['institution'])
        
        # Verificar que los tokens son strings largos
        self.assertGreater(len(response.data['access']), 50)
        self.assertGreater(len(response.data['refresh']), 50)
