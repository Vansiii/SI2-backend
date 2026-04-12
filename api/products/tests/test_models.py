"""
Tests para modelos de productos crediticios.
"""

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from api.products.models import CreditProduct
from api.tenants.models import FinancialInstitution


@pytest.mark.django_db
class TestCreditProductModel:
    """Tests para el modelo CreditProduct."""
    
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
    def product_data(self, institution):
        """Datos de prueba para crear un producto."""
        return {
            'institution': institution,
            'name': 'Crédito Personal',
            'description': 'Crédito personal para cualquier necesidad',
            'product_type': 'PERSONAL',
            'min_amount': Decimal('1000.00'),
            'max_amount': Decimal('50000.00'),
            'interest_rate': Decimal('12.50'),
            'interest_type': 'FIXED',
            'min_term_months': 6,
            'max_term_months': 60,
            'commission_rate': Decimal('1.00'),
            'insurance_rate': Decimal('0.50'),
            'amortization_system': 'FRENCH',
            'requires_guarantor': False,
            'auto_approval_enabled': True,
            'min_credit_score': 600,
        }
    
    def test_create_product(self, product_data):
        """Test crear un producto válido."""
        product = CreditProduct.objects.create(**product_data)
        
        assert product.id is not None
        assert product.name == 'Crédito Personal'
        assert product.product_type == 'PERSONAL'
        assert product.interest_rate == Decimal('12.50')
        assert product.is_active is True
    
    def test_product_str_representation(self, product_data):
        """Test representación en string del producto."""
        product = CreditProduct.objects.create(**product_data)
        expected = 'Crédito Personal (Personal)'
        assert str(product) == expected
    
    def test_calculate_monthly_payment(self, product_data):
        """Test cálculo de cuota mensual."""
        product = CreditProduct.objects.create(**product_data)
        
        # Calcular cuota para 10000 Bs a 12 meses
        monthly_payment = product.calculate_monthly_payment(
            Decimal('10000.00'),
            12
        )
        
        assert monthly_payment > 0
        assert isinstance(monthly_payment, Decimal)
        # La cuota debe ser mayor al monto/plazo (por los intereses)
        assert monthly_payment > Decimal('10000.00') / 12
    
    def test_calculate_total_cost(self, product_data):
        """Test cálculo de costo total."""
        product = CreditProduct.objects.create(**product_data)
        
        # Calcular costo total para 10000 Bs a 12 meses
        total_cost = product.calculate_total_cost(
            Decimal('10000.00'),
            12
        )
        
        assert total_cost > Decimal('10000.00')  # Debe ser mayor por intereses
        assert isinstance(total_cost, Decimal)
    
    def test_product_types(self, product_data):
        """Test tipos de producto válidos."""
        valid_types = [
            'PERSONAL',
            'VEHICULAR',
            'HIPOTECARIO',
            'VIVIENDA_SOCIAL',
            'PYME',
            'EMPRESARIAL',
            'AGROPECUARIO',
            'MICROEMPRESA'
        ]
        
        for product_type in valid_types:
            product_data['product_type'] = product_type
            product_data['name'] = f'Crédito {product_type}'
            product = CreditProduct.objects.create(**product_data)
            assert product.product_type == product_type
            product.delete()
    
    def test_interest_types(self, product_data):
        """Test tipos de interés válidos."""
        valid_types = ['FIXED', 'VARIABLE', 'MIXED']
        
        for interest_type in valid_types:
            product_data['interest_type'] = interest_type
            product_data['name'] = f'Crédito {interest_type}'
            product = CreditProduct.objects.create(**product_data)
            assert product.interest_type == interest_type
            product.delete()
    
    def test_amortization_systems(self, product_data):
        """Test sistemas de amortización válidos."""
        valid_systems = ['FRENCH', 'GERMAN', 'AMERICAN']
        
        for system in valid_systems:
            product_data['amortization_system'] = system
            product_data['name'] = f'Crédito {system}'
            product = CreditProduct.objects.create(**product_data)
            assert product.amortization_system == system
            product.delete()
    
    def test_min_amount_less_than_max(self, product_data):
        """Test que el monto mínimo debe ser menor al máximo."""
        product_data['min_amount'] = Decimal('60000.00')
        product_data['max_amount'] = Decimal('50000.00')
        product = CreditProduct(**product_data)
        
        with pytest.raises(ValidationError):
            product.full_clean()
    
    def test_min_term_less_than_max(self, product_data):
        """Test que el plazo mínimo debe ser menor al máximo."""
        product_data['min_term_months'] = 72
        product_data['max_term_months'] = 60
        product = CreditProduct(**product_data)
        
        with pytest.raises(ValidationError):
            product.full_clean()
    
    def test_positive_interest_rate(self, product_data):
        """Test que la tasa de interés debe ser positiva."""
        product_data['interest_rate'] = Decimal('-5.00')
        product = CreditProduct(**product_data)
        
        with pytest.raises(ValidationError):
            product.full_clean()
    
    def test_deactivate_product(self, product_data):
        """Test desactivar un producto."""
        product = CreditProduct.objects.create(**product_data)
        assert product.is_active is True
        
        product.is_active = False
        product.save()
        
        assert product.is_active is False
    
    def test_product_ordering(self, product_data, institution):
        """Test ordenamiento de productos."""
        # Crear varios productos con diferentes display_order
        CreditProduct.objects.create(
            **{**product_data, 'name': 'Producto A', 'display_order': 3}
        )
        CreditProduct.objects.create(
            **{**product_data, 'name': 'Producto B', 'display_order': 1}
        )
        CreditProduct.objects.create(
            **{**product_data, 'name': 'Producto C', 'display_order': 2}
        )
        
        products = CreditProduct.objects.all()
        
        # Verificar que están ordenados por display_order
        assert products[0].name == 'Producto B'
        assert products[1].name == 'Producto C'
        assert products[2].name == 'Producto A'
    
    def test_required_documents_json(self, product_data):
        """Test campo JSON de documentos requeridos."""
        product_data['required_documents'] = [
            'Cédula de Identidad',
            'Comprobante de ingresos',
            'Certificado de trabajo'
        ]
        product = CreditProduct.objects.create(**product_data)
        
        assert len(product.required_documents) == 3
        assert 'Cédula de Identidad' in product.required_documents
