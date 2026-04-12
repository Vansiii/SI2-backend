"""
Middleware para auditoría automática de requests.
"""

import json
import time
from django.utils.deprecation import MiddlewareMixin
from api.audit.services import AuditService, SecurityEventService


class AuditMiddleware(MiddlewareMixin):
    """
    Middleware que registra automáticamente acciones importantes.
    """
    
    # Endpoints que deben ser auditados
    AUDIT_PATHS = [
        '/api/users/',
        '/api/roles/',
        '/api/saas/',
        '/api/auth/login/',
        '/api/auth/logout/',
    ]
    
    # Métodos que deben ser auditados
    AUDIT_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']
    
    def process_request(self, request):
        """Marca el inicio del request."""
        request._audit_start_time = time.time()
        return None
    
    def process_response(self, request, response):
        """Registra el request si es necesario."""
        # Solo auditar si el usuario está autenticado
        if not request.user or not request.user.is_authenticated:
            return response
        
        # Verificar si el path debe ser auditado
        should_audit = any(
            request.path.startswith(path) for path in self.AUDIT_PATHS
        )
        
        if not should_audit:
            return response
        
        # Verificar si el método debe ser auditado
        if request.method not in self.AUDIT_METHODS:
            return response
        
        # Registrar la acción
        self._log_request(request, response)
        
        return response
    
    def _log_request(self, request, response):
        """Registra el request en el log de auditoría."""
        try:
            # Determinar el tipo de acción
            action = self._get_action_type(request.method)
            
            # Determinar el tipo de recurso
            resource_type = self._get_resource_type(request.path)
            
            # Obtener el ID del recurso si está disponible
            resource_id = self._get_resource_id(request.path, response)
            
            # Crear descripción
            description = f"{request.method} {request.path}"
            
            # Obtener metadata
            metadata = {
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'duration_ms': int((time.time() - getattr(request, '_audit_start_time', time.time())) * 1000)
            }
            
            # Determinar severidad basada en el código de respuesta
            severity = 'info'
            if response.status_code >= 400:
                severity = 'warning'
            if response.status_code >= 500:
                severity = 'error'
            
            # Registrar en el log
            AuditService.log_action(
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                description=description,
                user=request.user,
                institution=getattr(request, 'tenant', None),
                request=request,
                severity=severity,
                metadata=metadata
            )
            
        except Exception as e:
            # No fallar el request si hay error en auditoría
            print(f"Error en auditoría: {e}")
    
    def _get_action_type(self, method: str) -> str:
        """Mapea el método HTTP a un tipo de acción."""
        mapping = {
            'POST': 'create',
            'PUT': 'update',
            'PATCH': 'update',
            'DELETE': 'delete',
        }
        return mapping.get(method, 'view')
    
    def _get_resource_type(self, path: str) -> str:
        """Extrae el tipo de recurso del path."""
        if '/users/' in path:
            return 'User'
        elif '/roles/' in path:
            return 'Role'
        elif '/saas/' in path:
            return 'Institution'
        elif '/auth/' in path:
            return 'Auth'
        return 'Unknown'
    
    def _get_resource_id(self, path: str, response) -> int:
        """Intenta extraer el ID del recurso."""
        # Intentar extraer del path (ej: /api/users/123/)
        parts = path.strip('/').split('/')
        for part in parts:
            if part.isdigit():
                return int(part)
        
        # Intentar extraer de la respuesta
        try:
            if hasattr(response, 'data') and isinstance(response.data, dict):
                return response.data.get('id')
        except:
            pass
        
        return None


class SecurityEventMiddleware(MiddlewareMixin):
    """
    Middleware que detecta y registra eventos de seguridad.
    """
    
    def process_response(self, request, response):
        """Detecta eventos de seguridad basados en la respuesta."""
        # Registrar accesos no autorizados (403)
        if response.status_code == 403 and request.user.is_authenticated:
            self._log_unauthorized_access(request)
        
        # Registrar intentos de login fallidos (401 en /auth/login/)
        if response.status_code == 401 and '/auth/login/' in request.path:
            self._log_failed_login(request)
        
        return response
    
    def _log_unauthorized_access(self, request):
        """Registra un intento de acceso no autorizado."""
        try:
            resource_type = self._get_resource_type(request.path)
            resource_id = self._get_resource_id_from_path(request.path)
            
            SecurityEventService.log_unauthorized_access(
                user=request.user,
                resource_type=resource_type,
                resource_id=resource_id,
                request=request,
                required_permission='unknown'
            )
        except Exception as e:
            print(f"Error registrando acceso no autorizado: {e}")
    
    def _log_failed_login(self, request):
        """Registra un intento de login fallido."""
        try:
            # Intentar obtener el email del body
            email = 'unknown'
            if hasattr(request, 'data') and isinstance(request.data, dict):
                email = request.data.get('email', 'unknown')
            
            SecurityEventService.log_failed_login(
                email=email,
                request=request,
                reason='Invalid credentials'
            )
        except Exception as e:
            print(f"Error registrando login fallido: {e}")
    
    def _get_resource_type(self, path: str) -> str:
        """Extrae el tipo de recurso del path."""
        if '/users/' in path:
            return 'User'
        elif '/roles/' in path:
            return 'Role'
        elif '/saas/' in path:
            return 'Institution'
        return 'Unknown'
    
    def _get_resource_id_from_path(self, path: str) -> int:
        """Extrae el ID del recurso del path."""
        parts = path.strip('/').split('/')
        for part in parts:
            if part.isdigit():
                return int(part)
        return None
