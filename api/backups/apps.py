"""
Configuración de la app backups.
"""
from django.apps import AppConfig


class BackupsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.backups'
    verbose_name = 'Backups de Tenants'
