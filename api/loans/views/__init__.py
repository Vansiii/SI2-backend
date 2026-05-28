"""
Views para gestión de créditos.

Organización:
- rule_viewsets.py: ViewSets para CU-09 (Administración de Reglas)
- document_viewsets.py: ViewSets para CU-12 (Gestión Documental)
- timeline_viewsets.py: ViewSets para CU-07 (Timeline y Seguimiento)
"""

from .rule_viewsets import (
    TenantRuleSetViewSet,
    EligibilityRuleViewSet,
    CreditProductParameterViewSet,
    # DocumentRequirementViewSet,  # DEPRECATED: Eliminado
    WorkflowStageDefinitionViewSet,
    DecisionThresholdViewSet,
)
from .document_viewsets import (
    ClientDocumentViewSet,
    StaffDocumentViewSet,
)
from .timeline_viewsets import (
    ClientApplicationViewSet,
)

__all__ = [
    # Rule viewsets (CU-09)
    'TenantRuleSetViewSet',
    'EligibilityRuleViewSet',
    'CreditProductParameterViewSet',
    # 'DocumentRequirementViewSet',  # DEPRECATED: Eliminado
    'WorkflowStageDefinitionViewSet',
    'DecisionThresholdViewSet',
    # Document viewsets (CU-12)
    'ClientDocumentViewSet',
    'StaffDocumentViewSet',
    # Timeline viewsets (CU-07)
    'ClientApplicationViewSet',
]
