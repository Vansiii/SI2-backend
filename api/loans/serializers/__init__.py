"""
Serializers para el módulo de loans.

Organización:
- loan_serializers.py: Serializers principales de LoanApplication
- rule_serializers.py: Serializers para CU-09 (Administración de Reglas)
- document_serializers.py: Serializers para CU-12 (Gestión Documental)
- timeline_serializers.py: Serializers para CU-07 (Timeline y Seguimiento)
"""

# Importar serializers principales (mantener compatibilidad con código existente)
from api.loans.serializers.loan_serializers import *

# Importar serializers de reglas (CU-09)
from api.loans.serializers.rule_serializers import (
    TenantRuleSetSerializer,
    TenantRuleSetWriteSerializer,
    EligibilityRuleSerializer,
    CreditProductParameterSerializer,
    # DocumentRequirementSerializer,  # DEPRECATED: Eliminado
    WorkflowStageDefinitionSerializer,
    DecisionThresholdSerializer,
    RuleSetAuditSerializer,
)

# Importar serializers de documentos (CU-12)
from api.loans.serializers.document_serializers import (
    LoanApplicationDocumentRequirementSerializer,
    DocumentUploadSerializer,
    DocumentReviewSerializer,
    DocumentReviewHistorySerializer,
)

# Importar serializers de timeline (CU-07)
from api.loans.serializers.timeline_serializers import (
    TimelineEventSerializer,
    PendingActionSerializer,
    LoanApplicationTimelineSerializer,
    LoanApplicationListSerializer,
)

__all__ = [
    # Serializers de reglas (CU-09)
    'TenantRuleSetSerializer',
    'TenantRuleSetWriteSerializer',
    'EligibilityRuleSerializer',
    'CreditProductParameterSerializer',
    # 'DocumentRequirementSerializer',  # DEPRECATED: Eliminado
    'WorkflowStageDefinitionSerializer',
    'DecisionThresholdSerializer',
    'RuleSetAuditSerializer',
    # Serializers de documentos (CU-12)
    'LoanApplicationDocumentRequirementSerializer',
    'DocumentUploadSerializer',
    'DocumentReviewSerializer',
    'DocumentReviewHistorySerializer',
    # Serializers de timeline (CU-07)
    'TimelineEventSerializer',
    'PendingActionSerializer',
    'LoanApplicationTimelineSerializer',
    'LoanApplicationListSerializer',
]
