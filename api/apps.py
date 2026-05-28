from django.apps import AppConfig


class ApiConfig(AppConfig):
    name = 'api'
    default_auto_field = 'django.db.models.BigAutoField'
    
    def ready(self):
        """
        Importa los signals cuando la aplicación está lista.
        """
        import api.users.signals
