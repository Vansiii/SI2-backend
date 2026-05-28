from django.apps import AppConfig


class ApiConfig(AppConfig):
    name = 'api'
    default_auto_field = 'django.db.models.BigAutoField'
    
    def ready(self):
        """
        Importa los signals y configura propiedades dinámicas cuando la aplicación está lista.
        """
        import api.users.signals

        # Monkeypatch para agregar la propiedad 'institution' al modelo User
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        if not hasattr(User, 'institution'):
            @property
            def user_institution(self):
                if not hasattr(self, 'institution_memberships'):
                    return None
                membership = self.institution_memberships.filter(is_active=True).first()
                if membership:
                    return membership.institution
                
                # Fallback para clientes
                if hasattr(self, 'client_profile') and self.client_profile:
                    return getattr(self.client_profile, 'institution', None)
                
                return None
            
            User.add_to_class('institution', user_institution)
