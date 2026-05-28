from django.contrib import admin
from .models import LoanApplication, LoanApplicationDocument, LoanApplicationComment


@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    list_display = ['application_number', 'client', 'product', 'requested_amount', 'status', 'created_at']
    list_filter = ['status', 'risk_level', 'created_at', 'submitted_at']
    search_fields = ['application_number', 'client__first_name', 'client__last_name', 'client__document_number']
    readonly_fields = ['application_number', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('application_number', 'client', 'product', 'institution')
        }),
        ('Detalles de la Solicitud', {
            'fields': ('requested_amount', 'term_months', 'purpose', 'status')
        }),
        ('Evaluación', {
            'fields': ('credit_score', 'risk_level', 'debt_to_income_ratio')
        }),
        ('Términos Aprobados', {
            'fields': ('approved_amount', 'approved_term_months', 'approved_interest_rate', 'monthly_payment')
        }),
        ('Fechas', {
            'fields': ('submitted_at', 'reviewed_at', 'approved_at', 'rejected_at', 'disbursed_at')
        }),
        ('Responsables', {
            'fields': ('reviewed_by', 'approved_by')
        }),
        ('Notas', {
            'fields': ('notes', 'rejection_reason')
        }),
    )


@admin.register(LoanApplicationDocument)
class LoanApplicationDocumentAdmin(admin.ModelAdmin):
    list_display = ['application', 'document_type', 'file_name', 'is_verified', 'created_at']
    list_filter = ['document_type', 'is_verified', 'created_at']
    search_fields = ['application__application_number', 'file_name']


@admin.register(LoanApplicationComment)
class LoanApplicationCommentAdmin(admin.ModelAdmin):
    list_display = ['application', 'user', 'is_internal', 'created_at']
    list_filter = ['is_internal', 'created_at']
    search_fields = ['application__application_number', 'comment']
