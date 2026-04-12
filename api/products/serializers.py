"""
Serializers para gestión de productos crediticios.
"""

from rest_framework import serializers
from api.products.models import CreditProduct, ProductRequirement


class CreditProductSerializer(serializers.ModelSerializer):
    """Serializer completo para lectura de productos."""
    
    product_type_display = serializers.CharField(source='get_product_type_display', read_only=True)
    interest_type_display = serializers.CharField(source='get_interest_type_display', read_only=True)
    payment_frequency_display = serializers.CharField(source='get_payment_frequency_display', read_only=True)
    amortization_system_display = serializers.CharField(source='get_amortization_system_display', read_only=True)
    
    class Meta:
        model = CreditProduct
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class CreateCreditProductSerializer(serializers.ModelSerializer):
    """Serializer para crear productos."""
    
    class Meta:
        model = CreditProduct
        exclude = ['institution', 'created_at', 'updated_at']
    
    def validate(self, attrs):
        """Validaciones a nivel de objeto."""
        if attrs['min_amount'] >= attrs['max_amount']:
            raise serializers.ValidationError({
                'min_amount': 'El monto mínimo debe ser menor al monto máximo'
            })
        
        if attrs['min_term_months'] >= attrs['max_term_months']:
            raise serializers.ValidationError({
                'min_term_months': 'El plazo mínimo debe ser menor al plazo máximo'
            })
        
        return attrs


class UpdateCreditProductSerializer(serializers.ModelSerializer):
    """Serializer para actualización parcial de productos."""
    
    class Meta:
        model = CreditProduct
        exclude = ['institution', 'code', 'created_at', 'updated_at']


class CreditProductListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listado de productos."""
    
    product_type_display = serializers.CharField(source='get_product_type_display', read_only=True)
    
    class Meta:
        model = CreditProduct
        fields = [
            'id',
            'name',
            'code',
            'product_type',
            'product_type_display',
            'description',
            'min_amount',
            'max_amount',
            'interest_rate',
            'interest_type',
            'min_term_months',
            'max_term_months',
            'commission_rate',
            'insurance_rate',
            'amortization_system',
            'requires_guarantor',
            'auto_approval_enabled',
            'min_credit_score',
            'is_active',
            'created_at',
        ]


class ProductRequirementSerializer(serializers.ModelSerializer):
    """Serializer para requisitos de productos."""
    
    class Meta:
        model = ProductRequirement
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
