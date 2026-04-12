"""
Configuración del admin de Django para productos crediticios.
"""

from django.contrib import admin
from api.products.models import CreditProduct, ProductRequirement


@admin.register(CreditProduct)
class CreditProductAdmin(admin.ModelAdmin):
    """Admin para el modelo CreditProduct."""
    
    list_display = [
        'id',
        'name',
        'code',
        'product_type',
        'interest_rate',
        'min_amount',
        'max_amount',
        'is_active',
        'created_at',
    ]
    
    list_filter = [
        'product_type',
        'interest_type',
        'is_active',
        'requires_guarantor',
        'requires_collateral',
        'created_at',
    ]
    
    search_fields = [
        'name',
        'code',
        'description',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('Información Básica', {
            'fields': (
                'id',
                'name',
                'code',
                'product_type',
                'description',
                'is_active',
                'display_order',
            )
        }),
        ('Montos y Plazos', {
            'fields': (
                'min_amount',
                'max_amount',
                'min_term_months',
                'max_term_months',
            )
        }),
        ('Tasas de Interés', {
            'fields': (
                'interest_rate',
                'interest_type',
                'effective_annual_rate',
            )
        }),
        ('Comisiones y Seguros', {
            'fields': (
                'commission_rate',
                'insurance_rate',
                'additional_insurance_rate',
            )
        }),
        ('Sistema de Pago', {
            'fields': (
                'payment_frequency',
                'amortization_system',
                'grace_period_months',
                'allows_early_payment',
                'early_payment_penalty',
            )
        }),
        ('Requisitos', {
            'fields': (
                'min_income_required',
                'max_debt_to_income_ratio',
                'min_employment_months',
                'requires_guarantor',
                'requires_collateral',
                'min_collateral_coverage',
                'required_documents',
            )
        }),
        ('Scoring y Aprobación', {
            'fields': (
                'min_credit_score',
                'auto_approval_enabled',
                'max_auto_approval_amount',
            )
        }),
        ('Información Adicional', {
            'fields': (
                'target_audience',
                'benefits',
                'terms_and_conditions',
            )
        }),
        ('Sistema', {
            'fields': (
                'institution',
                'created_at',
                'updated_at',
            )
        }),
    )


@admin.register(ProductRequirement)
class ProductRequirementAdmin(admin.ModelAdmin):
    """Admin para el modelo ProductRequirement."""
    
    list_display = [
        'id',
        'product',
        'requirement_name',
        'is_mandatory',
        'display_order',
    ]
    
    list_filter = [
        'is_mandatory',
        'product__product_type',
    ]
    
    search_fields = [
        'requirement_name',
        'description',
        'product__name',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
    ]
