"""
Clases de permisos personalizadas para autorización basada en roles.

Este módulo implementa verificación de permisos granulares usando el sistema
de roles y permisos dinámicos.
"""

from rest_framework.permissions import BasePermission


class HasPermission(BasePermission):
	"""
	Permission class que verifica si el usuario tiene un permiso específico.
	
	Comportamiento:
	- Superadmin SaaS: Tiene acceso a todo (retorna True siempre)
	- Usuario de tenant: Verifica permiso en su institución
	- Usuario no autenticado: Rechaza acceso (retorna False)
	
	Uso:
		class MyView(APIView):
			permission_classes = [IsAuthenticated, HasPermission]
			
			def __init__(self):
				self.permission_instance = HasPermission('users.view')
				super().__init__()
	"""
	
	def __init__(self, permission_code):
		"""
		Inicializa la clase de permiso.
		
		Args:
			permission_code: Código del permiso a verificar (ej: 'users.view')
		"""
		self.permission_code = permission_code
		super().__init__()
	
	def has_permission(self, request, view):
		"""
		Verifica si el usuario tiene el permiso requerido.
		
		Args:
			request: HttpRequest con usuario autenticado
			view: Vista que está siendo accedida
		
		Returns:
			bool: True si tiene permiso, False en caso contrario
		"""
		# Verificar autenticación
		if not request.user.is_authenticated:
			return False
		
		# Verificar si tiene perfil
		if not hasattr(request.user, 'profile'):
			return False
		
		# Superadmin SaaS tiene acceso a todo
		if request.user.profile.is_saas_admin():
			return True
		
		# Usuario de tenant - verificar permiso en su institución
		if not request.tenant:
			# Usuario sin tenant no puede acceder
			return False
		
		# Verificar permiso usando el método del perfil
		return request.user.profile.has_permission(self.permission_code, request.tenant)


class IsSaaSAdmin(BasePermission):
	"""
	Permission class que verifica si el usuario es un administrador SaaS.
	
	Solo permite acceso a usuarios con user_type='SAAS_ADMIN'.
	"""
	
	def has_permission(self, request, view):
		"""
		Verifica si el usuario es administrador SaaS.
		
		Args:
			request: HttpRequest con usuario autenticado
			view: Vista que está siendo accedida
		
		Returns:
			bool: True si es SaaS admin, False en caso contrario
		"""
		if not request.user.is_authenticated:
			return False
		
		if not hasattr(request.user, 'profile'):
			return False
		
		return request.user.profile.is_saas_admin()


def require_permission(permission_code):
	"""
	Factory function para crear clases de permiso dinámicamente.
	
	Esta función permite crear permission classes de forma más limpia:
	
	Uso:
		class MyView(APIView):
			permission_classes = [IsAuthenticated, require_permission('users.view')]
	
	Args:
		permission_code: Código del permiso a verificar
	
	Returns:
		Clase de permiso configurada
	"""
	class PermissionClass(HasPermission):
		def __init__(self):
			super().__init__(permission_code)
	
	# Establecer nombre descriptivo para debugging
	PermissionClass.__name__ = f'Require_{permission_code.replace(".", "_")}'
	
	return PermissionClass
