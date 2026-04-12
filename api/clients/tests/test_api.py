"""
Tests completos para API de clientes.
Incluye tests de permisos, validaciones y multi-tenancy.
"""

import pytest
from decimal import Decimal
from datetime import date
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import override_settings
from api.clients.models import Client, ClientDocument
from api.tenants.models import FinancialInstitution, FinancialInstitutionMembership
from api.users.models import UserProfile
from api.roles.models import Role, Permission, UserRole

User = get_user_model()


class TenantAPITestCase:
    """Base class for API tests that need tenant context."""
    
    def setup_api_client_with_tenant(self, user, institution):
        """Setup API client with proper tenant context."""
        from rest_framework_simplejwt.tokens import RefreshToken
        from django.test import Client
        import json
        
        # Generate JWT token for the user
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        
        # Use Django's test client which goes through middleware
        client = Client()
        
        # Create a wrapper that converts to DRF-style responses and adds JWT auth
        class MiddlewareAPIClient:
            def __init__(self, django_client, token):
                self.client = django_client
                self.token = token
            
            def _get_auth_headers(self):
                return {'HTTP_AUTHORIZATION': f'Bearer {self.token}'}
            
            def get(self, path, data=None, **extra):
                extra.update(self._get_auth_headers())
                response = self.client.get(path, data, **extra)
                return self._convert_response(response)
            
            def post(self, path, data=None, format='json', **extra):
                extra.update(self._get_auth_headers())
                if format == 'json' and data:
                    extra['content_type'] = 'application/json'
                    data = json.dumps(data)
                response = self.client.post(path, data, **extra)
                return self._convert_response(response)
            
            def patch(self, path, data=None, format='json', **extra):
                extra.update(self._get_auth_headers())
                if format == 'json' and data:
                    extra['content_type'] = 'application/json'
                    data = json.dumps(data)
                response = self.client.patch(path, data, **extra)
                return self._convert_response(response)
            
            def delete(self, path, **extra):
                extra.update(self._get_auth_headers())
                response = self.client.delete(path, **extra)
                return self._convert_response(response)
            
            def _convert_response(self, response):
                # Convert Django response to DRF-style response
                if hasattr(response, 'json') and response.get('content-type', '').startswith('application/json'):
                    try:
                        response.data = response.json()
                    except:
                        response.data = {}
                else:
                    response.data = {}
                return response
        
        return MiddlewareAPIClient(client, access_token)


