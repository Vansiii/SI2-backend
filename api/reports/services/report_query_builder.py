"""
Constructor de queries seguro para reportes.

Este servicio construye QuerySets de Django usando ORM,
validando todos los campos, filtros y agrupaciones contra
el catálogo de reportes.
"""
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta, date
from decimal import Decimal

from django.db.models import (
    Q, QuerySet, Count, Sum, Avg, Max, F, 
    ExpressionWrapper, FloatField, IntegerField
)
from django.db.models.functions import (
    TruncDay, TruncWeek, TruncMonth, TruncQuarter, TruncYear
)
from django.apps import apps

from .report_catalog import ReportCatalogService

logger = logging.getLogger(__name__)


class ReportQueryBuilder:
    """
    Constructor de queries seguro para reportes.
    
    Construye QuerySets validados usando ORM de Django,
    sin ejecutar SQL directo ni confiar en entrada del usuario.
    
    SEGURIDAD:
    - Todos los campos se validan contra listas blancas del catálogo
    - Solo se usa ORM de Django, nunca SQL directo
    - Filtrado automático por tenant para reportes TENANT
    - Validación de tipos de datos
    """
    
    # Mapeo de datasources a modelos Django
    MODEL_MAP = {
        'LoanApplication': 'loans.LoanApplication',
        'Client': 'clients.Client',
        'CreditProduct': 'products.CreditProduct',
        'LoanApplicationDocumentRequirement': 'loans.LoanApplicationDocumentRequirement',
        'IdentityVerification': 'identity_verification.IdentityVerification',
        'FinancialInstitution': 'tenants.FinancialInstitution',
        'User': 'auth.User',
        'SubscriptionPlan': 'saas.SubscriptionPlan',
        'Subscription': 'saas.Subscription',
    }
    
    # Mapeo de columnas a relaciones ForeignKey para optimización
    SELECT_RELATED_MAP = {
        'client_name': 'client__user',
        'client_document': 'client',
        'product_name': 'product',
        'product_code': 'product',
        'product_type': 'product',
        'branch_name': 'branch',
        'branch_city': 'branch',
        'assigned_to_name': 'assigned_to',
        'plan_name': 'subscription__plan',
        'tenant_name': 'institution',
        'tenant_slug': 'institution',
        # Productos crediticios
        'rule_set_name': 'rule_set',
        'rule_set_code': 'rule_set',
    }
    
    def __init__(self, tenant=None):
        """
        Inicializa el query builder.
        
        Args:
            tenant: Instancia de FinancialInstitution o None para reportes SAAS
        """
        self.tenant = tenant
        self.catalog = ReportCatalogService()
        # Importar aquí para evitar importaciones circulares
        from .product_report_builder import ProductReportBuilder
        self.product_builder = ProductReportBuilder()
    
    def build_query(
        self,
        scope: str,
        category: str,
        report_type: str,
        config: Dict[str, Any]
    ) -> QuerySet:
        """
        Construye un QuerySet seguro para el reporte.
        
        Args:
            scope: TENANT o SAAS
            category: Categoría del reporte
            report_type: Tipo específico de reporte
            config: Configuración del reporte validada
        
        Returns:
            QuerySet configurado
        
        Raises:
            ValueError: Si la configuración es inválida
        """
        # Obtener definición del reporte
        report_def = self.catalog.get_report_definition(scope, category, report_type)
        if not report_def:
            raise ValueError(f"Reporte no encontrado: {scope}.{category}.{report_type}")
        
        # Obtener modelo base
        model = self._get_model(report_def['datasource'])
        
        # Iniciar queryset con filtrado por tenant si aplica
        if scope == 'TENANT':
            if not self.tenant:
                raise ValueError("Tenant requerido para reportes TENANT")
            # Usar manager con filtrado automático por tenant
            queryset = model.objects.all()
        else:
            # Reportes SAAS: usar all_objects sin filtrar por tenant
            queryset = model.all_objects.all() if hasattr(model, 'all_objects') else model.objects.all()
        
        # Aplicar filtros
        if 'filters' in config and config['filters']:
            queryset = self._apply_filters(queryset, config['filters'], report_def)
        
        # Aplicar date_range
        if 'date_range' in config and config['date_range']:
            queryset = self._apply_date_range(queryset, config['date_range'])
        
        # Aplicar anotaciones especiales para productos crediticios
        if report_def['datasource'] == 'CreditProduct':
            queryset = self.product_builder.annotate_product_parameters(queryset)
        
        # Aplicar select_related y prefetch_related para optimización
        queryset = self._optimize_query(queryset, config.get('columns', []), report_def)
        
        return queryset
    
    def build_aggregated_query(
        self,
        queryset: QuerySet,
        config: Dict[str, Any],
        report_def: Dict[str, Any]
    ) -> QuerySet:
        """
        Construye query con agrupaciones y agregaciones.
        
        Args:
            queryset: QuerySet base
            config: Configuración del reporte
            report_def: Definición del reporte del catálogo
        
        Returns:
            QuerySet con agregaciones
        """
        if not config.get('group_by'):
            logger.warning("No se especificaron campos de agrupación (group_by)")
            return queryset
        
        logger.info(f"Construyendo query agregado con group_by: {config['group_by']}")
        
        # Construir annotaciones para campos temporales si se usan
        queryset = self._annotate_temporal_fields(queryset, config['group_by'])
        
        # Construir values() con campos de agrupación
        group_fields = self._build_group_fields(config['group_by'])
        logger.info(f"Campos de agrupación mapeados: {group_fields}")
        
        try:
            queryset = queryset.values(*group_fields)
        except Exception as e:
            logger.error(f"Error al aplicar values() con campos {group_fields}: {e}")
            raise ValueError(f"Error en campos de agrupación: {e}")
        
        # Construir agregaciones
        annotations = self._build_aggregations(config.get('columns', []), report_def)
        logger.info(f"Agregaciones construidas: {list(annotations.keys())}")
        
        if annotations:
            try:
                queryset = queryset.annotate(**annotations)
            except Exception as e:
                logger.error(f"Error al aplicar agregaciones: {e}")
                raise ValueError(f"Error en agregaciones: {e}")
        
        # Aplicar ordenamiento
        if 'sort' in config and config['sort']:
            queryset = self._apply_sorting(queryset, config['sort'])
        
        return queryset
    
    def _get_model(self, datasource: str):
        """
        Obtiene el modelo de Django por nombre.
        
        Args:
            datasource: Nombre del datasource del catálogo
        
        Returns:
            Clase del modelo Django
        
        Raises:
            ValueError: Si el datasource no está soportado
        """
        if datasource not in self.MODEL_MAP:
            raise ValueError(f"Datasource no soportado: {datasource}")
        
        app_label, model_name = self.MODEL_MAP[datasource].split('.')
        return apps.get_model(app_label, model_name)
    
    def _apply_filters(
        self,
        queryset: QuerySet,
        filters: List[Dict],
        report_def: Dict
    ) -> QuerySet:
        """
        Aplica filtros al queryset de forma segura.
        
        Todos los filtros se validan contra el catálogo antes de aplicarse.
        
        Args:
            queryset: QuerySet base
            filters: Lista de filtros a aplicar
            report_def: Definición del reporte
        
        Returns:
            QuerySet filtrado
        """
        q_objects = Q()
        
        for filter_item in filters:
            field = filter_item.get('field')
            operator = filter_item.get('operator')
            value = filter_item.get('value')
            
            # Validar que el filtro existe en el catálogo (lista blanca)
            if field not in report_def['available_filters']:
                continue
            
            # Construir Q object según operador
            q_obj = self._build_filter_q(field, operator, value)
            if q_obj:
                q_objects &= q_obj
        
        return queryset.filter(q_objects)
    
    def _build_filter_q(self, field: str, operator: str, value: Any) -> Optional[Q]:
        """
        Construye un Q object para un filtro.
        
        Args:
            field: Campo a filtrar
            operator: Operador de comparación
            value: Valor a comparar
        
        Returns:
            Q object o None si el operador no es válido
        """
        operator_map = {
            'equals': lambda f, v: Q(**{f: v}),
            'not_equals': lambda f, v: ~Q(**{f: v}),
            'in': lambda f, v: Q(**{f'{f}__in': v}),
            'not_in': lambda f, v: ~Q(**{f'{f}__in': v}),
            'gte': lambda f, v: Q(**{f'{f}__gte': v}),
            'lte': lambda f, v: Q(**{f'{f}__lte': v}),
            'gt': lambda f, v: Q(**{f'{f}__gt': v}),
            'lt': lambda f, v: Q(**{f'{f}__lt': v}),
            'between': lambda f, v: Q(**{f'{f}__gte': v[0], f'{f}__lte': v[1]}) if isinstance(v, list) and len(v) == 2 else Q(),
            'contains': lambda f, v: Q(**{f'{f}__icontains': v}),
            'startswith': lambda f, v: Q(**{f'{f}__istartswith': v}),
            'endswith': lambda f, v: Q(**{f'{f}__iendswith': v}),
            'is_null': lambda f, v: Q(**{f'{f}__isnull': True}),
            'is_not_null': lambda f, v: Q(**{f'{f}__isnull': False}),
        }
        
        if operator not in operator_map:
            return None
        
        return operator_map[operator](field, value)
    
    def _apply_date_range(
        self,
        queryset: QuerySet,
        date_range: Dict
    ) -> QuerySet:
        """
        Aplica rango de fechas al queryset.
        
        Args:
            queryset: QuerySet base
            date_range: Configuración de rango de fechas
        
        Returns:
            QuerySet filtrado por fechas
        """
        start_date = date_range.get('start_date')
        end_date = date_range.get('end_date')
        
        if not start_date or not end_date:
            return queryset
        
        # Convertir strings a date si es necesario
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date).date()
        if isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date).date()
        
        # Aplicar filtro de fecha (campo created_at por defecto)
        # TODO: Hacer configurable el campo de fecha según el reporte
        return queryset.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )
    
    def _optimize_query(
        self,
        queryset: QuerySet,
        columns: List[str],
        report_def: Dict
    ) -> QuerySet:
        """
        Optimiza el queryset con select_related y prefetch_related.
        
        Reduce el número de queries SQL usando JOINs para ForeignKeys.
        
        Args:
            queryset: QuerySet base
            columns: Columnas solicitadas
            report_def: Definición del reporte
        
        Returns:
            QuerySet optimizado
        """
        # Mapeo extendido de columnas a relaciones ForeignKey
        select_related_map = {
            # Producto
            'product_name': 'product',
            'product_code': 'product',
            'product_type': 'product',
            
            # Sucursal
            'branch_name': 'branch',
            'branch_city': 'branch',
            
            # Cliente
            'client_name': 'client__user',
            'client_document': 'client',
            'client_email': 'client__user',
            'client_phone': 'client',
            
            # Usuario asignado
            'assigned_to_name': 'assigned_to',
            
            # Tenant (para reportes SAAS)
            'tenant_name': 'institution',
            'tenant_slug': 'institution',
            
            # Plan (para reportes SAAS)
            'plan_name': 'subscription__plan',
            
            # Reglas
            'rule_set_snapshot': 'rule_set_snapshot',
            
            # Usuario que creó/aprobó/rechazó
            'created_by': 'created_by',
            'approved_by': 'approved_by',
            'reviewed_by': 'reviewed_by',
        }
        
        select_related_fields = set()
        
        for column in columns:
            if column in select_related_map:
                select_related_fields.add(select_related_map[column])
        
        # Agregar relaciones comunes para reportes de créditos
        datasource = report_def.get('datasource')
        if datasource == 'LoanApplication':
            # Siempre incluir product y client para reportes de créditos
            select_related_fields.update(['product', 'client', 'branch'])
        elif datasource == 'CreditProduct':
            # Para reportes de productos crediticios, incluir rule_set y product_type
            select_related_fields.update(['rule_set', 'product_type', 'selected_parameter'])
        
        if select_related_fields:
            queryset = queryset.select_related(*select_related_fields)
        
        return queryset
    
    def _annotate_temporal_fields(
        self,
        queryset: QuerySet,
        group_by: List[str]
    ) -> QuerySet:
        """
        Anota campos temporales (month, quarter, year, etc.) si se usan en agrupación.
        
        Args:
            queryset: QuerySet base
            group_by: Lista de campos de agrupación
        
        Returns:
            QuerySet con anotaciones temporales
        """
        temporal_fields = {
            'day': TruncDay('created_at'),
            'week': TruncWeek('created_at'),
            'month': TruncMonth('created_at'),
            'quarter': TruncQuarter('created_at'),
            'year': TruncYear('created_at'),
        }
        
        annotations = {}
        for field in group_by:
            if field in temporal_fields:
                annotations[field] = temporal_fields[field]
        
        if annotations:
            queryset = queryset.annotate(**annotations)
        
        return queryset
    
    def _build_group_fields(self, group_by: List[str]) -> List[str]:
        """
        Construye lista de campos para values() en agrupación.
        
        Mapea columnas virtuales a campos reales de la base de datos.
        
        Args:
            group_by: Lista de campos de agrupación
        
        Returns:
            Lista de campos para values()
        """
        # Mapeo de columnas virtuales a campos reales de la base de datos
        field_mapping = {
            # === PRODUCTO ===
            'product_name': 'product__name',
            'product_code': 'product__code',
            'product_type': 'product__product_type__name',
            
            # === SUCURSAL ===
            'branch_name': 'branch__name',
            'branch_city': 'branch__city',
            
            # === CLIENTE ===
            'client_name': 'client__user__first_name',  # Se concatena en annotate
            'client_document': 'client__document_number',
            'client_email': 'client__user__email',
            'client_phone': 'client__mobile_phone',
            'full_name': 'user__first_name',  # Se concatena en annotate
            'first_name': 'user__first_name',
            'last_name': 'user__last_name',
            'email': 'user__email',
            'phone': 'mobile_phone',
            'document_number': 'document_number',
            'document_type': 'document_type',
            'document_extension': 'document_extension',
            'birth_date': 'birth_date',
            'gender': 'gender',
            'client_type': 'client_type',
            'address': 'address',
            'city': 'city',
            'department': 'department',
            'country': 'country',
            'postal_code': 'postal_code',
            
            # === INFORMACIÓN LABORAL ===
            'employment_status': 'employment_status',
            'employment_type': 'employment_type',
            'employer_name': 'employer_name',
            'employer_nit': 'employer_nit',
            'job_title': 'job_title',
            'employment_start_date': 'employment_start_date',
            'monthly_income': 'monthly_income',
            'additional_income': 'additional_income',
            'debt_to_income_ratio': 'debt_to_income_ratio',
            
            # === USUARIOS ===
            'assigned_to_name': 'assigned_to__first_name',  # Se concatena en annotate
            'reviewed_by_name': 'reviewed_by__first_name',  # Se concatena en annotate
            'approved_by_name': 'approved_by__first_name',  # Se concatena en annotate
            'created_by_name': 'created_by__first_name',  # Se concatena en annotate
            'updated_by_name': 'updated_by__first_name',  # Se concatena en annotate
            'verified_by_name': 'verified_by__first_name',  # Se concatena en annotate
            
            # === SOLICITUD ===
            'application_number': 'application_number',
            'status': 'status',
            'risk_level': 'risk_level',
            'credit_score': 'credit_score',
            'purpose': 'purpose',
            'notes': 'notes',
            'observation_reason': 'observation_reason',
            'rejection_reason': 'rejection_reason',
            'identity_verification_status': 'identity_verification_status',
            'documents_status': 'documents_status',
            'requested_amount': 'requested_amount',
            'approved_amount': 'approved_amount',
            'term_months': 'term_months',
            'approved_term_months': 'approved_term_months',
            'approved_interest_rate': 'approved_interest_rate',
            'monthly_payment': 'monthly_payment',
            'is_active': 'is_active',
            
            # === FECHAS ===
            'created_at': 'created_at',
            'submitted_at': 'submitted_at',
            'reviewed_at': 'reviewed_at',
            'approved_at': 'approved_at',
            'rejected_at': 'rejected_at',
            'disbursed_at': 'disbursed_at',
            'updated_at': 'updated_at',
            'verified_at': 'verified_at',
            
            # === ESTADOS ===
            'kyc_status': 'kyc_status',
            
            # === TENANT ===
            'tenant_name': 'institution__name',
            'tenant_slug': 'institution__slug',
            'institution_type': 'institution_type',
            
            # === PLAN ===
            'plan_name': 'subscription__plan__name',
            'subscription_status': 'subscription_status',
            'payment_status': 'payment_status',
            
            # === DOCUMENTOS ===
            'application_status': 'status',
            'document_status': 'document_status',
            
            # === VERIFICACIÓN ===
            'decision': 'decision',
            'provider': 'provider',
            
            # === PRODUCTOS CREDITICIOS ===
            'rule_set_name': 'rule_set__name',
            'rule_set_code': 'rule_set__code',
            'interest_rate_type': 'selected_parameter__interest_rate_type',
            'display_order': 'display_order',
            'description': 'description',
            'target_audience': 'target_audience',
            'benefits': 'benefits',
            
            # === CAMPOS TEMPORALES (ya anotados, mantener nombre) ===
            'day': 'day',
            'week': 'week',
            'month': 'month',
            'quarter': 'quarter',
            'year': 'year',
        }
        
        mapped_fields = []
        for field in group_by:
            mapped_field = field_mapping.get(field, field)
            mapped_fields.append(mapped_field)
        
        return mapped_fields
    
    def _build_aggregations(
        self,
        columns: List[str],
        report_def: Dict
    ) -> Dict[str, Any]:
        """
        Construye diccionario de agregaciones.
        
        Mapea columnas virtuales a expresiones Django ORM con soporte completo
        para todos los tipos de reportes del catálogo.
        
        Args:
            columns: Columnas solicitadas
            report_def: Definición del reporte
        
        Returns:
            Diccionario de agregaciones para annotate()
        """
        aggregations = {}
        
        # Mapeo completo de columnas agregadas a expresiones Django ORM
        # Organizado por tipo de reporte para mejor mantenibilidad
        
        # ===== AGREGACIONES GENERALES (Créditos) =====
        agg_map = {
            # Conteos básicos
            'total_applications': Count('id'),
            'total_loans': Count('id'),
            'total_clients': Count('client', distinct=True),
            'total_users': Count('id'),
            'total_active_loans': Count('id', filter=Q(status__in=['APPROVED', 'DISBURSED'])),
            
            # Conteos por estado
            'approved_count': Count('id', filter=Q(status='APPROVED')),
            'rejected_count': Count('id', filter=Q(status='REJECTED')),
            'pending_count': Count('id', filter=Q(status__in=['SUBMITTED', 'IN_REVIEW', 'OBSERVED'])),
            'disbursed_count': Count('id', filter=Q(status='DISBURSED')),
            'draft_count': Count('id', filter=Q(status='DRAFT')),
            'cancelled_count': Count('id', filter=Q(status='CANCELLED')),
            
            # Montos
            'total_requested_amount': Sum('requested_amount'),
            'total_approved_amount': Sum('approved_amount'),
            'avg_requested_amount': Avg('requested_amount'),
            'avg_approved_amount': Avg('approved_amount'),
            'max_approved_amount': Sum('approved_amount'),  # Para reportes de máximo
            'min_approved_amount': Sum('approved_amount'),  # Para reportes de mínimo
            
            # Promedios
            'avg_credit_score': Avg('credit_score'),
            'avg_term_months': Avg('term_months'),
            'avg_interest_rate': Avg('approved_interest_rate'),
            'avg_monthly_payment': Avg('monthly_payment'),
            'avg_monthly_income': Avg('monthly_income'),
            'avg_debt_to_income': Avg('debt_to_income_ratio'),
            
            # Tasas y porcentajes calculados
            'approval_rate': ExpressionWrapper(
                (Count('id', filter=Q(status='APPROVED')) * 100.0) / Count('id'),
                output_field=FloatField()
            ),
            'rejection_rate': ExpressionWrapper(
                (Count('id', filter=Q(status='REJECTED')) * 100.0) / Count('id'),
                output_field=FloatField()
            ),
            'disbursement_rate': ExpressionWrapper(
                (Count('id', filter=Q(status='DISBURSED')) * 100.0) / Count('id'),
                output_field=FloatField()
            ),
            
            # ===== AGREGACIONES PARA CLIENTES =====
            'active_users': Count('id', filter=Q(is_active=True)),
            'inactive_users': Count('id', filter=Q(is_active=False)),
            'verified_clients': Count('id', filter=Q(kyc_status='VERIFIED')),
            'pending_verification': Count('id', filter=Q(kyc_status='PENDING')),
            
            # ===== AGREGACIONES PARA DOCUMENTOS =====
            'total_documents_required': Count('document_checklist'),
            'pending_documents_count': Count('document_checklist', filter=Q(document_checklist__status='PENDING')),
            'uploaded_documents_count': Count('document_checklist', filter=Q(document_checklist__status='UPLOADED')),
            'completion_percentage': ExpressionWrapper(
                (Count('document_checklist', filter=Q(document_checklist__status__in=['UPLOADED', 'VERIFIED'])) * 100.0) / Count('document_checklist'),
                output_field=FloatField()
            ),
            
            # ===== AGREGACIONES PARA VERIFICACIÓN DE IDENTIDAD =====
            'processing_time_minutes': Avg('processing_time_minutes'),
            'approved_verifications': Count('id', filter=Q(decision='APPROVED')),
            'declined_verifications': Count('id', filter=Q(decision='DECLINED')),
            'manual_review_count': Count('id', filter=Q(decision='MANUAL_REVIEW')),
            
            # ===== AGREGACIONES PARA REPORTES SAAS =====
            'user_count': Count('users'),
            'branch_count': Count('branches'),
            'active_loans_count': Count('loan_applications', filter=Q(loan_applications__status__in=['APPROVED', 'DISBURSED'])),
            'admin_count': Count('users', filter=Q(users__role='ADMIN')),
            'manager_count': Count('users', filter=Q(users__role='MANAGER')),
            'analyst_count': Count('users', filter=Q(users__role='ANALYST')),
            'officer_count': Count('users', filter=Q(users__role='OFFICER')),
            'client_count': Count('users', filter=Q(users__role='CLIENT')),
            
            # ===== AGREGACIONES PARA SUSCRIPCIONES =====
            'amount_due': Sum('amount_due'),
            'total_paid': Sum('total_paid'),
            'current_users': Sum('current_users'),
            'current_branches': Sum('current_branches'),
            'days_active': Avg('days_active'),
        }
        
        # Agregar las agregaciones solicitadas
        for column in columns:
            if column in agg_map:
                aggregations[column] = agg_map[column]
        
        # ===== CAMPOS CALCULADOS ESPECIALES =====
        
        # Campos que requieren anotaciones adicionales
        if 'days_since_submission' in columns:
            from django.utils import timezone
            aggregations['days_since_submission'] = ExpressionWrapper(
                (timezone.now() - F('submitted_at')).total_seconds() / 86400,
                output_field=IntegerField()
            )
        
        if 'days_since_disbursement' in columns:
            from django.utils import timezone
            aggregations['days_since_disbursement'] = ExpressionWrapper(
                (timezone.now() - F('disbursed_at')).total_seconds() / 86400,
                output_field=IntegerField()
            )
        
        if 'latest_loan_date' in columns:
            from django.db.models import Max
            aggregations['latest_loan_date'] = Max('approved_at')
        
        if 'last_user_created_at' in columns:
            from django.db.models import Max
            aggregations['last_user_created_at'] = Max('created_at')
        
        # ===== CAMPOS NO AGREGADOS (campos directos de ForeignKey) =====
        # Estos campos se obtienen directamente del GROUP BY, no necesitan agregación
        non_aggregated_fields = [
            'product_name', 'product_code', 'product_type',
            'branch_name', 'branch_city',
            'client_name', 'client_document', 'client_email', 'client_phone',
            'assigned_to_name',
            'tenant_name', 'tenant_slug',
            'plan_name',
            'application_number',
            'status', 'risk_level', 'employment_status', 'kyc_status',
            'city', 'department', 'decision', 'provider',
            'institution_type', 'is_active', 'subscription_status', 'payment_status',
            'application_status', 'document_status',
            'document_type', 'full_name', 'email', 'mobile_phone',
            'pending_document_types',  # Este requiere lógica especial
        ]
        
        # Para campos no agregados que están en columns pero no en group_by,
        # necesitamos agregarlos como anotaciones usando F()
        # Esto es necesario cuando se solicita un campo que no está en el GROUP BY
        # pero que es único para cada grupo (como product_name cuando agrupamos por product_id)
        
        return aggregations
    
    def _apply_sorting(
        self,
        queryset: QuerySet,
        sort: List[Dict]
    ) -> QuerySet:
        """
        Aplica ordenamiento al queryset.
        
        Mapea campos virtuales a campos reales o agregados.
        
        Args:
            queryset: QuerySet base
            sort: Lista de configuraciones de ordenamiento
        
        Returns:
            QuerySet ordenado
        """
        # Mapeo de campos virtuales a campos reales para ordenamiento
        field_mapping = {
            # === PRODUCTO ===
            'product_name': 'product__name',
            'product_code': 'product__code',
            'product_type': 'product__product_type__name',
            
            # === SUCURSAL ===
            'branch_name': 'branch__name',
            'branch_city': 'branch__city',
            
            # === CLIENTE ===
            'client_name': 'client__user__first_name',
            'client_document': 'client__document_number',
            'client_email': 'client__user__email',
            'client_phone': 'client__mobile_phone',
            'full_name': 'user__first_name',
            'first_name': 'user__first_name',
            'last_name': 'user__last_name',
            'email': 'user__email',
            'phone': 'mobile_phone',
            'document_number': 'document_number',
            'document_type': 'document_type',
            'document_extension': 'document_extension',
            'birth_date': 'birth_date',
            'gender': 'gender',
            'client_type': 'client_type',
            'address': 'address',
            'city': 'city',
            'department': 'department',
            'country': 'country',
            'postal_code': 'postal_code',
            
            # === INFORMACIÓN LABORAL ===
            'employment_status': 'employment_status',
            'employment_type': 'employment_type',
            'employer_name': 'employer_name',
            'employer_nit': 'employer_nit',
            'job_title': 'job_title',
            'employment_start_date': 'employment_start_date',
            'monthly_income': 'monthly_income',
            'additional_income': 'additional_income',
            'debt_to_income_ratio': 'debt_to_income_ratio',
            
            # === USUARIOS ===
            'assigned_to_name': 'assigned_to__first_name',
            'reviewed_by_name': 'reviewed_by__first_name',
            'approved_by_name': 'approved_by__first_name',
            'created_by_name': 'created_by__first_name',
            'updated_by_name': 'updated_by__first_name',
            'verified_by_name': 'verified_by__first_name',
            
            # === SOLICITUD ===
            'application_number': 'application_number',
            'status': 'status',
            'risk_level': 'risk_level',
            'credit_score': 'credit_score',
            'purpose': 'purpose',
            'notes': 'notes',
            'observation_reason': 'observation_reason',
            'rejection_reason': 'rejection_reason',
            'identity_verification_status': 'identity_verification_status',
            'documents_status': 'documents_status',
            'requested_amount': 'requested_amount',
            'approved_amount': 'approved_amount',
            'term_months': 'term_months',
            'approved_term_months': 'approved_term_months',
            'approved_interest_rate': 'approved_interest_rate',
            'monthly_payment': 'monthly_payment',
            'is_active': 'is_active',
            
            # === FECHAS ===
            'created_at': 'created_at',
            'submitted_at': 'submitted_at',
            'reviewed_at': 'reviewed_at',
            'approved_at': 'approved_at',
            'rejected_at': 'rejected_at',
            'disbursed_at': 'disbursed_at',
            'updated_at': 'updated_at',
            'verified_at': 'verified_at',
            
            # === ESTADOS ===
            'kyc_status': 'kyc_status',
            
            # === TENANT ===
            'tenant_name': 'institution__name',
            'tenant_slug': 'institution__slug',
            'institution_type': 'institution_type',
            
            # === PLAN ===
            'plan_name': 'subscription__plan__name',
            'subscription_status': 'subscription_status',
            'payment_status': 'payment_status',
            
            # === CAMPOS AGREGADOS (mantener nombre, ya están anotados) ===
            'total_applications': 'total_applications',
            'approved_count': 'approved_count',
            'rejected_count': 'rejected_count',
            'pending_count': 'pending_count',
            'total_requested_amount': 'total_requested_amount',
            'total_approved_amount': 'total_approved_amount',
            'avg_requested_amount': 'avg_requested_amount',
            'avg_approved_amount': 'avg_approved_amount',
            'approval_rate': 'approval_rate',
            'disbursement_rate': 'disbursement_rate',
            'total_users': 'total_users',
            'active_users': 'active_users',
            'avg_credit_score': 'avg_credit_score',
            'avg_term_months': 'avg_term_months',
        }
        
        order_by = []
        
        for sort_item in sort:
            field = sort_item.get('field')
            direction = sort_item.get('direction', 'asc')
            
            if not field:
                continue
            
            # Mapear campo virtual a campo real
            mapped_field = field_mapping.get(field, field)
            
            if direction == 'desc':
                order_by.append(f'-{mapped_field}')
            else:
                order_by.append(mapped_field)
        
        if order_by:
            queryset = queryset.order_by(*order_by)
        
        return queryset
