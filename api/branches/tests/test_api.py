"""
Tests para API de gestión de sucursales.
"""

import json

import pytest
from django.contrib.auth import get_user_model
from django.test import Client as DjangoClient
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from api.branches.models import Branch
from api.roles.models import Role, UserRole
from api.saas.models import Subscription, SubscriptionPlan
from api.tenants.models import FinancialInstitution, FinancialInstitutionMembership

User = get_user_model()


class MiddlewareAPIClient:
    """Wrapper para usar Django Client con JWT y conservar middleware de tenant."""

    def __init__(self, user):
        refresh = RefreshToken.for_user(user)
        self.token = str(refresh.access_token)
        self.client = DjangoClient()

    def _auth_headers(self):
        return {'HTTP_AUTHORIZATION': f'Bearer {self.token}'}

    @staticmethod
    def _convert_response(response):
        if hasattr(response, 'json') and response.get('content-type', '').startswith('application/json'):
            try:
                response.data = response.json()
            except Exception:
                response.data = {}
        else:
            response.data = {}
        return response

    def get(self, path, data=None, **extra):
        extra.update(self._auth_headers())
        response = self.client.get(path, data, **extra)
        return self._convert_response(response)

    def post(self, path, data=None, format='json', **extra):
        extra.update(self._auth_headers())
        payload = data
        if format == 'json' and data is not None:
            extra['content_type'] = 'application/json'
            payload = json.dumps(data)
        response = self.client.post(path, payload, **extra)
        return self._convert_response(response)

    def put(self, path, data=None, format='json', **extra):
        extra.update(self._auth_headers())
        payload = data
        if format == 'json' and data is not None:
            extra['content_type'] = 'application/json'
            payload = json.dumps(data)
        response = self.client.put(path, payload, **extra)
        return self._convert_response(response)

    def delete(self, path, **extra):
        extra.update(self._auth_headers())
        response = self.client.delete(path, **extra)
        return self._convert_response(response)