@pytest.mark.django_db
class TestClientAPIAuthentication(TenantAPITestCase):
    """Tests de autenticación y autorización."""
    
    @pytest.fixture
    def api_client(self):
        return APIClient()
    
    @pytest.fixture
    def institution(self):
        return FinancialInstitution.objects.create(
            name='Banco Test Auth',
            slug='banco-test-auth',
            
            is_active=True
        )
    
    def test_list_clients_unauthenticated(self, api_client):
        """Test listar clientes sin autenticación debe fallar."""
        url = '/api/clients/'
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_create_client_unauthenticated(self, api_client):
        """Test crear cliente sin autenticación debe fallar."""
        url = '/api/clients/'
        response = api_client.post(url, {}, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestClientAPIPermissions(TenantAPITestCase):
    """Tests de permisos."""
    
    @pytest.fixture
    def api_client(self):
        return APIClient()
    
    @pytest.fixture
    def institution(self):
        return FinancialInstitution.objects.create(
            name='Banco Test Perms',
            slug='banco-test-perms',
            
            is_active=True
        )
    
    @pytest.fixture
    def user_without_permissions(self, institution):
        """Usuario sin permisos de clientes."""
        user = User.objects.create_user(
            username='noperm_perms@example.com',
            email='noperm_perms@example.com',
            password='testpass123',
            first_name='No',
            last_name='Perms'
        )
        # El UserProfile se crea automáticamente por signal
        user.profile.user_type = 'tenant_user'
        user.profile.save()
        return user
    
    @pytest.fixture
    def user_with_view_only(self, institution):
        """Usuario solo con permiso de ver."""
        user = User.objects.create_user(
            username='viewonly_perms@example.com',
            email='viewonly_perms@example.com',
            password='testpass123',
            first_name='View',
            last_name='Only'
        )
        # El UserProfile se crea automáticamente por signal
        user.profile.user_type = 'tenant_user'
        user.profile.save()
        
        # Crear membership (requerido por tenant middleware)
        FinancialInstitutionMembership.objects.create(
            user=user,
            institution=institution,
            is_active=True
        )
        
        role = Role.objects.create(name='Viewer Perms', institution=institution)
        perm, created = Permission.objects.get_or_create(
            code='clients.view',
            defaults={
                'name': 'Ver Clientes',
                'description': 'Permiso para ver clientes'
            }
        )
        role.permissions.add(perm)
        
        # Crear UserRole para asociar usuario con institución y rol
        UserRole.objects.create(
            user=user,
            role=role,
            institution=institution
        )
        return user
    
    @pytest.fixture
    def user_with_all_permissions(self, institution):
        """Usuario con todos los permisos."""
        user = User.objects.create_user(
            username='admin_perms@example.com',
            email='admin_perms@example.com',
            password='testpass123',
            first_name='Admin',
            last_name='User'
        )
        # El UserProfile se crea automáticamente por signal
        user.profile.user_type = 'tenant_user'
        user.profile.save()
        
        # Crear membership (requerido por tenant middleware)
        FinancialInstitutionMembership.objects.create(
            user=user,
            institution=institution,
            is_active=True
        )
        
        role = Role.objects.create(name='Admin Perms', institution=institution)
        
        permissions = []
        for p in ['view', 'create', 'edit', 'delete']:
            perm, created = Permission.objects.get_or_create(
                code=f'clients.{p}',
                defaults={
                    'name': f'{p.title()}',
                    'description': f'{p.title()}'
                }
            )
            permissions.append(perm)
        role.permissions.set(permissions)
        
        # Crear UserRole para asociar usuario con institución y rol
        UserRole.objects.create(
            user=user,
            role=role,
            institution=institution
        )
        return user
    
    def test_list_without_view_permission(self, api_client, user_without_permissions, institution):
        """Test listar sin permiso de ver debe fallar."""
        api_client = self.setup_api_client_with_tenant(user_without_permissions, institution)
        response = api_client.get('/api/clients/')
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_create_without_create_permission(self, api_client, user_with_view_only, institution):
        """Test crear sin permiso de crear debe fallar."""
        api_client = self.setup_api_client_with_tenant(user_with_view_only, institution)
        response = api_client.post('/api/clients/', {}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestClientAPIMultiTenancy(TenantAPITestCase):
    """Tests de aislamiento multi-tenant."""
    
    @pytest.fixture
    def api_client(self):
        return APIClient()
    
    @pytest.fixture
    def institution1(self):
        return FinancialInstitution.objects.create(
            name='Banco 1 MT',
            slug='banco-1-mt',
            
            is_active=True
        )
    
    @pytest.fixture
    def institution2(self):
        return FinancialInstitution.objects.create(
            name='Banco 2 MT',
            slug='banco-2-mt',
            
            is_active=True
        )
    
    @pytest.fixture
    def user_institution1(self, institution1):
        user = User.objects.create_user(
            username='user1_mt@example.com',
            email='user1_mt@example.com',
            password='testpass123',
            first_name='User',
            last_name='One'
        )
        # El UserProfile se crea automáticamente por signal
        user.profile.user_type = 'tenant_user'
        user.profile.save()
        
        # Crear membership (requerido por tenant middleware)
        FinancialInstitutionMembership.objects.create(
            user=user,
            institution=institution1,
            is_active=True
        )
        
        role = Role.objects.create(name='Admin MT1', institution=institution1)
        permissions = []
        for p in ['view', 'create', 'edit', 'delete']:
            perm, created = Permission.objects.get_or_create(
                code=f'clients.{p}',
                defaults={
                    'name': f'{p.title()} MT1',
                    'description': f'{p.title()} MT1'
                }
            )
            permissions.append(perm)
        role.permissions.set(permissions)
        
        # Crear UserRole para asociar usuario con institución y rol
        UserRole.objects.create(
            user=user,
            role=role,
            institution=institution1
        )
        return user
    
    @pytest.fixture
    def user_institution2(self, institution2):
        user = User.objects.create_user(
            username='user2_mt@example.com',
            email='user2_mt@example.com',
            password='testpass123',
            first_name='User',
            last_name='Two'
        )
        # El UserProfile se crea automáticamente por signal
        user.profile.user_type = 'tenant_user'
        user.profile.save()
        
        # Crear membership (requerido por tenant middleware)
        FinancialInstitutionMembership.objects.create(
            user=user,
            institution=institution2,
            is_active=True
        )
        
        role = Role.objects.create(name='Admin MT2', institution=institution2)
        permissions = []
        for p in ['view', 'create', 'edit', 'delete']:
            perm, created = Permission.objects.get_or_create(
                code=f'clients.{p}',
                defaults={
                    'name': f'{p.title()} MT2',
                    'description': f'{p.title()} MT2'
                }
            )
            permissions.append(perm)
        role.permissions.set(permissions)
        
        # Crear UserRole para asociar usuario con institución y rol
        UserRole.objects.create(
            user=user,
            role=role,
            institution=institution2
        )
        return user
    
    def test_user_cannot_see_other_institution_clients(
        self, api_client, user_institution1, user_institution2, institution1, institution2
    ):
        """Test que un usuario no puede ver clientes de otra institución."""
        # Crear cliente en institución 1
        Client.objects.create(
            institution=institution1,
            client_type='NATURAL',
            first_name='Cliente',
            last_name='Uno',
            document_type='CI',
            document_number='11111111',
            birth_date=date(1990, 1, 1),
            phone='70123456',
            address='Dirección 1',
            city='La Paz',
            department='La Paz',
            employment_status='EMPLOYED',
            monthly_income=Decimal('5000.00'),
        )
        
        # Crear cliente en institución 2
        Client.objects.create(
            institution=institution2,
            client_type='NATURAL',
            first_name='Cliente',
            last_name='Dos',
            document_type='CI',
            document_number='22222222',
            birth_date=date(1990, 1, 1),
            phone='70123456',
            address='Dirección 2',
            city='Santa Cruz',
            department='Santa Cruz',
            employment_status='EMPLOYED',
            monthly_income=Decimal('5000.00'),
        )
        
        # Usuario 1 solo debe ver su cliente
        api_client = self.setup_api_client_with_tenant(user_institution1, institution1)
        response = api_client.get('/api/clients/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert 'Uno' in response.data['results'][0]['full_name']
        
        # Usuario 2 solo debe ver su cliente
        api_client = self.setup_api_client_with_tenant(user_institution2, institution2)
        response = api_client.get('/api/clients/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert 'Dos' in response.data['results'][0]['full_name']
    
    def test_same_document_different_institutions(
        self, api_client, user_institution1, user_institution2, institution1, institution2
    ):
        """Test que el mismo documento puede existir en diferentes instituciones."""
        client_data = {
            'client_type': 'NATURAL',
            'first_name': 'Juan',
            'last_name': 'Pérez',
            'document_type': 'CI',
            'document_number': '12345678',
            'birth_date': '1990-01-15',
            'phone': '70123456',
            'address': 'Av. Principal 123',
            'city': 'La Paz',
            'department': 'La Paz',
            'employment_status': 'EMPLOYED',
            'monthly_income': '5000.00',
        }
        
        # Crear en institución 1
        api_client = self.setup_api_client_with_tenant(user_institution1, institution1)
        response1 = api_client.post('/api/clients/', client_data, format='json')
        assert response1.status_code == status.HTTP_201_CREATED
        
        # Crear en institución 2 con mismo documento
        api_client = self.setup_api_client_with_tenant(user_institution2, institution2)
        response2 = api_client.post('/api/clients/', client_data, format='json')
        assert response2.status_code == status.HTTP_201_CREATED
        
        # Verificar que ambos existen
        assert Client.objects.filter(document_number='12345678').count() == 2


@pytest.mark.django_db
class TestClientAPICRUD(TenantAPITestCase):
    """Tests de operaciones CRUD."""
    
    @pytest.fixture
    def api_client(self):
        return APIClient()
    
    @pytest.fixture
    def institution(self):
        return FinancialInstitution.objects.create(
            name='Banco Test CRUD',
            slug='banco-test-crud',
            
            is_active=True
        )
    
    @pytest.fixture
    def user(self, institution):
        user = User.objects.create_user(
            username='crud_test@example.com',
            email='crud_test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        # El UserProfile se crea automáticamente por signal
        user.profile.user_type = 'tenant_user'
        user.profile.save()
        
        # Crear membership (requerido por tenant middleware)
        FinancialInstitutionMembership.objects.create(
            user=user,
            institution=institution,
            is_active=True
        )
        
        role = Role.objects.create(name='Admin CRUD', institution=institution)
        permissions = []
        for p in ['view', 'create', 'edit', 'delete']:
            perm, created = Permission.objects.get_or_create(
                code=f'clients.{p}',
                defaults={
                    'name': f'{p.title()} CRUD',
                    'description': f'{p.title()} CRUD'
                }
            )
            permissions.append(perm)
        role.permissions.set(permissions)
        
        # Crear UserRole para asociar usuario con institución y rol
        UserRole.objects.create(
            user=user,
            role=role,
            institution=institution
        )
        return user
    
    @pytest.fixture
    def client_data(self):
        return {
            'client_type': 'NATURAL',
            'first_name': 'Juan',
            'last_name': 'Pérez',
            'document_type': 'CI',
            'document_number': '12345678',
            'document_extension': 'LP',
            'birth_date': '1990-01-15',
            'gender': 'M',
            'email': 'juan.perez@example.com',
            'phone': '+591 70123456',
            'mobile_phone': '+591 71234567',
            'address': 'Av. Principal 123',
            'city': 'La Paz',
            'department': 'La Paz',
            'country': 'Bolivia',
            'postal_code': '0000',
            'employment_status': 'EMPLOYED',
            'employer_name': 'Empresa ABC',
            'employer_nit': '1234567890',
            'job_title': 'Ingeniero',
            'monthly_income': '5000.00',
            'additional_income': '500.00',
        }
    
    def test_create_client_success(self, user, client_data, institution):
        """Test crear cliente exitosamente."""
        api_client = self.setup_api_client_with_tenant(user, institution)
        response = api_client.post('/api/clients/', client_data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['success'] is True
        assert response.data['client']['first_name'] == 'Juan'
        assert response.data['client']['last_name'] == 'Pérez'
        assert response.data['client']['document_number'] == '12345678'
        assert Client.objects.count() == 1
    
    def test_create_client_duplicate_document(self, api_client, user, client_data, institution):
        """Test crear cliente con documento duplicado debe fallar."""
        # Crear primer cliente
        Client.objects.create(
            institution=institution,
            client_type='NATURAL',
            first_name='Existing',
            last_name='Client',
            document_type='CI',
            document_number='12345678',
            birth_date=date(1990, 1, 15),
            phone='70123456',
            address='Address',
            city='La Paz',
            department='La Paz',
            employment_status='EMPLOYED',
            monthly_income=Decimal('5000.00'),
        )
        
        # Intentar crear segundo con mismo documento
        api_client = self.setup_api_client_with_tenant(user, institution)
        response = api_client.post('/api/clients/', client_data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['success'] is False
    
    def test_list_clients(self, api_client, user, institution):
        """Test listar clientes."""
        # Crear varios clientes
        for i in range(5):
            Client.objects.create(
                institution=institution,
                client_type='NATURAL',
                first_name=f'Cliente{i}',
                last_name='Test',
                document_type='CI',
                document_number=f'1234567{i}',
                birth_date=date(1990, 1, 1),
                phone='70123456',
                address='Address',
                city='La Paz',
                department='La Paz',
                employment_status='EMPLOYED',
                monthly_income=Decimal('5000.00'),
            )
        
        api_client = self.setup_api_client_with_tenant(user, institution)
        response = api_client.get('/api/clients/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 5
        assert len(response.data['results']) == 5
    
    def test_get_client_detail(self, api_client, user, institution):
        """Test obtener detalle de cliente."""
        client = Client.objects.create(
            institution=institution,
            client_type='NATURAL',
            first_name='Juan',
            last_name='Pérez',
            document_type='CI',
            document_number='12345678',
            birth_date=date(1990, 1, 15),
            phone='70123456',
            address='Address',
            city='La Paz',
            department='La Paz',
            employment_status='EMPLOYED',
            monthly_income=Decimal('5000.00'),
        )
        
        api_client = self.setup_api_client_with_tenant(user, institution)
        response = api_client.get(f'/api/clients/{client.id}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['client']['id'] == client.id
        assert response.data['client']['first_name'] == 'Juan'
    
    def test_update_client(self, api_client, user, institution):
        """Test actualizar cliente."""
        client = Client.objects.create(
            institution=institution,
            client_type='NATURAL',
            first_name='Juan',
            last_name='Pérez',
            document_type='CI',
            document_number='12345678',
            birth_date=date(1990, 1, 15),
            phone='70123456',
            address='Old Address',
            city='La Paz',
            department='La Paz',
            employment_status='EMPLOYED',
            monthly_income=Decimal('5000.00'),
        )
        
        api_client = self.setup_api_client_with_tenant(user, institution)
        update_data = {
            'phone': '+591 70999999',
            'address': 'New Address 456',
            'monthly_income': '6000.00',
        }
        response = api_client.patch(f'/api/clients/{client.id}/', update_data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['client']['phone'] == '+591 70999999'
        assert response.data['client']['address'] == 'New Address 456'
        
        # Verificar en BD
        client.refresh_from_db()
        assert client.phone == '+591 70999999'
        assert client.address == 'New Address 456'
    
    def test_deactivate_client(self, api_client, user, institution):
        """Test desactivar cliente."""
        client = Client.objects.create(
            institution=institution,
            client_type='NATURAL',
            first_name='Juan',
            last_name='Pérez',
            document_type='CI',
            document_number='12345678',
            birth_date=date(1990, 1, 15),
            phone='70123456',
            address='Address',
            city='La Paz',
            department='La Paz',
            employment_status='EMPLOYED',
            monthly_income=Decimal('5000.00'),
        )
        
        api_client = self.setup_api_client_with_tenant(user, institution)
        response = api_client.delete(f'/api/clients/{client.id}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        
        # Verificar que está desactivado
        client.refresh_from_db()
        assert client.is_active is False


@pytest.mark.django_db
class TestClientAPIValidations(TenantAPITestCase):
    """Tests de validaciones."""
    
    @pytest.fixture
    def api_client(self):
        return APIClient()
    
    @pytest.fixture
    def institution(self):
        return FinancialInstitution.objects.create(
            name='Banco Test Validations',
            slug='banco-test-validations',
            
            is_active=True
        )
    
    @pytest.fixture
    def user(self, institution):
        user = User.objects.create_user(
            username='validations_test@example.com',
            email='validations_test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        # El UserProfile se crea automáticamente por signal
        user.profile.user_type = 'tenant_user'
        user.profile.save()
        
        # Crear membership (requerido por tenant middleware)
        FinancialInstitutionMembership.objects.create(
            user=user,
            institution=institution,
            is_active=True
        )
        
        role = Role.objects.create(name='Admin Validations', institution=institution)
        permissions = []
        for p in ['view', 'create', 'edit', 'delete']:
            perm, created = Permission.objects.get_or_create(
                code=f'clients.{p}',
                defaults={
                    'name': f'{p.title()} VAL',
                    'description': f'{p.title()} VAL'
                }
            )
            permissions.append(perm)
        role.permissions.set(permissions)
        
        # Crear UserRole para asociar usuario con institución y rol
        UserRole.objects.create(
            user=user,
            role=role,
            institution=institution
        )
        return user
    
    def test_create_client_missing_required_fields(self, api_client, user, institution):
        """Test crear cliente sin campos requeridos debe fallar."""
        api_client = self.setup_api_client_with_tenant(user, institution)
        response = api_client.post('/api/clients/', {}, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['success'] is False
    
    def test_create_client_invalid_email(self, api_client, user, institution):
        """Test crear cliente con email inválido debe fallar."""
        api_client = self.setup_api_client_with_tenant(user, institution)
        data = {
            'first_name': 'Juan',
            'last_name': 'Pérez',
            'document_type': 'CI',
            'document_number': '12345678',
            'birth_date': '1990-01-15',
            'email': 'invalid-email',  # Email inválido
            'phone': '70123456',
            'address': 'Address',
            'city': 'La Paz',
            'department': 'La Paz',
            'employment_status': 'EMPLOYED',
            'monthly_income': '5000.00',
        }
        response = api_client.post('/api/clients/', data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_create_client_negative_income(self, api_client, user, institution):
        """Test crear cliente con ingreso negativo debe fallar."""
        api_client = self.setup_api_client_with_tenant(user, institution)
        data = {
            'first_name': 'Juan',
            'last_name': 'Pérez',
            'document_type': 'CI',
            'document_number': '12345678',
            'birth_date': '1990-01-15',
            'phone': '70123456',
            'address': 'Address',
            'city': 'La Paz',
            'department': 'La Paz',
            'employment_status': 'EMPLOYED',
            'monthly_income': '-1000.00',  # Ingreso negativo
        }
        response = api_client.post('/api/clients/', data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_create_client_underage(self, api_client, user, institution):
        """Test crear cliente menor de 18 años debe fallar."""
        api_client = self.setup_api_client_with_tenant(user, institution)
        data = {
            'first_name': 'Juan',
            'last_name': 'Pérez',
            'document_type': 'CI',
            'document_number': '12345678',
            'birth_date': '2015-01-15',  # Menor de edad
            'phone': '70123456',
            'address': 'Address',
            'city': 'La Paz',
            'department': 'La Paz',
            'employment_status': 'EMPLOYED',
            'monthly_income': '5000.00',
        }
        response = api_client.post('/api/clients/', data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestClientAPIFilters(TenantAPITestCase):
    """Tests de filtros y búsqueda."""
    
    @pytest.fixture
    def api_client(self):
        return APIClient()
    
    @pytest.fixture
    def institution(self):
        return FinancialInstitution.objects.create(
            name='Banco Test Filters',
            slug='banco-test-filters',
            
            is_active=True
        )
    
    @pytest.fixture
    def user(self, institution):
        user = User.objects.create_user(
            username='filters_test@example.com',
            email='filters_test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        # El UserProfile se crea automáticamente por signal
        user.profile.user_type = 'tenant_user'
        user.profile.save()
        
        # Crear membership (requerido por tenant middleware)
        FinancialInstitutionMembership.objects.create(
            user=user,
            institution=institution,
            is_active=True
        )
        
        role = Role.objects.create(name='Admin Filters', institution=institution)
        perm, created = Permission.objects.get_or_create(
            code='clients.view',
            defaults={
                'name': 'Ver Filters',
                'description': 'Ver Filters'
            }
        )
        role.permissions.add(perm)
        
        # Crear UserRole para asociar usuario con institución y rol
        UserRole.objects.create(
            user=user,
            role=role,
            institution=institution
        )
        return user
    
    @pytest.fixture
    def clients(self, institution):
        """Crea varios clientes de prueba."""
        clients = []
        for i in range(10):
            client = Client.objects.create(
                institution=institution,
                client_type='NATURAL',
                first_name=f'Cliente{i}',
                last_name='Test',
                document_type='CI',
                document_number=f'1234567{i}',
                birth_date=date(1990, 1, 1),
                phone='70123456',
                address='Address',
                city='La Paz',
                department='La Paz',
                employment_status='EMPLOYED',
                monthly_income=Decimal('5000.00'),
                is_active=(i % 2 == 0),  # Alternar activo/inactivo
                kyc_status='VERIFIED' if i < 5 else 'PENDING',
            )
            clients.append(client)
        return clients
    
    def test_filter_by_active_status(self, api_client, user, clients, institution):
        """Test filtrar por estado activo."""
        api_client = self.setup_api_client_with_tenant(user, institution)
        
        # Filtrar activos
        response = api_client.get('/api/clients/', {'is_active': 'true'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 5
        
        # Filtrar inactivos
        response = api_client.get('/api/clients/', {'is_active': 'false'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 5
    
    def test_filter_by_kyc_status(self, api_client, user, clients, institution):
        """Test filtrar por estado KYC."""
        api_client = self.setup_api_client_with_tenant(user, institution)
        
        # Filtrar verificados
        response = api_client.get('/api/clients/', {'kyc_status': 'VERIFIED'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 5
        
        # Filtrar pendientes
        response = api_client.get('/api/clients/', {'kyc_status': 'PENDING'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 5
    
    def test_search_by_name(self, api_client, user, clients, institution):
        """Test búsqueda por nombre."""
        api_client = self.setup_api_client_with_tenant(user, institution)
        
        response = api_client.get('/api/clients/', {'search': 'Cliente5'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert 'Cliente5' in response.data['results'][0]['full_name']
    
    def test_pagination(self, api_client, user, clients, institution):
        """Test paginación."""
        api_client = self.setup_api_client_with_tenant(user, institution)
        
        # Primera página (default 20 items)
        response = api_client.get('/api/clients/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 10
        assert len(response.data['results']) == 10
        
        # Cambiar tamaño de página
        response = api_client.get('/api/clients/', {'page_size': 5})
        assert len(response.data['results']) == 5
        assert response.data['next'] is not None
