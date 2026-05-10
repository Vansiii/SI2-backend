"""
Constructor de reportes de productos crediticios.

Este servicio construye QuerySets especializados para reportes de productos
crediticios, incluyendo sus parámetros desde CreditProductParameter.
"""
import logging
from typing import Dict, List, Any
from django.db.models import F, Q, Value, CharField
from django.db.models.functions import Coalesce

logger = logging.getLogger(__name__)


class ProductReportBuilder:
    """
    Constructor especializado para reportes de productos crediticios.
    
    Maneja la complejidad de obtener parámetros desde CreditProductParameter
    a través de la relación con TenantRuleSet.
    """
    
    @staticmethod
    def annotate_product_parameters(queryset):
        """
        Anota el queryset de productos con sus parámetros desde CreditProductParameter.
        
        Los parámetros están en CreditProductParameter vinculados al rule_set del producto.
        
        Args:
            queryset: QuerySet de CreditProduct
        
        Returns:
            QuerySet anotado con campos de parámetros
        """
        # Obtener parámetros desde rule_set__creditproductparameter
        # Nota: CreditProductParameter tiene una relación OneToOne con TenantRuleSet
        
        queryset = queryset.annotate(
            # Parámetros de montos
            min_amount=Coalesce(
                F('rule_set__creditproductparameter__min_amount'),
                Value(0)
            ),
            max_amount=Coalesce(
                F('rule_set__creditproductparameter__max_amount'),
                Value(0)
            ),
            default_amount=Coalesce(
                F('rule_set__creditproductparameter__default_amount'),
                Value(0)
            ),
            
            # Parámetros de plazos
            min_term_months=Coalesce(
                F('rule_set__creditproductparameter__min_term_months'),
                Value(0)
            ),
            max_term_months=Coalesce(
                F('rule_set__creditproductparameter__max_term_months'),
                Value(0)
            ),
            default_term_months=Coalesce(
                F('rule_set__creditproductparameter__default_term_months'),
                Value(0)
            ),
            
            # Tasas de interés
            min_interest_rate=Coalesce(
                F('rule_set__creditproductparameter__min_interest_rate'),
                Value(0.0)
            ),
            max_interest_rate=Coalesce(
                F('rule_set__creditproductparameter__max_interest_rate'),
                Value(0.0)
            ),
            default_interest_rate=Coalesce(
                F('rule_set__creditproductparameter__default_interest_rate'),
                Value(0.0)
            ),
            interest_rate_type_value=Coalesce(
                F('rule_set__creditproductparameter__interest_rate_type'),
                Value('FIXED', output_field=CharField())
            ),
            
            # Comisiones y cargos
            origination_fee_percentage=Coalesce(
                F('rule_set__creditproductparameter__origination_fee_percentage'),
                Value(0.0)
            ),
            origination_fee_fixed=Coalesce(
                F('rule_set__creditproductparameter__origination_fee_fixed'),
                Value(0.0)
            ),
            late_payment_fee_percentage=Coalesce(
                F('rule_set__creditproductparameter__late_payment_fee_percentage'),
                Value(0.0)
            ),
            late_payment_fee_fixed=Coalesce(
                F('rule_set__creditproductparameter__late_payment_fee_fixed'),
                Value(0.0)
            ),
            prepayment_penalty_percentage=Coalesce(
                F('rule_set__creditproductparameter__prepayment_penalty_percentage'),
                Value(0.0)
            ),
            
            # Información del conjunto de reglas
            rule_set_name_value=Coalesce(
                F('rule_set__name'),
                Value('Sin conjunto de reglas', output_field=CharField())
            ),
            rule_set_code_value=Coalesce(
                F('rule_set__code'),
                Value('N/A', output_field=CharField())
            ),
        )
        
        return queryset
    
    @staticmethod
    def build_product_catalog_query(queryset, columns: List[str]):
        """
        Construye query específico para el reporte de catálogo de productos.
        
        Args:
            queryset: QuerySet base de CreditProduct
            columns: Columnas solicitadas
        
        Returns:
            QuerySet configurado con anotaciones necesarias
        """
        # Anotar con parámetros
        queryset = ProductReportBuilder.annotate_product_parameters(queryset)
        
        # Optimizar con select_related
        queryset = queryset.select_related(
            'product_type',
            'rule_set',
            'rule_set__creditproductparameter'
        )
        
        return queryset
    
    @staticmethod
    def map_column_to_field(column: str) -> str:
        """
        Mapea nombres de columnas del catálogo a campos anotados o reales.
        
        Args:
            column: Nombre de columna del catálogo
        
        Returns:
            Nombre del campo en el queryset
        """
        # Mapeo de columnas virtuales a campos reales o anotados
        column_mapping = {
            # Información básica (campos directos del modelo)
            'product_name': 'name',
            'product_code': 'code',
            'product_type': 'product_type__name',
            'description': 'description',
            'is_active': 'is_active',
            'display_order': 'display_order',
            
            # Parámetros de montos (campos anotados)
            'min_amount': 'min_amount',
            'max_amount': 'max_amount',
            'default_amount': 'default_amount',
            
            # Parámetros de plazos (campos anotados)
            'min_term_months': 'min_term_months',
            'max_term_months': 'max_term_months',
            'default_term_months': 'default_term_months',
            
            # Tasas de interés (campos anotados)
            'min_interest_rate': 'min_interest_rate',
            'max_interest_rate': 'max_interest_rate',
            'default_interest_rate': 'default_interest_rate',
            'interest_rate_type': 'interest_rate_type_value',
            
            # Comisiones y cargos (campos anotados)
            'origination_fee_percentage': 'origination_fee_percentage',
            'origination_fee_fixed': 'origination_fee_fixed',
            'late_payment_fee_percentage': 'late_payment_fee_percentage',
            'late_payment_fee_fixed': 'late_payment_fee_fixed',
            'prepayment_penalty_percentage': 'prepayment_penalty_percentage',
            
            # Información de marketing (campos directos)
            'target_audience': 'target_audience',
            'benefits': 'benefits',
            
            # Conjunto de reglas (campos anotados)
            'rule_set_name': 'rule_set_name_value',
            'rule_set_code': 'rule_set_code_value',
            
            # Fechas (campos directos)
            'created_at': 'created_at',
            'updated_at': 'updated_at',
        }
        
        return column_mapping.get(column, column)
    
    @staticmethod
    def get_values_fields(columns: List[str]) -> List[str]:
        """
        Obtiene la lista de campos para values() basándose en las columnas solicitadas.
        
        Args:
            columns: Columnas solicitadas del catálogo
        
        Returns:
            Lista de campos para values()
        """
        fields = []
        for column in columns:
            field = ProductReportBuilder.map_column_to_field(column)
            fields.append(field)
        
        return fields
