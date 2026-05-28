"""
Tests para API de suscripciones SaaS.
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from rest_framework import status
from rest_framework.test import APIClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from api.saas.models import SubscriptionPlan, Subscription
from api.tenants.models import FinancialInstitution
from api.models import UserProfile

User = get_user_model()


@pytest.mark.django_db
class TestSubscriptionPlanAPI:
    """Tests para la API de planes de suscripción."""
    
    @pytest.fixture
    def api_client(self):
        """Cliente API de prueba."""
        return APIClient()
    
    @pytest.fixture
    def saas_admin(self):
        """Crea un usuario SaaS Admin."""
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
    def plan_data(self):
        """Datos de prueba para crear un plan."""
        return {
            'name': 'Plan Básico',
            'slug': 'plan-basico',
            'description': 'Plan ideal para instituciones pequeñas',
            'price': '500.00',
            'billing_cycle': 'MONTHLY',
            'trial_days': 30,
            'setup_fee': '100.00',
            'max_users': 10,
            'max_branches': 1,
            'max_products': 5,
            'max_loans_per_month': 100,
            'max_storage_gb': 10,
            'has_ai_scoring': False,
            'has_workflows': False,
            'has_reporting': True,
            'has_mobile_app': True,
            'has_api_access': False,
        }
    
    def test_list_plans_public(self, api_client):
        """Test listar planes sin autenticación (público)."""
        # Crear plan activo
        SubscriptionPlan.objects.create(
            name='Plan Público',
            slug='plan-publico',
            description='Plan público',
            price=Decimal('500.00'),
            is_active=True
        )
        
        url = reverse('saas:plan-list-create')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
    
    def test_list_plans_includes_inactive_for_admin(self, api_client, saas_admin):
        """Test que admin ve planes inactivos."""
        # Crear plan activo e inactivo
        SubscriptionPlan.objects.create(
            name='Plan Activo',
            slug='plan-activo',
            description='Plan activo',
            price=Decimal('500.00'),
            is_active=True
        )
        SubscriptionPlan.objects.create(
            name='Plan Inactivo',
            slug='plan-inactivo',
            description='Plan inactivo',
            price=Decimal('500.00'),
            is_active=False
        )
        
        api_client.force_authenticate(user=saas_admin)
        
        url = reverse('saas:plan-list-create')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2
    
    def test_create_plan_unauthenticated(self, api_client, plan_data):
        """Test crear plan sin autenticación."""
        url = reverse('saas:plan-list-create')
        response = api_client.post(url, plan_data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_create_plan_as_saas_admin(self, api_client, saas_admin, plan_data):
        """Test crear plan como SaaS Admin."""
        api_client.force_authenticate(user=saas_admin)
        
        url = reverse('saas:plan-list-create')
        response = api_client.post(url, plan_data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Plan Básico'
        assert SubscriptionPlan.objects.count() == 1
    
    def test_create_plan_duplicate_slug(self, api_client, saas_admin, plan_data):
        """Test crear plan con slug duplicado."""
        # Crear primer plan
        SubscriptionPlan.objects.create(
            name='Plan Existente',
            slug='plan-basico',
            description='Plan existente',
            price=Decimal('500.00')
        )
        
        api_client.force_authenticate(user=saas_admin)
        
        url = reverse('saas:plan-list-create')
        response = api_client.post(url, plan_data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_get_plan_detail(self, api_client):
        """Test obtener detalle de un plan."""
        plan = SubscriptionPlan.objects.create(
            name='Plan Test',
            slug='plan-test',
            description='Plan de prueba',
            price=Decimal('500.00'),
            is_active=True
        )
        
        url = reverse('saas:plan-detail', kwargs={'id': plan.id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == plan.id
        assert response.data['name'] == 'Plan Test'
    
    def test_update_plan(self, api_client, saas_admin):
        """Test actualizar un plan."""
        plan = SubscriptionPlan.objects.create(
            name='Plan Test',
            slug='plan-test',
            description='Plan de prueba',
            price=Decimal('500.00')
        )
        
        api_client.force_authenticate(user=saas_admin)
        
        url = reverse('saas:plan-detail', kwargs={'id': plan.id})
        update_data = {
            'price': '600.00',
            'description': 'Nueva descripción'
        }
        response = api_client.patch(url, update_data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['price'] == '600.00'
        
        plan.refresh_from_db()
        assert plan.price == Decimal('600.00')
    
    def test_deactivate_plan(self, api_client, saas_admin):
        """Test desactivar un plan."""
        plan = SubscriptionPlan.objects.create(
            name='Plan Test',
            slug='plan-test',
            description='Plan de prueba',
            price=Decimal('500.00'),
            is_active=True
        )
        
        api_client.force_authenticate(user=saas_admin)
        
        url = reverse('saas:plan-detail', kwargs={'id': plan.id})
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        plan.refresh_from_db()
        assert plan.is_active is False


@pytest.mark.django_db
class TestSubscriptionAPI:
    """Tests para la API de suscripciones."""
    
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
    def plan(self):
        """Crea un plan de prueba."""
        return SubscriptionPlan.objects.create(
            name='Plan Básico',
            slug='plan-basico',
            description='Plan básico',
            price=Decimal('500.00'),
            billing_cycle='MONTHLY',
            trial_days=30,
            max_users=10,
            max_branches=1,
            max_products=5,
            max_loans_per_month=100,
            max_storage_gb=10
        )
    
    @pytest.fixture
    def saas_admin(self):
        """Crea un usuario SaaS Admin."""
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
    def institution_user(self, institution):
        """Crea un usuario de institución."""
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
    
    def test_list_subscriptions_unauthenticated(self, api_client):
        """Test listar suscripciones sin autenticación."""
        url = reverse('saas:subscription-list-create')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_list_subscriptions_as_saas_admin(self, api_client, saas_admin, institution, plan):
        """Test listar suscripciones como SaaS Admin."""
        # Crear suscripción
        Subscription.objects.create(
            institution=institution,
            plan=plan,
            start_date=date.today()
        )
        
        api_client.force_authenticate(user=saas_admin)
        
        url = reverse('saas:subscription-list-create')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
    
    def test_create_subscription(self, api_client, saas_admin, institution, plan):
        """Test crear suscripción."""
        api_client.force_authenticate(user=saas_admin)
        
        url = reverse('saas:subscription-list-create')
        data = {
            'institution': institution.id,
            'plan': plan.id,
            'start_date': date.today().isoformat()
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert Subscription.objects.count() == 1
    
    def test_create_subscription_duplicate_institution(self, api_client, saas_admin, institution, plan):
        """Test crear suscripción duplicada para misma institución."""
        # Crear primera suscripción
        subscription = Subscription.objects.create(
            institution=institution,
            plan=plan,
            start_date=date.today()
        )
        subscription.activate_trial()
        
        api_client.force_authenticate(user=saas_admin)
        
        # Intentar crear segunda
        url = reverse('saas:subscription-list-create')
        data = {
            'institution': institution.id,
            'plan': plan.id,
            'start_date': date.today().isoformat()
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_get_subscription_detail(self, api_client, saas_admin, institution, plan):
        """Test obtener detalle de suscripción."""
        subscription = Subscription.objects.create(
            institution=institution,
            plan=plan,
            start_date=date.today()
        )
        
        api_client.force_authenticate(user=saas_admin)
        
        url = reverse('saas:subscription-detail', kwargs={'id': subscription.id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == subscription.id
    
    def test_activate_subscription(self, api_client, saas_admin, institution, plan):
        """Test activar suscripción."""
        subscription = Subscription.objects.create(
            institution=institution,
            plan=plan,
            start_date=date.today()
        )
        subscription.activate_trial()
        
        api_client.force_authenticate(user=saas_admin)
        
        url = reverse('saas:subscription-activate', kwargs={'id': subscription.id})
        data = {
            'payment_method': 'Transferencia',
            'transaction_id': 'TXN-123'
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        subscription.refresh_from_db()
        assert subscription.status == 'ACTIVE'
    
    def test_suspend_subscription(self, api_client, saas_admin, institution, plan):
        """Test suspender suscripción."""
        subscription = Subscription.objects.create(
            institution=institution,
            plan=plan,
            start_date=date.today()
        )
        subscription.activate_trial()
        
        api_client.force_authenticate(user=saas_admin)
        
        url = reverse('saas:subscription-suspend', kwargs={'id': subscription.id})
        data = {'reason': 'Pago vencido'}
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        subscription.refresh_from_db()
        assert subscription.status == 'SUSPENDED'
    
    def test_cancel_subscription(self, api_client, saas_admin, institution, plan):
        """Test cancelar suscripción."""
        subscription = Subscription.objects.create(
            institution=institution,
            plan=plan,
            start_date=date.today()
        )
        subscription.activate_trial()
        
        api_client.force_authenticate(user=saas_admin)
        
        url = reverse('saas:subscription-cancel', kwargs={'id': subscription.id})
        data = {'reason': 'Cliente solicitó cancelación'}
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        subscription.refresh_from_db()
        assert subscription.status == 'CANCELLED'
    
    def test_get_my_subscription(self, api_client, institution_user, institution, plan):
        """Test obtener mi suscripción como usuario de institución."""
        subscription = Subscription.objects.create(
            institution=institution,
            plan=plan,
            start_date=date.today()
        )
        subscription.activate_trial()
        
        api_client.force_authenticate(user=institution_user)
        
        url = reverse('saas:my-subscription')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == subscription.id
