"""
Catálogo de reportes disponibles.

Este servicio define todos los tipos de reportes disponibles en el sistema,
sus configuraciones, columnas, filtros, agrupaciones y ordenamientos permitidos.
"""
from typing import Dict, List, Optional, Any


class ReportCatalogService:
    """
    Servicio de catálogo de reportes.
    
    Proporciona acceso al catálogo completo de reportes disponibles,
    validación de tipos de reportes, y metadatos de configuración.
    """
    
    # Catálogo completo de reportes
    CATALOG = {
        'TENANT': {
            'CREDITS': {
                'loans_by_status': {
                    'name': 'Créditos por Estado',
                    'description': 'Créditos agrupados por estado',
                    'datasource': 'LoanApplication',
                    'roles': ['ADMIN', 'MANAGER', 'ANALYST', 'OFFICER'],
                    'available_columns': [
                        # Identificación
                        'application_number', 'status', 'risk_level', 'credit_score',
                        # Cliente
                        'client_name', 'client_document', 'client_email', 'client_phone',
                        # Producto
                        'product_name', 'product_code', 'product_type',
                        # Montos y términos
                        'requested_amount', 'approved_amount', 'term_months', 
                        'approved_term_months', 'approved_interest_rate', 'monthly_payment',
                        # Información económica
                        'monthly_income', 'employment_type', 'debt_to_income_ratio',
                        # Sucursal y asignación
                        'branch_name', 'assigned_to_name', 'reviewed_by_name', 
                        'approved_by_name', 'created_by_name',
                        # Estados de verificación
                        'identity_verification_status', 'documents_status',
                        # Fechas
                        'created_at', 'submitted_at', 'reviewed_at', 'approved_at', 
                        'rejected_at', 'disbursed_at', 'updated_at',
                        # Propósito y notas
                        'purpose', 'notes', 'observation_reason', 'rejection_reason',
                        # Metadata
                        'is_active'
                    ],
                    'available_filters': {
                        'status': {
                            'operators': ['in', 'not_in'],
                            'type': 'choice',
                            'values': ['DRAFT', 'SUBMITTED', 'IN_REVIEW', 'OBSERVED',
                                      'APPROVED', 'REJECTED', 'DISBURSED', 'CANCELLED']
                        },
                        'risk_level': {
                            'operators': ['in', 'not_in'],
                            'type': 'choice',
                            'values': ['LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH']
                        },
                        'identity_verification_status': {
                            'operators': ['in', 'not_in'],
                            'type': 'choice',
                            'values': ['NOT_VERIFIED', 'PENDING', 'IN_PROGRESS', 'APPROVED', 
                                      'DECLINED', 'MANUAL_REVIEW']
                        },
                        'documents_status': {
                            'operators': ['in', 'not_in'],
                            'type': 'choice',
                            'values': ['NOT_REQUIRED', 'PENDING', 'COMPLETE', 'OBSERVED']
                        },
                        'employment_type': {
                            'operators': ['in', 'not_in'],
                            'type': 'choice',
                            'values': ['EMPLOYED', 'SELF_EMPLOYED', 'BUSINESS_OWNER', 
                                      'RETIRED', 'UNEMPLOYED', 'STUDENT', 'OTHER']
                        },
                        'branch_id': {
                            'operators': ['in', 'not_in'],
                            'type': 'integer'
                        },
                        'product_id': {
                            'operators': ['in', 'not_in'],
                            'type': 'integer'
                        },
                        'requested_amount': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'decimal'
                        },
                        'approved_amount': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'decimal'
                        },
                        'credit_score': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'integer'
                        },
                        'monthly_income': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'decimal'
                        },
                        'created_at': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'date'
                        },
                        'submitted_at': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'date'
                        },
                        'approved_at': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'date'
                        },
                        'is_active': {
                            'operators': ['equals'],
                            'type': 'boolean'
                        }
                    },
                    'available_groupings': [
                        'status', 'risk_level', 'branch_name', 'product_name',
                        'employment_type', 'identity_verification_status', 'documents_status',
                        'month', 'quarter', 'year'
                    ],
                    'available_sort_fields': [
                        'application_number', 'client_name', 'client_document',
                        'requested_amount', 'approved_amount', 'monthly_payment',
                        'credit_score', 'debt_to_income_ratio', 'monthly_income',
                        'created_at', 'submitted_at', 'reviewed_at', 'approved_at', 
                        'rejected_at', 'disbursed_at', 'updated_at',
                        'term_months', 'approved_term_months'
                    ],
                    'formats': ['csv', 'xlsx', 'pdf']
                },
                'loans_by_date_range': {
                    'name': 'Créditos por Rango de Fechas',
                    'description': 'Créditos por rango de fechas',
                    'datasource': 'LoanApplication',
                    'roles': ['ADMIN', 'MANAGER', 'ANALYST'],
                    'available_columns': [
                        # Identificación
                        'application_number', 'status', 'risk_level', 'credit_score',
                        # Cliente
                        'client_name', 'client_document', 'client_email', 'client_phone',
                        # Producto
                        'product_name', 'product_code', 'product_type',
                        # Montos y términos
                        'requested_amount', 'approved_amount', 'term_months',
                        'approved_term_months', 'monthly_payment',
                        # Información económica
                        'monthly_income', 'employment_type',
                        # Sucursal
                        'branch_name', 'branch_city',
                        # Fechas
                        'created_at', 'submitted_at', 'reviewed_at', 'approved_at',
                        'rejected_at', 'disbursed_at'
                    ],
                    'available_filters': {
                        'date_field': {
                            'operators': ['equals'],
                            'type': 'choice',
                            'values': ['created_at', 'submitted_at', 'approved_at', 
                                      'reviewed_at', 'rejected_at', 'disbursed_at']
                        },
                        'date_range': {
                            'operators': ['between'],
                            'type': 'date',
                            'required': True
                        },
                        'status': {
                            'operators': ['in', 'not_in'],
                            'type': 'choice',
                            'values': ['DRAFT', 'SUBMITTED', 'IN_REVIEW', 'APPROVED',
                                      'REJECTED', 'DISBURSED', 'CANCELLED']
                        },
                        'risk_level': {
                            'operators': ['in', 'not_in'],
                            'type': 'choice',
                            'values': ['LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH']
                        },
                        'employment_type': {
                            'operators': ['in'],
                            'type': 'choice',
                            'values': ['EMPLOYED', 'SELF_EMPLOYED', 'BUSINESS_OWNER', 
                                      'RETIRED', 'UNEMPLOYED', 'STUDENT', 'OTHER']
                        },
                        'branch_id': {
                            'operators': ['in'],
                            'type': 'integer'
                        },
                        'product_id': {
                            'operators': ['in'],
                            'type': 'integer'
                        }
                    },
                    'available_groupings': [
                        'status', 'branch_name', 'product_name', 'risk_level',
                        'employment_type', 'day', 'week', 'month', 'quarter'
                    ],
                    'available_sort_fields': [
                        'created_at', 'submitted_at', 'reviewed_at', 'approved_at',
                        'rejected_at', 'disbursed_at', 'requested_amount', 
                        'approved_amount', 'client_name', 'client_document',
                        'application_number', 'credit_score', 'monthly_income'
                    ],
                    'formats': ['csv', 'xlsx', 'pdf']
                },
                'loans_by_branch': {
                    'name': 'Créditos por Sucursal',
                    'description': 'Créditos agrupados por sucursal',
                    'datasource': 'LoanApplication',
                    'roles': ['ADMIN', 'MANAGER'],
                    'available_columns': [
                        'branch_name', 'branch_city', 'total_applications',
                        'approved_count', 'rejected_count', 'pending_count',
                        'total_requested_amount', 'total_approved_amount',
                        'avg_requested_amount', 'avg_approved_amount', 'approval_rate'
                    ],
                    'available_filters': {
                        'branch_id': {
                            'operators': ['in', 'not_in'],
                            'type': 'integer'
                        },
                        'created_at': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'date'
                        },
                        'status': {
                            'operators': ['in', 'not_in'],
                            'type': 'choice',
                            'values': ['DRAFT', 'SUBMITTED', 'IN_REVIEW', 'APPROVED',
                                      'REJECTED', 'DISBURSED']
                        }
                    },
                    'available_groupings': [
                        'branch_name', 'branch_city', 'month', 'quarter'
                    ],
                    'available_sort_fields': [
                        'branch_name', 'total_applications', 'approved_count',
                        'total_approved_amount', 'approval_rate'
                    ],
                    'formats': ['csv', 'xlsx', 'pdf']
                },
                'loans_by_product': {
                    'name': 'Créditos por Producto',
                    'description': 'Créditos agrupados por producto financiero',
                    'datasource': 'LoanApplication',
                    'roles': ['ADMIN', 'MANAGER'],
                    'available_columns': [
                        'product_name', 'product_code', 'product_type',
                        'total_applications', 'approved_count', 'rejected_count',
                        'pending_count', 'total_requested_amount', 'total_approved_amount',
                        'avg_requested_amount', 'avg_approved_amount', 'avg_term_months',
                        'approval_rate'
                    ],
                    'available_filters': {
                        'product_id': {
                            'operators': ['in', 'not_in'],
                            'type': 'integer'
                        },
                        'product_type': {
                            'operators': ['in'],
                            'type': 'string'
                        },
                        'created_at': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'date'
                        },
                        'status': {
                            'operators': ['in', 'not_in'],
                            'type': 'choice',
                            'values': ['SUBMITTED', 'IN_REVIEW', 'APPROVED',
                                      'REJECTED', 'DISBURSED']
                        }
                    },
                    'available_groupings': [
                        'product_name', 'product_type', 'month', 'quarter'
                    ],
                    'available_sort_fields': [
                        'product_name', 'total_applications', 'approved_count',
                        'total_approved_amount', 'approval_rate'
                    ],
                    'formats': ['csv', 'xlsx', 'pdf']
                },
                'active_loans': {
                    'name': 'Créditos Activos',
                    'description': 'Créditos activos (aprobados y desembolsados)',
                    'datasource': 'LoanApplication',
                    'roles': ['ADMIN', 'MANAGER', 'ANALYST'],
                    'available_columns': [
                        'application_number', 'client_name', 'client_document',
                        'product_name', 'approved_amount', 'term_months',
                        'branch_name', 'approved_at', 'disbursed_at',
                        'days_since_disbursement'
                    ],
                    'available_filters': {
                        'status': {
                            'operators': ['in'],
                            'type': 'choice',
                            'values': ['APPROVED', 'DISBURSED'],
                            'default': ['APPROVED', 'DISBURSED']
                        },
                        'approved_at': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'date'
                        },
                        'branch_id': {
                            'operators': ['in'],
                            'type': 'integer'
                        },
                        'product_id': {
                            'operators': ['in'],
                            'type': 'integer'
                        },
                        'approved_amount': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'decimal'
                        }
                    },
                    'available_groupings': [
                        'product_name', 'branch_name', 'month'
                    ],
                    'available_sort_fields': [
                        'approved_at', 'disbursed_at', 'approved_amount', 'client_name'
                    ],
                    'formats': ['csv', 'xlsx', 'pdf']
                }
            },
            'CUSTOMERS': {
                'customers_registered': {
                    'name': 'Clientes Registrados',
                    'description': 'Clientes registrados por período',
                    'datasource': 'Client',
                    'roles': ['ADMIN', 'MANAGER'],
                    'available_columns': [
                        # Identificación
                        'document_number', 'document_type', 'document_extension',
                        # Información personal
                        'full_name', 'first_name', 'last_name', 'email', 'birth_date',
                        'gender', 'client_type',
                        # Contacto
                        'mobile_phone', 'phone', 'address', 'city', 'department', 
                        'country', 'postal_code',
                        # Información laboral
                        'employment_status', 'employer_name', 'employer_nit', 
                        'job_title', 'employment_start_date', 'monthly_income', 
                        'additional_income',
                        # Estados
                        'kyc_status', 'status', 'risk_level', 'is_active',
                        # Fechas
                        'created_at', 'verified_at', 'updated_at',
                        # Verificación
                        'verified_by_name'
                    ],
                    'available_filters': {
                        'created_at': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'date'
                        },
                        'verified_at': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'date'
                        },
                        'kyc_status': {
                            'operators': ['in', 'not_in'],
                            'type': 'choice',
                            'values': ['PENDING', 'VERIFIED', 'REJECTED', 'EXPIRED']
                        },
                        'employment_status': {
                            'operators': ['in'],
                            'type': 'choice',
                            'values': ['EMPLOYED', 'SELF_EMPLOYED', 'BUSINESS_OWNER',
                                      'RETIRED', 'UNEMPLOYED', 'OTHER']
                        },
                        'risk_level': {
                            'operators': ['in'],
                            'type': 'choice',
                            'values': ['LOW', 'MEDIUM', 'HIGH']
                        },
                        'client_type': {
                            'operators': ['in'],
                            'type': 'choice',
                            'values': ['NATURAL', 'JURIDICA']
                        },
                        'document_type': {
                            'operators': ['in'],
                            'type': 'choice',
                            'values': ['CI', 'NIT', 'PASSPORT', 'RUC']
                        },
                        'gender': {
                            'operators': ['in'],
                            'type': 'choice',
                            'values': ['M', 'F', 'O']
                        },
                        'city': {
                            'operators': ['in'],
                            'type': 'string'
                        },
                        'department': {
                            'operators': ['in'],
                            'type': 'string'
                        },
                        'is_active': {
                            'operators': ['equals'],
                            'type': 'boolean'
                        },
                        'monthly_income': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'decimal'
                        }
                    },
                    'available_groupings': [
                        'kyc_status', 'employment_status', 'risk_level', 'client_type',
                        'document_type', 'gender', 'city', 'department', 'is_active',
                        'month', 'quarter', 'year'
                    ],
                    'available_sort_fields': [
                        'created_at', 'verified_at', 'updated_at', 'full_name', 
                        'first_name', 'last_name', 'document_number', 'email', 
                        'mobile_phone', 'phone', 'birth_date', 'monthly_income',
                        'additional_income', 'employment_start_date'
                    ],
                    'formats': ['csv', 'xlsx', 'pdf']
                },
                'customers_by_status': {
                    'name': 'Clientes por Estado',
                    'description': 'Clientes agrupados por estado de KYC y actividad',
                    'datasource': 'Client',
                    'roles': ['ADMIN', 'MANAGER'],
                    'available_columns': [
                        'document_number', 'document_type', 'full_name', 'email',
                        'mobile_phone', 'phone', 'kyc_status', 'status', 'is_active',
                        'employment_status', 'risk_level', 'created_at', 'verified_at',
                        'last_activity_at', 'last_login', 'active_time', 'device_type'
                    ],
                    'available_filters': {
                        'kyc_status': {
                            'operators': ['in', 'not_in'],
                            'type': 'choice',
                            'values': ['PENDING', 'VERIFIED', 'REJECTED', 'EXPIRED']
                        },
                        'is_active': {
                            'operators': ['equals'],
                            'type': 'boolean'
                        },
                        'employment_status': {
                            'operators': ['in'],
                            'type': 'choice',
                            'values': ['EMPLOYED', 'SELF_EMPLOYED', 'BUSINESS_OWNER',
                                      'RETIRED', 'UNEMPLOYED', 'OTHER']
                        },
                        'risk_level': {
                            'operators': ['in'],
                            'type': 'choice',
                            'values': ['LOW', 'MEDIUM', 'HIGH']
                        },
                        'created_at': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'date'
                        },
                        'verified_at': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'date'
                        }
                    },
                    'available_groupings': [
                        'kyc_status', 'is_active', 'employment_status', 'risk_level',
                        'month', 'quarter', 'year'
                    ],
                    'available_sort_fields': [
                        'created_at', 'verified_at', 'last_activity_at', 'last_login',
                        'full_name', 'email', 'document_number'
                    ],
                    'formats': ['csv', 'xlsx', 'pdf']
                },
                'customers_with_active_loans': {
                    'name': 'Clientes con Créditos Activos',
                    'description': 'Clientes con créditos activos',
                    'datasource': 'Client',
                    'roles': ['ADMIN', 'MANAGER', 'ANALYST'],
                    'available_columns': [
                        'client_document', 'client_name', 'client_email', 'client_phone',
                        'total_active_loans', 'total_approved_amount', 'avg_credit_score',
                        'latest_loan_date', 'risk_level'
                    ],
                    'available_filters': {
                        'loan_status': {
                            'operators': ['in'],
                            'type': 'choice',
                            'values': ['APPROVED', 'DISBURSED'],
                            'default': ['APPROVED', 'DISBURSED']
                        },
                        'approved_at': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'date'
                        },
                        'total_approved_amount': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'decimal'
                        },
                        'risk_level': {
                            'operators': ['in'],
                            'type': 'choice',
                            'values': ['LOW', 'MEDIUM', 'HIGH']
                        }
                    },
                    'available_groupings': [
                        'risk_level', 'month'
                    ],
                    'available_sort_fields': [
                        'client_name', 'total_active_loans', 'total_approved_amount',
                        'latest_loan_date'
                    ],
                    'formats': ['csv', 'xlsx', 'pdf']
                }
            },
            'DOCUMENTS': {
                'applications_with_pending_documents': {
                    'name': 'Solicitudes con Documentos Pendientes',
                    'description': 'Solicitudes con documentos pendientes',
                    'datasource': 'LoanApplication',
                    'roles': ['ADMIN', 'MANAGER', 'ANALYST'],
                    'available_columns': [
                        'application_number', 'client_name', 'client_email', 'client_phone',
                        'product_name', 'total_documents_required', 'pending_documents_count',
                        'pending_document_types', 'completion_percentage', 'application_status',
                        'days_since_submission', 'created_at'
                    ],
                    'available_filters': {
                        'document_status': {
                            'operators': ['in'],
                            'type': 'choice',
                            'values': ['PENDING', 'UPLOADED', 'UNDER_REVIEW'],
                            'default': ['PENDING']
                        },
                        'application_status': {
                            'operators': ['in'],
                            'type': 'choice',
                            'values': ['SUBMITTED', 'IN_REVIEW', 'OBSERVED']
                        },
                        'days_since_submission': {
                            'operators': ['gte'],
                            'type': 'integer'
                        },
                        'created_at': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'date'
                        }
                    },
                    'available_groupings': [
                        'product_name', 'application_status', 'month'
                    ],
                    'available_sort_fields': [
                        'days_since_submission', 'pending_documents_count', 'created_at',
                        'application_number', 'client_name', 'completion_percentage'
                    ],
                    'formats': ['csv', 'xlsx', 'pdf']
                }
            },
            'IDENTITY_VERIFICATION': {
                'verifications_by_status': {
                    'name': 'Verificaciones por Estado',
                    'description': 'Verificaciones de identidad por estado',
                    'datasource': 'IdentityVerification',
                    'roles': ['ADMIN', 'MANAGER', 'ANALYST'],
                    'available_columns': [
                        'client_name', 'client_document', 'application_number',
                        'status', 'decision', 'provider', 'started_at', 'completed_at',
                        'processing_time_minutes', 'branch_name'
                    ],
                    'available_filters': {
                        'status': {
                            'operators': ['in', 'not_in'],
                            'type': 'choice',
                            'values': ['PENDING', 'IN_PROGRESS', 'APPROVED', 'DECLINED',
                                      'MANUAL_REVIEW', 'EXPIRED', 'ERROR']
                        },
                        'decision': {
                            'operators': ['in'],
                            'type': 'choice',
                            'values': ['APPROVED', 'DECLINED', 'PENDING', 'MANUAL_REVIEW']
                        },
                        'started_at': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'date'
                        },
                        'branch_id': {
                            'operators': ['in'],
                            'type': 'integer'
                        }
                    },
                    'available_groupings': [
                        'status', 'decision', 'provider', 'branch_name', 'month'
                    ],
                    'available_sort_fields': [
                        'started_at', 'completed_at', 'processing_time_minutes',
                        'client_name', 'client_document', 'application_number'
                    ],
                    'formats': ['csv', 'xlsx', 'pdf']
                }
            },
            'PRODUCTS': {
                'credit_products_catalog': {
                    'name': 'Catálogo de Productos Crediticios',
                    'description': 'Lista de productos crediticios con sus parámetros y configuración',
                    'datasource': 'CreditProduct',
                    'roles': ['ADMIN', 'MANAGER', 'ANALYST', 'OFFICER'],
                    'available_columns': [
                        # Información básica del producto
                        'product_name', 'product_code', 'product_type', 'description',
                        'is_active', 'display_order',
                        # Parámetros de montos
                        'min_amount', 'max_amount', 'default_amount',
                        # Parámetros de plazos
                        'min_term_months', 'max_term_months', 'default_term_months',
                        # Tasas de interés
                        'min_interest_rate', 'max_interest_rate', 'default_interest_rate',
                        'interest_rate_type',
                        # Comisiones y cargos
                        'origination_fee_percentage', 'origination_fee_fixed',
                        'late_payment_fee_percentage', 'late_payment_fee_fixed',
                        'prepayment_penalty_percentage',
                        # Información de marketing
                        'target_audience', 'benefits',
                        # Conjunto de reglas
                        'rule_set_name', 'rule_set_code',
                        # Fechas
                        'created_at', 'updated_at'
                    ],
                    'available_filters': {
                        'is_active': {
                            'operators': ['equals'],
                            'type': 'boolean'
                        },
                        'product_type': {
                            'operators': ['in'],
                            'type': 'string'
                        },
                        'min_amount': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'decimal'
                        },
                        'max_amount': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'decimal'
                        },
                        'min_term_months': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'integer'
                        },
                        'max_term_months': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'integer'
                        },
                        'min_interest_rate': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'decimal'
                        },
                        'max_interest_rate': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'decimal'
                        },
                        'created_at': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'date'
                        }
                    },
                    'available_groupings': [
                        'product_type', 'is_active', 'rule_set_name', 'interest_rate_type'
                    ],
                    'available_sort_fields': [
                        'product_name', 'product_code', 'display_order',
                        'min_amount', 'max_amount', 'default_amount',
                        'min_term_months', 'max_term_months',
                        'min_interest_rate', 'max_interest_rate',
                        'created_at', 'updated_at'
                    ],
                    'formats': ['csv', 'xlsx', 'pdf']
                }
            }
        },
        'SAAS': {
            'TENANTS': {
                'tenants_by_status': {
                    'name': 'Tenants por Estado',
                    'description': 'Instituciones financieras por estado',
                    'datasource': 'FinancialInstitution',
                    'roles': ['saas_admin'],
                    'available_columns': [
                        'name', 'slug', 'institution_type', 'is_active', 'created_at',
                        'subscription_status', 'plan_name', 'user_count', 'branch_count',
                        'active_loans_count', 'total_clients'
                    ],
                    'available_filters': {
                        'institution_type': {
                            'operators': ['in'],
                            'type': 'choice',
                            'values': ['BANKING', 'MICROFINANCE', 'COOPERATIVE', 'FINTECH']
                        },
                        'is_active': {
                            'operators': ['equals'],
                            'type': 'boolean'
                        },
                        'created_at': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'date'
                        },
                        'subscription_status': {
                            'operators': ['in'],
                            'type': 'choice',
                            'values': ['TRIAL', 'ACTIVE', 'SUSPENDED', 'CANCELLED', 'EXPIRED']
                        }
                    },
                    'available_groupings': [
                        'institution_type', 'is_active', 'subscription_status',
                        'plan_name', 'month', 'quarter'
                    ],
                    'available_sort_fields': [
                        'name', 'created_at', 'user_count', 'branch_count', 'active_loans_count',
                        'total_clients', 'slug'
                    ],
                    'formats': ['csv', 'xlsx', 'pdf']
                }
            },
            'USERS': {
                'users_by_tenant': {
                    'name': 'Usuarios por Tenant',
                    'description': 'Usuarios registrados por tenant',
                    'datasource': 'User',
                    'roles': ['saas_admin'],
                    'available_columns': [
                        'tenant_name', 'tenant_slug', 'total_users', 'active_users',
                        'inactive_users', 'admin_count', 'manager_count', 'analyst_count',
                        'officer_count', 'client_count', 'last_user_created_at'
                    ],
                    'available_filters': {
                        'tenant_id': {
                            'operators': ['in'],
                            'type': 'integer'
                        },
                        'is_active': {
                            'operators': ['equals'],
                            'type': 'boolean'
                        },
                        'created_at': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'date'
                        }
                    },
                    'available_groupings': [
                        'tenant_name', 'month', 'quarter'
                    ],
                    'available_sort_fields': [
                        'tenant_name', 'total_users', 'active_users', 'last_user_created_at',
                        'inactive_users', 'admin_count', 'manager_count', 'analyst_count',
                        'officer_count', 'client_count'
                    ],
                    'formats': ['csv', 'xlsx', 'pdf']
                }
            },
            'SUBSCRIPTIONS': {
                'subscriptions_by_status': {
                    'name': 'Suscripciones por Estado',
                    'description': 'Suscripciones por estado',
                    'datasource': 'Subscription',
                    'roles': ['saas_admin'],
                    'available_columns': [
                        'tenant_name', 'plan_name', 'status', 'payment_status',
                        'start_date', 'end_date', 'trial_end_date', 'next_billing_date',
                        'amount_due', 'total_paid', 'current_users', 'current_branches',
                        'days_active'
                    ],
                    'available_filters': {
                        'status': {
                            'operators': ['in', 'not_in'],
                            'type': 'choice',
                            'values': ['TRIAL', 'ACTIVE', 'SUSPENDED', 'CANCELLED', 'EXPIRED']
                        },
                        'payment_status': {
                            'operators': ['in'],
                            'type': 'choice',
                            'values': ['PENDING', 'PAID', 'OVERDUE', 'FAILED']
                        },
                        'plan_id': {
                            'operators': ['in'],
                            'type': 'integer'
                        },
                        'tenant_id': {
                            'operators': ['in'],
                            'type': 'integer'
                        },
                        'start_date': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'date'
                        },
                        'end_date': {
                            'operators': ['gte', 'lte', 'between'],
                            'type': 'date'
                        }
                    },
                    'available_groupings': [
                        'status', 'payment_status', 'plan_name', 'month', 'quarter'
                    ],
                    'available_sort_fields': [
                        'tenant_name', 'start_date', 'end_date', 'next_billing_date',
                        'amount_due', 'total_paid', 'trial_end_date', 'plan_name',
                        'days_active'
                    ],
                    'formats': ['csv', 'xlsx', 'pdf']
                }
            }
        }
    }
    
    @classmethod
    def get_report_definition(
        cls,
        scope: str,
        category: str,
        report_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene la definición de un tipo de reporte.
        
        Args:
            scope: TENANT o SAAS
            category: Categoría del reporte
            report_type: Tipo específico de reporte
            
        Returns:
            Definición del reporte o None si no existe
        """
        try:
            return cls.CATALOG[scope][category][report_type]
        except KeyError:
            return None
    
    @classmethod
    def get_categories(cls, scope: str) -> List[str]:
        """
        Obtiene las categorías disponibles para un scope.
        
        Args:
            scope: TENANT o SAAS
            
        Returns:
            Lista de categorías
        """
        return list(cls.CATALOG.get(scope, {}).keys())
    
    @classmethod
    def get_report_types(cls, scope: str, category: str) -> List[str]:
        """
        Obtiene los tipos de reportes disponibles para una categoría.
        
        Args:
            scope: TENANT o SAAS
            category: Categoría del reporte
            
        Returns:
            Lista de tipos de reportes
        """
        return list(cls.CATALOG.get(scope, {}).get(category, {}).keys())
    
    @classmethod
    def get_full_catalog(cls, scope: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene el catálogo completo o filtrado por scope.
        
        Args:
            scope: TENANT, SAAS o None para todos
            
        Returns:
            Catálogo completo o filtrado
        """
        if scope:
            return {scope: cls.CATALOG.get(scope, {})}
        return cls.CATALOG
    
    @classmethod
    def validate_report_type(
        cls,
        scope: str,
        category: str,
        report_type: str
    ) -> bool:
        """
        Valida que un tipo de reporte exista.
        
        Args:
            scope: TENANT o SAAS
            category: Categoría del reporte
            report_type: Tipo específico de reporte
            
        Returns:
            True si existe, False si no
        """
        return cls.get_report_definition(scope, category, report_type) is not None
    
    @classmethod
    def get_available_columns(
        cls,
        scope: str,
        category: str,
        report_type: str
    ) -> List[str]:
        """
        Obtiene las columnas disponibles para un tipo de reporte.
        
        Args:
            scope: TENANT o SAAS
            category: Categoría del reporte
            report_type: Tipo específico de reporte
            
        Returns:
            Lista de columnas disponibles
        """
        definition = cls.get_report_definition(scope, category, report_type)
        return definition.get('available_columns', []) if definition else []
    
    @classmethod
    def get_available_filters(
        cls,
        scope: str,
        category: str,
        report_type: str
    ) -> Dict[str, Any]:
        """
        Obtiene los filtros disponibles para un tipo de reporte.
        
        Args:
            scope: TENANT o SAAS
            category: Categoría del reporte
            report_type: Tipo específico de reporte
            
        Returns:
            Diccionario de filtros disponibles
        """
        definition = cls.get_report_definition(scope, category, report_type)
        return definition.get('available_filters', {}) if definition else {}
    
    @classmethod
    def get_available_groupings(
        cls,
        scope: str,
        category: str,
        report_type: str
    ) -> List[str]:
        """
        Obtiene las agrupaciones disponibles para un tipo de reporte.
        
        Args:
            scope: TENANT o SAAS
            category: Categoría del reporte
            report_type: Tipo específico de reporte
            
        Returns:
            Lista de agrupaciones disponibles
        """
        definition = cls.get_report_definition(scope, category, report_type)
        return definition.get('available_groupings', []) if definition else []
    
    @classmethod
    def get_available_sort_fields(
        cls,
        scope: str,
        category: str,
        report_type: str
    ) -> List[str]:
        """
        Obtiene los campos de ordenamiento disponibles para un tipo de reporte.
        
        Args:
            scope: TENANT o SAAS
            category: Categoría del reporte
            report_type: Tipo específico de reporte
            
        Returns:
            Lista de campos de ordenamiento disponibles
        """
        definition = cls.get_report_definition(scope, category, report_type)
        return definition.get('available_sort_fields', []) if definition else []
    
    @classmethod
    def get_allowed_roles(
        cls,
        scope: str,
        category: str,
        report_type: str
    ) -> List[str]:
        """
        Obtiene los roles permitidos para un tipo de reporte.
        
        Args:
            scope: TENANT o SAAS
            category: Categoría del reporte
            report_type: Tipo específico de reporte
            
        Returns:
            Lista de roles permitidos
        """
        definition = cls.get_report_definition(scope, category, report_type)
        return definition.get('roles', []) if definition else []

    @classmethod
    def get_available_reports(
        cls,
        scope: str,
        user_roles: List[str]
    ) -> Dict[str, Any]:
        """
        Obtiene los reportes disponibles para un scope y roles de usuario.
        
        Filtra el catálogo completo para mostrar solo los reportes
        a los que el usuario tiene acceso según sus roles.
        
        Args:
            scope: TENANT o SAAS
            user_roles: Lista de roles del usuario
            
        Returns:
            Diccionario con categorías y lista de reportes disponibles
        """
        if scope not in cls.CATALOG:
            return {}
        
        # Normalizar roles a mayúsculas para comparación
        normalized_roles = [role.upper() for role in user_roles]
        
        available = {}
        scope_catalog = cls.CATALOG[scope]
        
        for category, reports in scope_catalog.items():
            category_reports = []
            
            for report_type, definition in reports.items():
                # Verificar si el usuario tiene algún rol permitido
                allowed_roles = [r.upper() for r in definition.get('roles', [])]
                
                # Si no hay roles definidos o el usuario tiene al menos un rol permitido
                if not allowed_roles or any(role in allowed_roles for role in normalized_roles):
                    # Retornar información completa del reporte para el frontend
                    category_reports.append({
                        'type': report_type,
                        'name': definition['name'],
                        'description': definition['description'],
                        'datasource': definition.get('datasource', ''),
                        'roles': definition.get('roles', []),
                        'available_columns': definition.get('available_columns', []),
                        'available_filters': definition.get('available_filters', {}),
                        'available_groupings': definition.get('available_groupings', []),
                        'available_sort_fields': definition.get('available_sort_fields', []),
                        'formats': definition.get('formats', ['csv', 'xlsx'])
                    })
            
            if category_reports:
                available[category] = category_reports
        
        return available