@pytest.mark.django_db
class TestBranchAPI:
    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def plan(self):
        return SubscriptionPlan.objects.create(
            name='Plan Branch Test',
            slug='plan-branch-test',
            description='Plan para pruebas de sucursales',
            price='100.00',
            max_users=10,
            max_branches=2,
            max_products=10,
            max_loans_per_month=100,
            max_storage_gb=10,
            is_active=True,
        )

    @pytest.fixture
    def institution(self):
        return FinancialInstitution.objects.create(
            name='Banco Uno',
            slug='banco-uno',
            institution_type='banking',
            is_active=True,
        )

    @pytest.fixture
    def institution_two(self):
        return FinancialInstitution.objects.create(
            name='Banco Dos',
            slug='banco-dos',
            institution_type='banking',
            is_active=True,
        )

    @pytest.fixture
    def subscription(self, institution, plan):
        return Subscription.objects.create(
            institution=institution,
            plan=plan,
            status='ACTIVE',
            start_date='2026-01-01',
            current_users=1,
            current_branches=0,
            current_products=0,
            current_month_loans=0,
            current_storage_gb='0.00',
        )

    @pytest.fixture
    def subscription_two(self, institution_two, plan):
        return Subscription.objects.create(
            institution=institution_two,
            plan=plan,
            status='ACTIVE',
            start_date='2026-01-01',
            current_users=1,
            current_branches=0,
            current_products=0,
            current_month_loans=0,
            current_storage_gb='0.00',
        )

    @pytest.fixture
    def admin_user(self, institution):
        user = User.objects.create_user(
            username='admin.branch@example.com',
            email='admin.branch@example.com',
            password='testpass123',
            first_name='Admin',
            last_name='Branch',
        )
        user.profile.user_type = 'tenant_user'
        user.profile.save()

        FinancialInstitutionMembership.objects.create(
            user=user,
            institution=institution,
            is_active=True,
        )

        admin_role = Role.objects.create(
            name='Administrador de Institución',
            institution=institution,
            is_active=True,
        )
        UserRole.objects.create(
            user=user,
            role=admin_role,
            institution=institution,
            is_active=True,
        )
        return user

    @pytest.fixture
    def analyst_user(self, institution):
        user = User.objects.create_user(
            username='analyst.branch@example.com',
            email='analyst.branch@example.com',
            password='testpass123',
            first_name='Analyst',
            last_name='Branch',
        )
        user.profile.user_type = 'tenant_user'
        user.profile.save()

        FinancialInstitutionMembership.objects.create(
            user=user,
            institution=institution,
            is_active=True,
        )

        analyst_role = Role.objects.create(
            name='Analista de Créditos',
            institution=institution,
            is_active=True,
        )
        UserRole.objects.create(
            user=user,
            role=analyst_role,
            institution=institution,
            is_active=True,
        )
        return user

    @pytest.fixture
    def admin_user_two(self, institution_two):
        user = User.objects.create_user(
            username='admin.branch.two@example.com',
            email='admin.branch.two@example.com',
            password='testpass123',
            first_name='Admin',
            last_name='Two',
        )
        user.profile.user_type = 'tenant_user'
        user.profile.save()

        FinancialInstitutionMembership.objects.create(
            user=user,
            institution=institution_two,
            is_active=True,
        )

        admin_role = Role.objects.create(
            name='Administrador de Institución',
            institution=institution_two,
            is_active=True,
        )
        UserRole.objects.create(
            user=user,
            role=admin_role,
            institution=institution_two,
            is_active=True,
        )
        return user

    def test_list_branches_unauthenticated_returns_401(self, api_client):
        response = api_client.get('/api/branches/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_admin_can_create_branch(self, admin_user, subscription):
        client = MiddlewareAPIClient(admin_user)

        payload = {
            'name': 'Sucursal Central',
            'address': 'Av. Principal 123',
            'city': 'La Paz',
            'is_active': True,
        }

        response = client.post('/api/branches/', payload)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['success'] is True
        assert response.data['branch']['name'] == 'Sucursal Central'

        subscription.refresh_from_db()
        assert subscription.current_branches == 1
        assert Branch.objects.filter(institution=subscription.institution).count() == 1

    def test_admin_can_update_branch(self, admin_user, institution, subscription):
        branch = Branch.objects.create(
            institution=institution,
            name='Sucursal Norte',
            address='Av. Norte 100',
            city='Cochabamba',
            is_active=True,
        )
        subscription.current_branches = 1
        subscription.save(update_fields=['current_branches'])

        client = MiddlewareAPIClient(admin_user)
        payload = {
            'name': 'Sucursal Norte Renovada',
            'address': 'Av. Norte 200',
            'city': 'Cochabamba',
            'is_active': True,
        }

        response = client.put(f'/api/branches/{branch.id}/', payload)

        assert response.status_code == status.HTTP_200_OK
        branch.refresh_from_db()
        assert branch.name == 'Sucursal Norte Renovada'

    def test_admin_can_soft_delete_branch(self, admin_user, institution, subscription):
        branch = Branch.objects.create(
            institution=institution,
            name='Sucursal Sur',
            address='Av. Sur 50',
            city='Santa Cruz',
            is_active=True,
        )
        subscription.current_branches = 1
        subscription.save(update_fields=['current_branches'])

        client = MiddlewareAPIClient(admin_user)
        response = client.delete(f'/api/branches/{branch.id}/')

        assert response.status_code == status.HTTP_200_OK
        branch.refresh_from_db()
        assert branch.is_active is False

        subscription.refresh_from_db()
        assert subscription.current_branches == 0

    def test_non_admin_cannot_manage_branches(self, analyst_user):
        client = MiddlewareAPIClient(analyst_user)
        payload = {
            'name': 'Sucursal Prohibida',
            'address': 'Calle 1',
            'city': 'La Paz',
        }

        response = client.post('/api/branches/', payload)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data['success'] is False

    def test_multi_tenant_isolation(self, admin_user, admin_user_two, institution_two):
        foreign_branch = Branch.objects.create(
            institution=institution_two,
            name='Sucursal Externa',
            address='Calle Externa 123',
            city='Tarija',
            is_active=True,
        )

        client_one = MiddlewareAPIClient(admin_user)
        list_response = client_one.get('/api/branches/')

        assert list_response.status_code == status.HTTP_200_OK
        assert list_response.data['count'] == 0

        detail_response = client_one.put(
            f'/api/branches/{foreign_branch.id}/',
            {
                'name': 'Intento no permitido',
                'address': 'X',
                'city': 'X',
                'is_active': True,
            },
        )

        assert detail_response.status_code == status.HTTP_404_NOT_FOUND

        client_two = MiddlewareAPIClient(admin_user_two)
        own_response = client_two.get('/api/branches/')
        assert own_response.status_code == status.HTTP_200_OK
        assert own_response.data['count'] == 1

    def test_subscription_limit_blocks_branch_creation(self, admin_user, subscription):
        subscription.current_branches = subscription.plan.max_branches
        subscription.save(update_fields=['current_branches'])

        client = MiddlewareAPIClient(admin_user)
        payload = {
            'name': 'Sucursal Límite',
            'address': 'Calle Límite',
            'city': 'Oruro',
            'is_active': True,
        }

        response = client.post('/api/branches/', payload)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['success'] is False
        assert 'subscription' in response.data['errors']

    def test_filter_branches_by_active_status(self, admin_user, institution, subscription):
        Branch.objects.create(
            institution=institution,
            name='Sucursal Activa',
            address='A',
            city='La Paz',
            is_active=True,
        )
        Branch.objects.create(
            institution=institution,
            name='Sucursal Inactiva',
            address='B',
            city='La Paz',
            is_active=False,
        )
        subscription.current_branches = 1
        subscription.save(update_fields=['current_branches'])

        client = MiddlewareAPIClient(admin_user)

        active_response = client.get('/api/branches/?is_active=true')
        inactive_response = client.get('/api/branches/?is_active=false')

        assert active_response.status_code == status.HTTP_200_OK
        assert inactive_response.status_code == status.HTTP_200_OK
        assert active_response.data['count'] == 1
        assert inactive_response.data['count'] == 1
