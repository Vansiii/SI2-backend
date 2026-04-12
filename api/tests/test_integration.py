"""
Tests de integración para flujos completos del sistema.
"""

import pytest
from decimal import Decimal
from datetime import date
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from api.models import UserProfile
from api.roles.models import Role, Permission
from api.tenants.models import FinancialInstitution
from api.clients.models import Client
from api.products.models import CreditProduct
from api.saas.models import SubscriptionPlan, Subscription

User = get_user_model()


@pytest.mark.django_db
class TestClientManagementFlow:
    """Tests de integración para el flujo completo de gestión de clientes."""
    
    @pytest.fixture
    def api_client(self):
        """Cliente API de prueba."""
        return APIClient()
    
    @pytest.fixture
    def setup_institution_with_user(self):
        """Configura una institución con usuario y permisos."""
        # Crear institución
        institution = FinancialInstitution.objects.create(
            name='Banco Integración',
            slug='banco-integracion',
            country='Bolivia',
            is_active=True
        )
        
        # Crear permisos
        perm_view = Permission.objects.create(
            code='view_clients',
            name='Ver Clientes',
            module='clients'
        )
        perm_create = Permission.objects.create(
            code='create_clients',
            name='Crear Clientes',
            module='clients'
        )
        perm_update = Permission.objects.create(
            code='update_clients',
            name='Actualizar Clientes',
            module='clients'
        )
        perm_delete = Permission.objects.create(
            code='delete_clients',
            name='Eliminar Clientes',
            module='clients'
        )
        
        # Crear rol con todos los permisos
        role = Role.objects.create(
            institution=institution,
            name='Gestor de Clientes',
            description='Puede gestionar clientes'
        )
        role.permissions.add(perm_view, perm_create, perm_update, perm_delete)
        
        # Crear usuario
        user = User.objects.create_user(
            email='gestor@banco.com',
            password='gestor123',
            first_name='Gestor',
            last_name='Test'
        )
        
        profile = UserProfile.objects.create(
            user=user,
            institution=institution,
            user_type='INSTITUTION_USER'
        )
        profile.roles.add(role)
        
        return {
            'institution': institution,
            'user': user,
            'role': role
        }
    
    def test_complete_client_lifecycle(self, api_client, setup_institution_with_user):
        """Test del ciclo de vida completo de un cliente."""
        setup = setup_institution_with_user
        api_client.force_authenticate(user=setup['user'])
        
        # 1. Crear cliente
        client_data = {
            'first_name': 'Juan',
            'last_name': 'Pérez',
            'document_type': 'CI',
            'document_number': '12345678',
            'email': 'juan.perez@example.com',
            'phone': '70123456',
            'monthly_income': '5000.00',
            'address': 'Av. Principal #123'
        }
        
        response = api_client.post('/api/clients/', client_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        client_id = response.data['id']
        assert response.data['first_name'] == 'Juan'
        
        # 2. Listar clientes (debe aparecer el creado)
        response = api_client.get('/api/clients/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['id'] == client_id
        
        # 3. Obtener detalle del cliente
        response = api_client.get(f'/api/clients/{client_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == 'juan.perez@example.com'
        
        # 4. Actualizar cliente
        update_data = {
            'phone': '70999999',
            'monthly_income': '6000.00'
        }
        response = api_client.patch(f'/api/clients/{client_id}/', update_data, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['phone'] == '70999999'
        assert response.data['monthly_income'] == '6000.00'
        
        # 5. Verificar que la actualización persiste
        response = api_client.get(f'/api/clients/{client_id}/')
        assert response.data['phone'] == '70999999'
        
        # 6. Desactivar cliente
        response = api_client.delete(f'/api/clients/{client_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # 7. Verificar que el cliente está desactivado
        client = Client.objects.get(id=client_id)
        assert client.is_active is False


@pytest.mark.django_db
class TestProductManagementFlow:
    """Tests de integración para el flujo completo de gestión de productos."""
    
    @pytest.fixture
    def api_client(self):
        """Cliente API de prueba."""
        return APIClient()
    
    @pytest.fixture
    def setup_institution_with_admin(self):
        """Configura una institución con administrador."""
        institution = FinancialInstitution.objects.create(
            name='Cooperativa Test',
            slug='cooperativa-test',
            country='Bolivia',
            is_active=True
        )
        
        user = User.objects.create_user(
            email='admin@cooperativa.com',
            password='admin123',
            first_name='Admin',
            last_name='Test'
        )
        
        UserProfile.objects.create(
            user=user,
            institution=institution,
            user_type='INSTITUTION_USER'
        )
        
        return {
            'institution': institution,
            'user': user
        }
    
    def test_complete_product_lifecycle(self, api_client, setup_institution_with_admin):
        """Test del ciclo de vida completo de un producto crediticio."""
        setup = setup_institution_with_admin
        api_client.force_authenticate(user=setup['user'])
        
        # 1. Crear producto
        product_data = {
            'name': 'Crédito Personal Plus',
            'description': 'Crédito para gastos personales con mejores tasas',
            'product_type': 'PERSONAL',
            'min_amount': '1000.00',
            'max_amount': '50000.00',
            'min_term_months': 6,
            'max_term_months': 60,
            'interest_rate': '11.50',
            'interest_type': 'FIXED',
            'amortization_system': 'FRENCH',
            'requires_guarantor': False,
            'requires_collateral': False,
            'min_age': 18,
            'max_age': 70,
            'is_active': True
        }
        
        response = api_client.post('/api/products/', product_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        product_id = response.data['id']
        assert response.data['name'] == 'Crédito Personal Plus'
        
        # 2. Listar productos
        response = api_client.get('/api/products/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        
        # 3. Obtener detalle del producto
        response = api_client.get(f'/api/products/{product_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['interest_rate'] == '11.50'
        
        # 4. Actualizar producto (cambiar tasa)
        update_data = {
            'interest_rate': '10.50',
            'description': 'Crédito con tasa promocional'
        }
        response = api_client.patch(f'/api/products/{product_id}/', update_data, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['interest_rate'] == '10.50'
        
        # 5. Crear segundo producto
        product_data2 = {
            'name': 'Crédito Empresarial',
            'description': 'Para capital de trabajo',
            'product_type': 'BUSINESS',
            'min_amount': '10000.00',
            'max_amount': '200000.00',
            'min_term_months': 12,
            'max_term_months': 84,
            'interest_rate': '14.00',
            'interest_type': 'FIXED',
            'amortization_system': 'FRENCH',
            'is_active': True
        }
        
        response = api_client.post('/api/products/', product_data2, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        
        # 6. Listar productos (deben ser 2)
        response = api_client.get('/api/products/')
        assert len(response.data['results']) == 2
        
        # 7. Filtrar por tipo
        response = api_client.get('/api/products/', {'product_type': 'PERSONAL'})
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['product_type'] == 'PERSONAL'
        
        # 8. Desactivar producto
        response = api_client.delete(f'/api/products/{product_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # 9. Verificar desactivación
        product = CreditProduct.objects.get(id=product_id)
        assert product.is_active is False


@pytest.mark.django_db
class TestSubscriptionFlow:
    """Tests de integración para el flujo completo de suscripciones."""
    
    @pytest.fixture
    def api_client(self):
        """Cliente API de prueba."""
        return APIClient()
    
    @pytest.fixture
    def saas_admin(self):
        """Crea un usuario SaaS Admin."""
        user = User.objects.create_superuser(
            email='saas@platform.com',
            password='saas123',
            first_name='SaaS',
            last_name='Admin'
        )
        
        UserProfile.objects.create(
            user=user,
            user_type='SAAS_ADMIN'
        )
        
        return user
    
    def test_complete_subscription_flow(self, api_client, saas_admin):
        """Test del flujo completo de suscripción de una institución."""
        api_client.force_authenticate(user=saas_admin)
        
        # 1. Crear plan de suscripción
        plan_data = {
            'name': 'Plan Starter',
            'slug': 'plan-starter',
            'description': 'Plan inicial para instituciones pequeñas',
            'price': '299.00',
            'billing_cycle': 'MONTHLY',
            'trial_days': 30,
            'max_users': 5,
            'max_branches': 1,
            'max_products': 3,
            'max_loans_per_month': 50,
            'max_storage_gb': 5,
            'has_ai_scoring': False,
            'has_workflows': True,
            'has_reporting': True,
            'has_mobile_app': True,
            'is_active': True
        }
        
        response = api_client.post('/api/saas/plans/', plan_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        plan_id = response.data['id']
        
        # 2. Crear institución
        institution = FinancialInstitution.objects.create(
            name='Microfinanciera Test',
            slug='microfinanciera-test',
            country='Bolivia',
            is_active=True
        )
        
        # 3. Crear suscripción para la institución
        subscription_data = {
            'institution': institution.id,
            'plan': plan_id,
            'start_date': date.today().isoformat()
        }
        
        response = api_client.post('/api/saas/subscriptions/', subscription_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        subscription_id = response.data['id']
        assert response.data['status'] == 'PENDING'
        
        # 4. Activar período de prueba
        subscription = Subscription.objects.get(id=subscription_id)
        subscription.activate_trial()
        
        # 5. Verificar estado de trial
        response = api_client.get(f'/api/saas/subscriptions/{subscription_id}/')
        assert response.data['status'] == 'TRIAL'
        assert response.data['is_trial'] is True
        
        # 6. Activar suscripción (simular pago)
        activate_data = {
            'payment_method': 'Tarjeta de Crédito',
            'transaction_id': 'TXN-TEST-001'
        }
        response = api_client.post(
            f'/api/saas/subscriptions/{subscription_id}/activate/',
            activate_data,
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        
        # 7. Verificar activación
        subscription.refresh_from_db()
        assert subscription.status == 'ACTIVE'
        assert subscription.is_trial is False
        
        # 8. Verificar límites
        assert subscription.is_within_limits('users', 3) is True
        assert subscription.is_within_limits('users', 10) is False
        
        # 9. Simular uso
        subscription.current_users = 4
        subscription.current_loans_this_month = 25
        subscription.save()
        
        # 10. Verificar porcentajes de uso
        assert subscription.get_usage_percentage('users') == 80.0  # 4/5 = 80%
        assert subscription.get_usage_percentage('loans') == 50.0  # 25/50 = 50%
        
        # 11. Suspender suscripción
        suspend_data = {'reason': 'Pago vencido'}
        response = api_client.post(
            f'/api/saas/subscriptions/{subscription_id}/suspend/',
            suspend_data,
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        
        subscription.refresh_from_db()
        assert subscription.status == 'SUSPENDED'
        
        # 12. Reactivar suscripción
        response = api_client.post(
            f'/api/saas/subscriptions/{subscription_id}/activate/',
            activate_data,
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        
        subscription.refresh_from_db()
        assert subscription.status == 'ACTIVE'


@pytest.mark.django_db
class TestMultiTenantFlow:
    """Tests de integración para verificar aislamiento multi-tenant."""
    
    @pytest.fixture
    def api_client(self):
        """Cliente API de prueba."""
        return APIClient()
    
    @pytest.fixture
    def setup_two_institutions(self):
        """Configura dos instituciones con usuarios."""
        # Institución 1
        inst1 = FinancialInstitution.objects.create(
            name='Banco A',
            slug='banco-a',
            country='Bolivia',
            is_active=True
        )
        
        user1 = User.objects.create_user(
            email='user@bancoa.com',
            password='user123',
            first_name='User',
            last_name='BancoA'
        )
        
        UserProfile.objects.create(
            user=user1,
            institution=inst1,
            user_type='INSTITUTION_USER'
        )
        
        # Institución 2
        inst2 = FinancialInstitution.objects.create(
            name='Banco B',
            slug='banco-b',
            country='Bolivia',
            is_active=True
        )
        
        user2 = User.objects.create_user(
            email='user@bancob.com',
            password='user123',
            first_name='User',
            last_name='BancoB'
        )
        
        UserProfile.objects.create(
            user=user2,
            institution=inst2,
            user_type='INSTITUTION_USER'
        )
        
        return {
            'inst1': inst1,
            'user1': user1,
            'inst2': inst2,
            'user2': user2
        }
    
    def test_data_isolation_between_institutions(self, api_client, setup_two_institutions):
        """Test que verifica el aislamiento completo de datos entre instituciones."""
        setup = setup_two_institutions
        
        # Usuario 1 crea un cliente
        api_client.force_authenticate(user=setup['user1'])
        
        client_data = {
            'first_name': 'Cliente',
            'last_name': 'BancoA',
            'document_type': 'CI',
            'document_number': '11111111',
            'email': 'cliente@bancoa.com',
            'phone': '70111111',
            'monthly_income': '5000.00'
        }
        
        response = api_client.post('/api/clients/', client_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        client1_id = response.data['id']
        
        # Usuario 1 crea un producto
        product_data = {
            'name': 'Producto Banco A',
            'product_type': 'PERSONAL',
            'min_amount': '1000.00',
            'max_amount': '50000.00',
            'min_term_months': 6,
            'max_term_months': 60,
            'interest_rate': '12.00',
            'is_active': True
        }
        
        response = api_client.post('/api/products/', product_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        product1_id = response.data['id']
        
        # Usuario 2 crea un cliente
        api_client.force_authenticate(user=setup['user2'])
        
        client_data2 = {
            'first_name': 'Cliente',
            'last_name': 'BancoB',
            'document_type': 'CI',
            'document_number': '22222222',
            'email': 'cliente@bancob.com',
            'phone': '70222222',
            'monthly_income': '6000.00'
        }
        
        response = api_client.post('/api/clients/', client_data2, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        client2_id = response.data['id']
        
        # Usuario 2 crea un producto
        product_data2 = {
            'name': 'Producto Banco B',
            'product_type': 'BUSINESS',
            'min_amount': '5000.00',
            'max_amount': '100000.00',
            'min_term_months': 12,
            'max_term_months': 84,
            'interest_rate': '15.00',
            'is_active': True
        }
        
        response = api_client.post('/api/products/', product_data2, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        product2_id = response.data['id']
        
        # Verificar aislamiento: Usuario 1 solo ve sus datos
        api_client.force_authenticate(user=setup['user1'])
        
        response = api_client.get('/api/clients/')
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['id'] == client1_id
        
        response = api_client.get('/api/products/')
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['id'] == product1_id
        
        # Usuario 1 no puede acceder a datos de Usuario 2
        response = api_client.get(f'/api/clients/{client2_id}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        response = api_client.get(f'/api/products/{product2_id}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # Verificar aislamiento: Usuario 2 solo ve sus datos
        api_client.force_authenticate(user=setup['user2'])
        
        response = api_client.get('/api/clients/')
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['id'] == client2_id
        
        response = api_client.get('/api/products/')
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['id'] == product2_id
        
        # Usuario 2 no puede acceder a datos de Usuario 1
        response = api_client.get(f'/api/clients/{client1_id}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        response = api_client.get(f'/api/products/{product1_id}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestEndToEndUserJourney:
    """Tests de integración end-to-end simulando el viaje completo de un usuario."""
    
    @pytest.fixture
    def api_client(self):
        """Cliente API de prueba."""
        return APIClient()
    
    def test_institution_onboarding_to_first_client(self, api_client):
        """Test del flujo completo desde onboarding hasta primer cliente."""
        
        # 1. SaaS Admin crea un plan
        saas_admin = User.objects.create_superuser(
            email='admin@saas.com',
            password='admin123'
        )
        UserProfile.objects.create(user=saas_admin, user_type='SAAS_ADMIN')
        
        api_client.force_authenticate(user=saas_admin)
        
        plan_data = {
            'name': 'Plan Básico',
            'slug': 'plan-basico',
            'price': '500.00',
            'billing_cycle': 'MONTHLY',
            'trial_days': 30,
            'max_users': 10,
            'is_active': True
        }
        
        response = api_client.post('/api/saas/plans/', plan_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        plan_id = response.data['id']
        
        # 2. Se crea una nueva institución
        institution = FinancialInstitution.objects.create(
            name='Nueva Cooperativa',
            slug='nueva-cooperativa',
            country='Bolivia',
            is_active=True
        )
        
        # 3. Se crea suscripción para la institución
        subscription_data = {
            'institution': institution.id,
            'plan': plan_id,
            'start_date': date.today().isoformat()
        }
        
        response = api_client.post('/api/saas/subscriptions/', subscription_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        
        # Activar trial
        subscription = Subscription.objects.first()
        subscription.activate_trial()
        
        # 4. Se crea el primer usuario administrador de la institución
        admin_user = User.objects.create_user(
            email='admin@cooperativa.com',
            password='admin123',
            first_name='Admin',
            last_name='Cooperativa'
        )
        
        UserProfile.objects.create(
            user=admin_user,
            institution=institution,
            user_type='INSTITUTION_USER'
        )
        
        # 5. Admin configura su primer producto
        api_client.force_authenticate(user=admin_user)
        
        product_data = {
            'name': 'Crédito de Consumo',
            'product_type': 'PERSONAL',
            'min_amount': '500.00',
            'max_amount': '20000.00',
            'min_term_months': 3,
            'max_term_months': 36,
            'interest_rate': '18.00',
            'is_active': True
        }
        
        response = api_client.post('/api/products/', product_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        product_id = response.data['id']
        
        # 6. Admin registra su primer cliente
        client_data = {
            'first_name': 'Primer',
            'last_name': 'Cliente',
            'document_type': 'CI',
            'document_number': '99999999',
            'email': 'primer@cliente.com',
            'phone': '70999999',
            'monthly_income': '3000.00'
        }
        
        response = api_client.post('/api/clients/', client_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        client_id = response.data['id']
        
        # 7. Verificar que todo está correctamente relacionado
        client = Client.objects.get(id=client_id)
        assert client.institution == institution
        
        product = CreditProduct.objects.get(id=product_id)
        assert product.institution == institution
        
        # 8. Verificar contadores de suscripción
        subscription.refresh_from_db()
        subscription.current_users = 1
        subscription.current_products = 1
        subscription.save()
        
        assert subscription.is_within_limits('users', 1) is True
        assert subscription.is_within_limits('products', 1) is True
        
        # 9. Verificar que el admin puede ver sus datos
        response = api_client.get('/api/clients/')
        assert len(response.data['results']) == 1
        
        response = api_client.get('/api/products/')
        assert len(response.data['results']) == 1
