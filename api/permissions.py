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
		# DEBUG: Imprimir información
		print(f"\n=== DEBUG HasPermission ===")
		print(f"Permission code: {self.permission_code}")
		print(f"User authenticated: {request.user.is_authenticated}")
		print(f"User: {request.user.email if request.user.is_authenticated else 'Anonymous'}")
		
		# Verificar autenticación
		if not request.user.is_authenticated:
			print("DENIED: User not authenticated")
			return False
		
		# Verificar si tiene perfil
		if not hasattr(request.user, 'profile'):
			print("DENIED: User has no profile")
			return False
		
		print(f"User type: {request.user.profile.user_type}")
		print(f"Is SaaS admin: {request.user.profile.is_saas_admin()}")
		
		# Superadmin SaaS tiene acceso a todo
		if request.user.profile.is_saas_admin():
			print("GRANTED: User is SaaS admin")
			return True
		
		# Usuario de tenant - verificar permiso en su institución
		print(f"Has request.tenant: {hasattr(request, 'tenant')}")
		print(f"request.tenant value: {request.tenant if hasattr(request, 'tenant') else 'N/A'}")
		
		if not request.tenant:
			# Usuario sin tenant no puede acceder
			print("DENIED: No tenant in request")
			return False
		
		# Verificar permiso usando el método del perfil
		has_perm = request.user.profile.has_permission(self.permission_code, request.tenant)
		print(f"has_permission result: {has_perm}")
		print("=== END DEBUG ===\n")
		
		return has_perm


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
