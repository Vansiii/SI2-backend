"""
Servicios de negocio para gestión de productos crediticios.
"""

from dataclasses import dataclass
from typing import Optional
from decimal import Decimal

from django.db import transaction
from django.contrib.auth import get_user_model

from api.products.models import CreditProduct, ProductRequirement
from api.models import FinancialInstitution
from api.saas.services import (
    CheckSubscriptionLimitsService,
    CheckSubscriptionLimitsInput,
    UpdateUsageCountersService,
    UpdateUsageCountersInput
)

User = get_user_model()


@dataclass
class CreateProductInput:
    """Input para crear un producto crediticio."""
    name: str
    code: str
    product_type: str
    description: str
    min_amount: Decimal
    max_amount: Decimal
    min_term_months: int
    max_term_months: int
    interest_rate: Decimal
    interest_type: str = 'FIXED'
    commission_rate: Decimal = Decimal('0')
    insurance_rate: Decimal = Decimal('0')
    payment_frequency: str = 'MONTHLY'
    amortization_system: str = 'FRENCH'
    min_income_required: Optional[Decimal] = None
    max_debt_to_income_ratio: Decimal = Decimal('40.00')
    min_employment_months: int = 6
    requires_guarantor: bool = False
    requires_collateral: bool = False
    is_active: bool = True


@dataclass
class CreateProductResult:
    """Resultado de crear un producto."""
    success: bool
    product: Optional[CreditProduct]
    message: str
    errors: Optional[dict] = None


class ProductManagementService:
    """
    Servicio para gestión de productos crediticios.
    """
    
    @transaction.atomic
    def create_product(
        self,
        institution_id: int,
        input_data: CreateProductInput,
        created_by: Optional[User] = None
    ) -> CreateProductResult:
        """
        Crea un nuevo producto crediticio.
        
        Args:
            institution_id: ID de la institución financiera
            input_data: Datos del producto
            created_by: Usuario que crea el producto
            
        Returns:
            CreateProductResult con el resultado de la operación
        """
        try:
            # Obtener la institución
            try:
                institution = FinancialInstitution.objects.get(id=institution_id)
            except FinancialInstitution.DoesNotExist:
                return CreateProductResult(
                    success=False,
                    product=None,
                    message='Institución no encontrada',
                    errors={'institution': 'Institución inválida'}
                )
            
            # Verificar límites de suscripción antes de crear el producto
            limits_service = CheckSubscriptionLimitsService()
            limits_result = limits_service.execute(CheckSubscriptionLimitsInput(
                institution=institution,
                action='add_product'
            ))
            
            if not limits_result.allowed:
                return CreateProductResult(
                    success=False,
                    product=None,
                    message=limits_result.message,
                    errors={'subscription': 'Límite de productos alcanzado'}
                )
            
            # Verificar si ya existe un producto con ese código
            existing = CreditProduct.objects.filter(code=input_data.code).first()
            
            if existing:
                return CreateProductResult(
                    success=False,
                    product=None,
                    message='Ya existe un producto con ese código',
                    errors={'code': 'Código duplicado'}
                )
            
            # Validar montos
            if input_data.min_amount >= input_data.max_amount:
                return CreateProductResult(
                    success=False,
                    product=None,
                    message='El monto mínimo debe ser menor al monto máximo',
                    errors={'min_amount': 'Monto inválido'}
                )
            
            # Validar plazos
            if input_data.min_term_months >= input_data.max_term_months:
                return CreateProductResult(
                    success=False,
                    product=None,
                    message='El plazo mínimo debe ser menor al plazo máximo',
                    errors={'min_term_months': 'Plazo inválido'}
                )
            
            # Crear el producto
            product = CreditProduct.objects.create(
                institution_id=institution_id,
                name=input_data.name,
                code=input_data.code,
                product_type=input_data.product_type,
                description=input_data.description,
                min_amount=input_data.min_amount,
                max_amount=input_data.max_amount,
                min_term_months=input_data.min_term_months,
                max_term_months=input_data.max_term_months,
                interest_rate=input_data.interest_rate,
                interest_type=input_data.interest_type,
                commission_rate=input_data.commission_rate,
                insurance_rate=input_data.insurance_rate,
                payment_frequency=input_data.payment_frequency,
                amortization_system=input_data.amortization_system,
                min_income_required=input_data.min_income_required,
                max_debt_to_income_ratio=input_data.max_debt_to_income_ratio,
                min_employment_months=input_data.min_employment_months,
                requires_guarantor=input_data.requires_guarantor,
                requires_collateral=input_data.requires_collateral,
                is_active=input_data.is_active,
            )
            
            # Actualizar contadores de suscripción
            usage_service = UpdateUsageCountersService()
            usage_service.execute(UpdateUsageCountersInput(
                institution=institution,
                products_delta=1  # Incrementar contador de productos
            ))
            
            return CreateProductResult(
                success=True,
                product=product,
                message=f'Producto {product.name} creado exitosamente'
            )
            
        except Exception as e:
            return CreateProductResult(
                success=False,
                product=None,
                message=f'Error al crear producto: {str(e)}',
                errors={'general': str(e)}
            )
    
    def get_product(self, product_id: int, institution_id: int) -> Optional[CreditProduct]:
        """Obtiene un producto por ID."""
        try:
            return CreditProduct.objects.get(
                id=product_id,
                institution_id=institution_id
            )
        except CreditProduct.DoesNotExist:
            return None
    
    def list_products(
        self,
        institution_id: int,
        is_active: Optional[bool] = None,
        product_type: Optional[str] = None
    ):
        """
        Lista productos con filtros opcionales.
        
        Args:
            institution_id: ID de la institución
            is_active: Filtrar por estado activo
            product_type: Filtrar por tipo de producto
            
        Returns:
            QuerySet de productos
        """
        queryset = CreditProduct.objects.filter(institution_id=institution_id)
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        
        if product_type:
            queryset = queryset.filter(product_type=product_type)
        
        return queryset.order_by('display_order', 'name')
