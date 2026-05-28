"""
Core abstract base models shared across all apps.
"""

from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base model that adds created_at and updated_at timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TenantModel(TimeStampedModel):
    """
    Abstract base model for multi-tenant entities.
    Every tenant-scoped model must be linked to a FinancialInstitution.
    """

    institution = models.ForeignKey(
        'api.FinancialInstitution',
        on_delete=models.CASCADE,
        related_name='+',
        db_index=True,
    )

    class Meta:
        abstract = True
