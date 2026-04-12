"""
Tests para modelos de suscripciones SaaS.
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from api.saas.models import SubscriptionPlan, Subscription
from api.tenants.models import FinancialInstitution


@pytest.mark.django_db
class TestSubscriptionPlanModel:
    """Tests para el modelo SubscriptionPlan."""
    
    @pytest.fixture
    def plan_data(self):
        """Datos de prueba para crear un plan."""
        return {
            'name': 'Plan Básico',
            'slug': 'plan-basico',
            'description': 'Plan ideal para instituciones pequeñas',
            'price': Decimal('500.00'),
            'billing_cycle': 'MONTHLY',
            'trial_days': 30,
            'setup_fee': Decimal('100.00'),
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
    
    def test_create_plan(self, plan_data):
        """Test crear un plan válido."""
        plan = SubscriptionPlan.objects.create(**plan_data)
        
        assert plan.id is not None
        assert plan.name == 'Plan Básico'
        assert plan.price == Decimal('500.00')
        assert plan.is_active is True
    
    def test_plan_str_representation(self, plan_data):
        """Test representación en string del plan."""
        plan = SubscriptionPlan.objects.create(**plan_data)
        expected = 'Plan Básico - Bs 500.00/Mensual'
        assert str(plan) == expected
    
    def test_get_price_per_month_monthly(self, plan_data):
        """Test precio mensual para plan mensual."""
        plan = SubscriptionPlan.objects.create(**plan_data)
        assert plan.get_price_per_month() == Decimal('500.00')
    
    def test_get_price_per_month_quarterly(self, plan_data):
        """Test precio mensual para plan trimestral."""
        plan_data['billing_cycle'] = 'QUARTERLY'
        plan_data['price'] = Decimal('1350.00')
        plan = SubscriptionPlan.objects.create(**plan_data)
        assert plan.get_price_per_month() == Decimal('450.00')
    
    def test_get_price_per_month_annual(self, plan_data):
        """Test precio mensual para plan anual."""
        plan_data['billing_cycle'] = 'ANNUAL'
        plan_data['price'] = Decimal('4800.00')
        plan = SubscriptionPlan.objects.create(**plan_data)
        assert plan.get_price_per_month() == Decimal('400.00')
    
    def test_unique_slug(self, plan_data):
        """Test que el slug debe ser único."""
        SubscriptionPlan.objects.create(**plan_data)
        
        with pytest.raises(Exception):  # IntegrityError
            SubscriptionPlan.objects.create(**plan_data)
    
    def test_positive_price(self, plan_data):
        """Test que el precio debe ser positivo."""
        plan_data['price'] = Decimal('-100.00')
        plan = SubscriptionPlan(**plan_data)
        
        with pytest.raises(ValidationError):
            plan.full_clean()
    
    def test_plan_ordering(self):
        """Test ordenamiento de planes."""
        SubscriptionPlan.objects.create(
            name='Plan C',
            slug='plan-c',
            description='Plan C',
            price=Decimal('1000.00'),
            display_order=3
        )
        SubscriptionPlan.objects.create(
            name='Plan A',
            slug='plan-a',
            description='Plan A',
            price=Decimal('500.00'),
            display_order=1
        )
        SubscriptionPlan.objects.create(
            name='Plan B',
            slug='plan-b',
            description='Plan B',
            price=Decimal('750.00'),
            display_order=2
        )
        
        plans = SubscriptionPlan.objects.all()
        
        assert plans[0].name == 'Plan A'
        assert plans[1].name == 'Plan B'
        assert plans[2].name == 'Plan C'


@pytest.mark.django_db
class TestSubscriptionModel:
    """Tests para el modelo Subscription."""
    
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
    def subscription_data(self, institution, plan):
        """Datos de prueba para crear una suscripción."""
        return {
            'institution': institution,
            'plan': plan,
            'start_date': date.today(),
        }
    
    def test_create_subscription(self, subscription_data):
        """Test crear una suscripción válida."""
        subscription = Subscription.objects.create(**subscription_data)
        
        assert subscription.id is not None
        assert subscription.status == 'TRIAL'
        assert subscription.payment_status == 'PENDING'
    
    def test_subscription_str_representation(self, subscription_data):
        """Test representación en string de la suscripción."""
        subscription = Subscription.objects.create(**subscription_data)
        expected = 'Banco Test - Plan Básico (Período de Prueba)'
        assert str(subscription) == expected
    
    def test_activate_trial(self, subscription_data, plan):
        """Test activar período de prueba."""
        subscription = Subscription.objects.create(**subscription_data)
        subscription.activate_trial()
        
        assert subscription.status == 'TRIAL'
        assert subscription.trial_end_date == date.today() + timedelta(days=plan.trial_days)
        assert subscription.next_billing_date == subscription.trial_end_date
    
    def test_activate_subscription(self, subscription_data):
        """Test activar suscripción después del trial."""
        subscription = Subscription.objects.create(**subscription_data)
        subscription.activate_trial()
        subscription.activate_subscription()
        
        assert subscription.status == 'ACTIVE'
        assert subscription.payment_status == 'PAID'
        assert subscription.next_billing_date is not None
    
    def test_suspend_subscription(self, subscription_data):
        """Test suspender suscripción."""
        subscription = Subscription.objects.create(**subscription_data)
        subscription.activate_trial()
        subscription.suspend_subscription(reason='Pago vencido')
        
        assert subscription.status == 'SUSPENDED'
        assert 'Pago vencido' in subscription.notes
    
    def test_cancel_subscription(self, subscription_data):
        """Test cancelar suscripción."""
        subscription = Subscription.objects.create(**subscription_data)
        subscription.activate_trial()
        subscription.cancel_subscription(reason='Cliente solicitó cancelación')
        
        assert subscription.status == 'CANCELLED'
        assert subscription.end_date == date.today()
        assert subscription.cancellation_reason == 'Cliente solicitó cancelación'
    
    def test_is_within_limits(self, subscription_data, plan):
        """Test verificar si está dentro de los límites."""
        subscription = Subscription.objects.create(**subscription_data)
        
        # Dentro de límites
        subscription.current_users = 5
        subscription.current_branches = 1
        subscription.current_products = 3
        subscription.current_month_loans = 50
        subscription.current_storage_gb = Decimal('5.0')
        subscription.save()
        
        assert subscription.is_within_limits() is True
        
        # Fuera de límites
        subscription.current_users = 15  # Excede max_users (10)
        subscription.save()
        
        assert subscription.is_within_limits() is False
    
    def test_get_usage_percentage(self, subscription_data):
        """Test calcular porcentaje de uso."""
        subscription = Subscription.objects.create(**subscription_data)
        
        subscription.current_users = 5  # 50% de 10
        subscription.current_branches = 1  # 100% de 1
        subscription.current_products = 2  # 40% de 5
        subscription.current_month_loans = 25  # 25% de 100
        subscription.current_storage_gb = Decimal('2.5')  # 25% de 10
        subscription.save()
        
        usage = subscription.get_usage_percentage()
        
        assert usage['users'] == 50.0
        assert usage['branches'] == 100.0
        assert usage['products'] == 40.0
        assert usage['loans'] == 25.0
        assert usage['storage'] == 25.0
    
    def test_is_trial(self, subscription_data, plan):
        """Test verificar si está en período de prueba."""
        subscription = Subscription.objects.create(**subscription_data)
        subscription.activate_trial()
        
        assert subscription.is_trial() is True
        
        # Después de activar
        subscription.activate_subscription()
        assert subscription.is_trial() is False
    
    def test_is_active_subscription(self, subscription_data):
        """Test verificar si la suscripción está activa."""
        subscription = Subscription.objects.create(**subscription_data)
        subscription.activate_trial()
        
        assert subscription.is_active_subscription() is True
        
        # Después de cancelar
        subscription.cancel_subscription()
        assert subscription.is_active_subscription() is False
    
    def test_days_until_renewal(self, subscription_data):
        """Test calcular días hasta renovación."""
        subscription = Subscription.objects.create(**subscription_data)
        subscription.activate_trial()
        
        days = subscription.days_until_renewal()
        assert days == 30  # trial_days
    
    def test_reset_monthly_counters(self, subscription_data):
        """Test resetear contadores mensuales."""
        subscription = Subscription.objects.create(**subscription_data)
        subscription.current_month_loans = 50
        subscription.save()
        
        subscription.reset_monthly_counters()
        
        assert subscription.current_month_loans == 0
    
    def test_one_subscription_per_institution(self, subscription_data, institution, plan):
        """Test que una institución solo puede tener una suscripción."""
        Subscription.objects.create(**subscription_data)
        
        # Intentar crear segunda suscripción para la misma institución
        with pytest.raises(Exception):  # IntegrityError
            Subscription.objects.create(**subscription_data)
