"""
Tests para API de productos crediticios.
"""

import pytest
from decimal import Decimal
from rest_framework import status
from rest_framework.test import APIClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from api.products.models import CreditProduct
from api.tenants.models import FinancialInstitution
from api.models import UserProfile

User = get_user_model()


@pytest.mark.django_db
class TestProductAPI:
    """Tests para la API de productos crediticios."""
    
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
    def institution2(self):
        """Crea una segunda institución de prueba."""
        return FinancialInstitution.objects.create(
            name='Banco Test 2',
            slug='banco-test-2',
            country='Bolivia',
            is_active=True
        )
    
    @pytest.fixture
    def admin_user(self, institution):
        """Crea un usuario administrador de institución."""
        user = User.objects.create_user(
            email='admin@banco.com',
            password='adminpass123',
            first_name='Admin',
            last_name='Test'
        )
        
        UserProfile.objects.create(
            user=user,
            institution=institution,
            user_type='INSTITUTION_USER'
        )
        
        return user
    
    @pytest.fixture
    def user_institution2(self, institution2):
        """Crea un usuario de la segunda institución."""
        user = User.objects.create_user(
            email='user@banco2.com',
            password='userpass123',
            first_name='User',
            last_name='Test2'
        )
        
        UserProfile.objects.create(
            user=user,
            institution=institution2,
            user_type='INSTITUTION_USER'
        )
        
        return user
    
    @pytest.fixture
    def product_data(self):
        """Datos de prueba para crear un producto."""
        return {
            'name': 'Crédito Personal',
            'description': 'Crédito para gastos personales',
            'product_type': 'PERSONAL',
            'min_amount': '1000.00',
            'max_amount': '50000.00',
            'min_term_months': 6,
            'max_term_months': 60,
            'interest_rate': '12.50',
            'interest_type': 'FIXED',
            'amortization_system': 'FRENCH',
            'requires_guarantor': False,
            'requires_collateral': False,
            'min_age': 18,
            'max_age': 70,
            'required_documents': ['CI', 'Comprobante de ingresos'],
            'is_active': True
        }
    
    def test_list_products_unauthenticated(self, api_client):
        """Test listar productos sin autenticación."""
        url = reverse('products:product-list-create')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_list_products_authenticated(self, api_client, admin_user, institution):
        """Test listar productos autenticado."""
        # Crear productos
        CreditProduct.objects.create(
            institution=institution,
            name='Producto 1',
            product_type='PERSONAL',
            min_amount=Decimal('1000.00'),
            max_amount=Decimal('50000.00'),
            min_term_months=6,
            max_term_months=60,
            interest_rate=Decimal('12.50')
        )
        CreditProduct.objects.create(
            institution=institution,
            name='Producto 2',
            product_type='BUSINESS',
            min_amount=Decimal('5000.00'),
            max_amount=Decimal('100000.00'),
            min_term_months=12,
            max_term_months=84,
            interest_rate=Decimal('15.00')
        )
        
        api_client.force_authenticate(user=admin_user)
        
        url = reverse('products:product-list-create')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2
    
    def test_list_products_multi_tenancy(self, api_client, admin_user, user_institution2, institution, institution2):
        """Test que cada institución solo ve sus productos."""
        # Crear productos para institución 1
        CreditProduct.objects.create(
            institution=institution,
            name='Producto Banco 1',
            product_type='PERSONAL',
            min_amount=Decimal('1000.00'),
            max_amount=Decimal('50000.00'),
            min_term_months=6,
            max_term_months=60,
            interest_rate=Decimal('12.50')
        )
        
        # Crear productos para institución 2
        CreditProduct.objects.create(
            institution=institution2,
            name='Producto Banco 2',
            product_type='BUSINESS',
            min_amount=Decimal('5000.00'),
            max_amount=Decimal('100000.00'),
            min_term_months=12,
            max_term_months=84,
            interest_rate=Decimal('15.00')
        )
        
        # Usuario de institución 1 solo ve sus productos
        api_client.force_authenticate(user=admin_user)
        url = reverse('products:product-list-create')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['name'] == 'Producto Banco 1'
        
        # Usuario de institución 2 solo ve sus productos
        api_client.force_authenticate(user=user_institution2)
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['name'] == 'Producto Banco 2'
    
    def test_create_product(self, api_client, admin_user, product_data):
        """Test crear producto."""
        api_client.force_authenticate(user=admin_user)
        
        url = reverse('products:product-list-create')
        response = api_client.post(url, product_data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Crédito Personal'
        assert CreditProduct.objects.count() == 1
    
    def test_create_product_invalid_amounts(self, api_client, admin_user, product_data):
        """Test crear producto con montos inválidos."""
        product_data['min_amount'] = '60000.00'  # Mayor que max_amount
        
        api_client.force_authenticate(user=admin_user)
        
        url = reverse('products:product-list-create')
        response = api_client.post(url, product_data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_create_product_invalid_terms(self, api_client, admin_user, product_data):
        """Test crear producto con plazos inválidos."""
        product_data['min_term_months'] = 72  # Mayor que max_term_months
        
        api_client.force_authenticate(user=admin_user)
        
        url = reverse('products:product-list-create')
        response = api_client.post(url, product_data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_create_product_negative_interest_rate(self, api_client, admin_user, product_data):
        """Test crear producto con tasa de interés negativa."""
        product_data['interest_rate'] = '-5.00'
        
        api_client.force_authenticate(user=admin_user)
        
        url = reverse('products:product-list-create')
        response = api_client.post(url, product_data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_get_product_detail(self, api_client, admin_user, institution):
        """Test obtener detalle de un producto."""
        product = CreditProduct.objects.create(
            institution=institution,
            name='Crédito Test',
            product_type='PERSONAL',
            min_amount=Decimal('1000.00'),
            max_amount=Decimal('50000.00'),
            min_term_months=6,
            max_term_months=60,
            interest_rate=Decimal('12.50')
        )
        
        api_client.force_authenticate(user=admin_user)
        
        url = reverse('products:product-detail', kwargs={'id': product.id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == product.id
        assert response.data['name'] == 'Crédito Test'
    
    def test_get_product_detail_other_institution(self, api_client, user_institution2, institution):
        """Test que un usuario no puede ver productos de otra institución."""
        product = CreditProduct.objects.create(
            institution=institution,
            name='Crédito Test',
            product_type='PERSONAL',
            min_amount=Decimal('1000.00'),
            max_amount=Decimal('50000.00'),
            min_term_months=6,
            max_term_months=60,
            interest_rate=Decimal('12.50')
        )
        
        api_client.force_authenticate(user=user_institution2)
        
        url = reverse('products:product-detail', kwargs={'id': product.id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_update_product(self, api_client, admin_user, institution):
        """Test actualizar un producto."""
        product = CreditProduct.objects.create(
            institution=institution,
            name='Crédito Test',
            product_type='PERSONAL',
            min_amount=Decimal('1000.00'),
            max_amount=Decimal('50000.00'),
            min_term_months=6,
            max_term_months=60,
            interest_rate=Decimal('12.50')
        )
        
        api_client.force_authenticate(user=admin_user)
        
        url = reverse('products:product-detail', kwargs={'id': product.id})
        update_data = {
            'interest_rate': '13.00',
            'description': 'Nueva descripción'
        }
        response = api_client.patch(url, update_data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['interest_rate'] == '13.00'
        
        product.refresh_from_db()
        assert product.interest_rate == Decimal('13.00')
    
    def test_deactivate_product(self, api_client, admin_user, institution):
        """Test desactivar un producto."""
        product = CreditProduct.objects.create(
            institution=institution,
            name='Crédito Test',
            product_type='PERSONAL',
            min_amount=Decimal('1000.00'),
            max_amount=Decimal('50000.00'),
            min_term_months=6,
            max_term_months=60,
            interest_rate=Decimal('12.50'),
            is_active=True
        )
        
        api_client.force_authenticate(user=admin_user)
        
        url = reverse('products:product-detail', kwargs={'id': product.id})
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        product.refresh_from_db()
        assert product.is_active is False
    
    def test_pagination(self, api_client, admin_user, institution):
        """Test paginación de productos."""
        # Crear 15 productos
        for i in range(15):
            CreditProduct.objects.create(
                institution=institution,
                name=f'Producto {i+1}',
                product_type='PERSONAL',
                min_amount=Decimal('1000.00'),
                max_amount=Decimal('50000.00'),
                min_term_months=6,
                max_term_months=60,
                interest_rate=Decimal('12.50')
            )
        
        api_client.force_authenticate(user=admin_user)
        
        url = reverse('products:product-list-create')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 10  # Página 1: 10 items
        assert response.data['count'] == 15
        
        # Página 2
        response = api_client.get(url, {'page': 2})
        assert len(response.data['results']) == 5  # Página 2: 5 items restantes
    
    def test_filter_by_product_type(self, api_client, admin_user, institution):
        """Test filtrar productos por tipo."""
        CreditProduct.objects.create(
            institution=institution,
            name='Crédito Personal',
            product_type='PERSONAL',
            min_amount=Decimal('1000.00'),
            max_amount=Decimal('50000.00'),
            min_term_months=6,
            max_term_months=60,
            interest_rate=Decimal('12.50')
        )
        CreditProduct.objects.create(
            institution=institution,
            name='Crédito Empresarial',
            product_type='BUSINESS',
            min_amount=Decimal('5000.00'),
            max_amount=Decimal('100000.00'),
            min_term_months=12,
            max_term_months=84,
            interest_rate=Decimal('15.00')
        )
        
        api_client.force_authenticate(user=admin_user)
        
        url = reverse('products:product-list-create')
        response = api_client.get(url, {'product_type': 'PERSONAL'})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['product_type'] == 'PERSONAL'
    
    def test_filter_by_active_status(self, api_client, admin_user, institution):
        """Test filtrar productos por estado activo."""
        CreditProduct.objects.create(
            institution=institution,
            name='Producto Activo',
            product_type='PERSONAL',
            min_amount=Decimal('1000.00'),
            max_amount=Decimal('50000.00'),
            min_term_months=6,
            max_term_months=60,
            interest_rate=Decimal('12.50'),
            is_active=True
        )
        CreditProduct.objects.create(
            institution=institution,
            name='Producto Inactivo',
            product_type='BUSINESS',
            min_amount=Decimal('5000.00'),
            max_amount=Decimal('100000.00'),
            min_term_months=12,
            max_term_months=84,
            interest_rate=Decimal('15.00'),
            is_active=False
        )
        
        api_client.force_authenticate(user=admin_user)
        
        url = reverse('products:product-list-create')
        response = api_client.get(url, {'is_active': 'true'})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['is_active'] is True
    
    def test_calculate_monthly_payment_endpoint(self, api_client, admin_user, institution):
        """Test endpoint de cálculo de cuota mensual."""
        product = CreditProduct.objects.create(
            institution=institution,
            name='Crédito Test',
            product_type='PERSONAL',
            min_amount=Decimal('1000.00'),
            max_amount=Decimal('50000.00'),
            min_term_months=6,
            max_term_months=60,
            interest_rate=Decimal('12.00'),
            amortization_system='FRENCH'
        )
        
        api_client.force_authenticate(user=admin_user)
        
        url = reverse('products:product-calculate-payment', kwargs={'id': product.id})
        data = {
            'amount': '10000.00',
            'term_months': 12
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'monthly_payment' in response.data
        assert 'total_cost' in response.data
        assert Decimal(response.data['monthly_payment']) > 0



