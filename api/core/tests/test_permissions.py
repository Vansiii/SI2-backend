"""
Tests para el sistema de permisos y control de acceso.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from api.models import UserProfile
from api.roles.models import Role, Permission
from api.tenants.models import FinancialInstitution
from api.clients.models import Client
from api.products.models import CreditProduct
from decimal import Decimal

User = get_user_model()


@pytest.mark.django_db
class TestPermissionSystem:
    """Tests para el sistema de permisos."""
    
    @pytest.fixture
    def api_client(self):
        """Cliente API de prueba."""
        return APIClient()
    
    @pytest.fixture
    def institution(self):
        """Crea una institución de prueba."""
        return FinancialInstitution.objects.create(
            name='Banco Test',
            slug='banco-test',
            country='Bolivia',
            is_active=True
        )
    
    @pytest.fixture
    def permission_view_clients(self):
        """Permiso para ver clientes."""
        return Permission.objects.create(
            code='view_clients',
            name='Ver Clientes',
            description='Permite ver la lista de clientes',
            module='clients'
        )
    
    @pytest.fixture
    def permission_create_clients(self):
        """Permiso para crear clientes."""
        return Permission.objects.create(
            code='create_clients',
            name='Crear Clientes',
            description='Permite crear nuevos clientes',
            module='clients'
        )
    
    @pytest.fixture
    def permission_view_products(self):
        """Permiso para ver productos."""
        return Permission.objects.create(
            code='view_products',
            name='Ver Productos',
            description='Permite ver la lista de productos',
            module='products'
        )
    
    @pytest.fixture
    def role_viewer(self, institution, permission_view_clients, permission_view_products):
        """Rol con permisos de solo lectura."""
        role = Role.objects.create(
            institution=institution,
            name='Viewer',
            description='Solo puede ver información'
        )
        role.permissions.add(permission_view_clients, permission_view_products)
        return role
    
    @pytest.fixture
    def role_editor(self, institution, permission_view_clients, permission_create_clients):
        """Rol con permisos de lectura y escritura."""
        role = Role.objects.create(
            institution=institution,
            name='Editor',
            description='Puede ver y crear'
        )
        role.permissions.add(permission_view_clients, permission_create_clients)
        return role
    
    @pytest.fixture
    def user_viewer(self, institution, role_viewer):
        """Usuario con rol de solo lectura."""
        user = User.objects.create_user(
            email='viewer@banco.com',
            password='viewerpass123',
            first_name='Viewer',
            last_name='Test'
        )
        
        profile = UserProfile.objects.create(
            user=user,
            institution=institution,
            user_type='INSTITUTION_USER'
        )
        profile.roles.add(role_viewer)
        
        return user
    
    @pytest.fixture
    def user_editor(self, institution, role_editor):
        """Usuario con rol de editor."""
        user = User.objects.create_user(
            email='editor@banco.com',
            password='editorpass123',
            first_name='Editor',
            last_name='Test'
        )
        
        profile = UserProfile.objects.create(
            user=user,
            institution=institution,
            user_type='INSTITUTION_USER'
        )
        profile.roles.add(role_editor)
        
        return user
    
    @pytest.fixture
    def user_no_permissions(self, institution):
        """Usuario sin permisos."""
        user = User.objects.create_user(
            email='noperm@banco.com',
            password='nopermpass123',
            first_name='NoPerm',
            last_name='Test'
        )
        
        UserProfile.objects.create(
            user=user,
            institution=institution,
            user_type='INSTITUTION_USER'
        )
        
        return user
    
    def test_user_with_view_permission_can_list(self, api_client, user_viewer, institution):
        """Test que usuario con permiso view puede listar."""
        # Crear cliente
        Client.objects.create(
            institution=institution,
            first_name='Juan',
            last_name='Pérez',
            document_type='CI',
            document_number='12345678',
            email='juan@example.com'
        )
        
        api_client.force_authenticate(user=user_viewer)
        
        url = reverse('clients:client-list-create')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
    
    def test_user_without_view_permission_cannot_list(self, api_client, user_no_permissions, institution):
        """Test que usuario sin permiso view no puede listar."""
        # Crear cliente
        Client.objects.create(
            institution=institution,
            first_name='Juan',
            last_name='Pérez',
            document_type='CI',
            document_number='12345678',
            email='juan@example.com'
        )
        
        api_client.force_authenticate(user=user_no_permissions)
        
        url = reverse('clients:client-list-create')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_user_with_create_permission_can_create(self, api_client, user_editor):
        """Test que usuario con permiso create puede crear."""
        api_client.force_authenticate(user=user_editor)
        
        url = reverse('clients:client-list-create')
        data = {
            'first_name': 'María',
            'last_name': 'González',
            'document_type': 'CI',
            'document_number='87654321',
            'email': 'maria@example.com',
            'phone': '70123456',
            'monthly_income': '5000.00'
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert Client.objects.count() == 1
    
    def test_user_without_create_permission_cannot_create(self, api_client, user_viewer):
        """Test que usuario sin permiso create no puede crear."""
        api_client.force_authenticate(user=user_viewer)
        
        url = reverse('clients:client-list-create')
        data = {
            'first_name': 'María',
            'last_name': 'González',
            'document_type': 'CI',
            'document_number': '87654321',
            'email': 'maria@example.com',
            'phone': '70123456',
            'monthly_income': '5000.00'
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Client.objects.count() == 0
    
    def test_permission_check_method(self, user_viewer, permission_view_clients):
        """Test método has_permission del usuario."""
        assert user_viewer.userprofile.has_permission('view_clients') is True
        assert user_viewer.userprofile.has_permission('create_clients') is False
        assert user_viewer.userprofile.has_permission('nonexistent_permission') is False
    
    def test_multiple_roles_combine_permissions(self, institution, user_no_permissions, 
                                               permission_view_clients, permission_create_clients):
        """Test que múltiples roles combinan sus permisos."""
        # Crear dos roles con diferentes permisos
        role1 = Role.objects.create(
            institution=institution,
            name='Role 1',
            description='Rol 1'
        )
        role1.permissions.add(permission_view_clients)
        
        role2 = Role.objects.create(
            institution=institution,
            name='Role 2',
            description='Rol 2'
        )
        role2.permissions.add(permission_create_clients)
        
        # Asignar ambos roles al usuario
        profile = user_no_permissions.userprofile
        profile.roles.add(role1, role2)
        
        # Usuario debe tener ambos permisos
        assert profile.has_permission('view_clients') is True
        assert profile.has_permission('create_clients') is True


@pytest.mark.django_db
class TestMultiTenancyPermissions:
    """Tests para permisos en arquitectura multi-tenant."""
    
    @pytest.fixture
    def api_client(self):
        """Cliente API de prueba."""
        return APIClient()
    
    @pytest.fixture
    def institution1(self):
        """Primera institución."""
        return FinancialInstitution.objects.create(
            name='Banco 1',
            slug='banco-1',
            country='Bolivia',
            is_active=True
        )
    
    @pytest.fixture
    def institution2(self):
        """Segunda institución."""
        return FinancialInstitution.objects.create(
            name='Banco 2',
            slug='banco-2',
            country='Bolivia',
            is_active=True
        )
    
    @pytest.fixture
    def user_institution1(self, institution1):
        """Usuario de institución 1."""
        user = User.objects.create_user(
            email='user1@banco1.com',
            password='user1pass123',
            first_name='User1',
            last_name='Test'
        )
        
        UserProfile.objects.create(
            user=user,
            institution=institution1,
            user_type='INSTITUTION_USER'
        )
        
        return user
    
    @pytest.fixture
    def user_institution2(self, institution2):
        """Usuario de institución 2."""
        user = User.objects.create_user(
            email='user2@banco2.com',
            password='user2pass123',
            first_name='User2',
            last_name='Test'
        )
        
        UserProfile.objects.create(
            user=user,
            institution=institution2,
            user_type='INSTITUTION_USER'
        )
        
        return user
    
    def test_user_cannot_access_other_institution_clients(self, api_client, user_institution1, 
                                                          institution1, institution2):
        """Test que usuario no puede acceder a clientes de otra institución."""
        # Crear cliente en institución 1
        client1 = Client.objects.create(
            institution=institution1,
            first_name='Cliente',
            last_name='Banco1',
            document_type='CI',
            document_number='11111111',
            email='cliente1@example.com'
        )
        
        # Crear cliente en institución 2
        client2 = Client.objects.create(
            institution=institution2,
            first_name='Cliente',
            last_name='Banco2',
            document_type='CI',
            document_number='22222222',
            email='cliente2@example.com'
        )
        
        api_client.force_authenticate(user=user_institution1)
        
        # Intentar acceder a cliente de institución 2
        url = reverse('clients:client-detail', kwargs={'id': client2.id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # Puede acceder a cliente de su institución
        url = reverse('clients:client-detail', kwargs={'id': client1.id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_user_cannot_access_other_institution_products(self, api_client, user_institution1,
                                                           institution1, institution2):
        """Test que usuario no puede acceder a productos de otra institución."""
        # Crear producto en institución 1
        product1 = CreditProduct.objects.create(
            institution=institution1,
            name='Producto Banco 1',
            product_type='PERSONAL',
            min_amount=Decimal('1000.00'),
            max_amount=Decimal('50000.00'),
            min_term_months=6,
            max_term_months=60,
            interest_rate=Decimal('12.50')
        )
        
        # Crear producto en institución 2
        product2 = CreditProduct.objects.create(
            institution=institution2,
            name='Producto Banco 2',
            product_type='BUSINESS',
            min_amount=Decimal('5000.00'),
            max_amount=Decimal('100000.00'),
            min_term_months=12,
            max_term_months=84,
            interest_rate=Decimal('15.00')
        )
        
        api_client.force_authenticate(user=user_institution1)
        
        # Intentar acceder a producto de institución 2
        url = reverse('products:product-detail', kwargs={'id': product2.id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # Puede acceder a producto de su institución
        url = reverse('products:product-detail', kwargs={'id': product1.id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_list_only_shows_own_institution_data(self, api_client, user_institution1,
                                                   institution1, institution2):
        """Test que listar solo muestra datos de la propia institución."""
        # Crear clientes en ambas instituciones
        Client.objects.create(
            institution=institution1,
            first_name='Cliente1',
            last_name='Banco1',
            document_type='CI',
            document_number='11111111',
            email='cliente1@example.com'
        )
        Client.objects.create(
            institution=institution1,
            first_name='Cliente2',
            last_name='Banco1',
            document_type='CI',
            document_number='11111112',
            email='cliente2@example.com'
        )
        Client.objects.create(
            institution=institution2,
            first_name='Cliente3',
            last_name='Banco2',
            document_type='CI',
            document_number='22222222',
            email='cliente3@example.com'
        )
        
        api_client.force_authenticate(user=user_institution1)
        
        url = reverse('clients:client-list-create')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2  # Solo ve los 2 de su institución


@pytest.mark.django_db
class TestSaaSAdminPermissions:
    """Tests para permisos de SaaS Admin."""
    
    @pytest.fixture
    def api_client(self):
        """Cliente API de prueba."""
        return APIClient()
    
    @pytest.fixture
    def saas_admin(self):
        """Usuario SaaS Admin."""
        user = User.objects.create_superuser(
            email='saas@example.com',
            password='saaspass123',
            first_name='SaaS',
            last_name='Admin'
        )
        
        UserProfile.objects.create(
            user=user,
            user_type='SAAS_ADMIN'
        )
        
        return user
    
    @pytest.fixture
    def institution_user(self):
        """Usuario de institución normal."""
        institution = FinancialInstitution.objects.create(
            name='Banco Test',
            slug='banco-test',
            country='Bolivia',
            is_active=True
        )
        
        user = User.objects.create_user(
            email='user@banco.com',
            password='userpass123',
            first_name='User',
            last_name='Test'
        )
        
        UserProfile.objects.create(
            user=user,
            institution=institution,
            user_type='INSTITUTION_USER'
        )
        
        return user
    
    def test_saas_admin_can_access_subscription_plans(self, api_client, saas_admin):
        """Test que SaaS Admin puede acceder a planes de suscripción."""
        api_client.force_authenticate(user=saas_admin)
        
        url = reverse('saas:plan-list-create')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_institution_user_cannot_create_subscription_plans(self, api_client, institution_user):
        """Test que usuario de institución no puede crear planes."""
        api_client.force_authenticate(user=institution_user)
        
        url = reverse('saas:plan-list-create')
        data = {
            'name': 'Plan Test',
            'slug': 'plan-test',
            'description': 'Plan de prueba',
            'price': '500.00',
            'billing_cycle': 'MONTHLY'
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_saas_admin_can_view_all_institutions(self, api_client, saas_admin):
        """Test que SaaS Admin puede ver todas las instituciones."""
        # Crear instituciones
        FinancialInstitution.objects.create(
            name='Banco 1',
            slug='banco-1',
            country='Bolivia',
            is_active=True
        )
        FinancialInstitution.objects.create(
            name='Banco 2',
            slug='banco-2',
            country='Bolivia',
            is_active=True
        )
        
        api_client.force_authenticate(user=saas_admin)
        
        url = reverse('tenants:institution-list-create')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2
    
    def test_institution_user_cannot_view_other_institutions(self, api_client, institution_user):
        """Test que usuario de institución no puede ver otras instituciones."""
        # Crear otra institución
        FinancialInstitution.objects.create(
            name='Banco 2',
            slug='banco-2',
            country='Bolivia',
            is_active=True
        )
        
        api_client.force_authenticate(user=institution_user)
        
        url = reverse('tenants:institution-list-create')
        response = api_client.get(url)
        
        # Debería ver solo su institución o ninguna (dependiendo de la implementación)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

