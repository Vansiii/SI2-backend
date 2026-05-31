"""
Permisos personalizados para el módulo de contratos
"""

from rest_framework import permissions


class CanViewContract(permissions.BasePermission):
    """
    Permiso para ver contratos.
    
    - Staff puede ver todos los contratos de su tenant
    - Prestatarios pueden ver solo sus propios contratos
    - Garantes pueden ver contratos donde son garantes
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Staff puede ver todos los contratos de su tenant
        if hasattr(request.user, 'is_staff_member') and request.user.is_staff_member:
            return obj.institution == request.user.institution
        
        # Prestatario puede ver su propio contrato
        if hasattr(obj.loan_application.client, 'user'):
            if obj.loan_application.client.user == request.user:
                return True
        
        # Garante puede ver contratos donde es garante
        if obj.loan_application.guarantors.filter(
            user=request.user,
            status='APPROVED'
        ).exists():
            return True
        
        return False


class CanGenerateContract(permissions.BasePermission):
    """
    Permiso para generar contratos.
    Solo staff con permisos adecuados.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Verificar que sea staff
        if not (hasattr(request.user, 'is_staff_member') and request.user.is_staff_member):
            return False
        
        # Verificar permiso específico
        return request.user.has_perm('contracts.add_contract')


class CanManageContractTemplates(permissions.BasePermission):
    """
    Permiso para gestionar plantillas de contratos.
    Solo administradores.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Solo administradores
        return request.user.has_perm('contracts.change_contracttemplate')


class CanSignContract(permissions.BasePermission):
    """
    Permiso para firmar contratos.
    
    - Prestatarios pueden firmar sus propios contratos
    - Garantes pueden firmar contratos donde son garantes
    - Staff puede firmar como institución
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Verificar que el contrato pueda ser firmado
        if not obj.can_be_signed():
            return False
        
        # Staff puede firmar como institución
        if hasattr(request.user, 'is_staff_member') and request.user.is_staff_member:
            if obj.institution == request.user.institution:
                return True
        
        # Prestatario puede firmar su propio contrato
        if hasattr(obj.loan_application.client, 'user'):
            if obj.loan_application.client.user == request.user:
                return True
        
        # Garante puede firmar si es garante del contrato
        if obj.loan_application.guarantors.filter(
            user=request.user,
            status='APPROVED'
        ).exists():
            return True
        
        return False


class CanCancelContract(permissions.BasePermission):
    """
    Permiso para cancelar contratos.
    Solo administradores.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return request.user.has_perm('contracts.delete_contract')
    
    def has_object_permission(self, request, view, obj):
        # Verificar que el contrato pueda ser cancelado
        if not obj.can_be_cancelled():
            return False
        
        # Verificar que pertenezca al mismo tenant
        return obj.institution == request.user.institution


class CanPublishContract(permissions.BasePermission):
    """
    Permiso para publicar contratos (cambiar de DRAFT a PENDING_SIGNATURE).
    Solo staff con permisos adecuados.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not (hasattr(request.user, 'is_staff_member') and request.user.is_staff_member):
            return False
        
        return request.user.has_perm('contracts.change_contract')
    
    def has_object_permission(self, request, view, obj):
        # Solo contratos en DRAFT pueden ser publicados
        if obj.status != obj.Status.DRAFT:
            return False
        
        # Verificar que pertenezca al mismo tenant
        return obj.institution == request.user.institution


class CanDownloadContractPDF(permissions.BasePermission):
    """
    Permiso para descargar el PDF del contrato.
    
    - Staff puede descargar todos los contratos de su tenant
    - Prestatarios pueden descargar sus propios contratos
    - Garantes pueden descargar contratos donde son garantes
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Reutilizar lógica de CanViewContract
        can_view = CanViewContract()
        return can_view.has_object_permission(request, view, obj)
