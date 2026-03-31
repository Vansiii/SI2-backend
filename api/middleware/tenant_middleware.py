"""
Middleware para inyectar contexto de tenant en cada request.

Este middleware identifica el tenant (institución financiera) del usuario autenticado
y lo inyecta en request.tenant para uso en vistas y servicios.

También establece el tenant en thread-local storage para el TenantManager.

Comportamiento:
- Superadmin SaaS: request.tenant = None, request.user_type = 'saas_admin'
- Usuario de tenant: request.tenant = Institution, request.user_type = 'tenant_user'
- Usuario no autenticado: request.tenant = None, request.user_type = None
"""

from api.managers import set_current_tenant, clear_current_tenant
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed


class TenantMiddleware:
	"""
	Middleware que inyecta el tenant actual en el request.
	
	Atributos inyectados:
	- request.tenant: Instancia de FinancialInstitution o None
	- request.user_type: 'saas_admin', 'tenant_user', o None
	"""
	
	def __init__(self, get_response):
		"""
		Inicializa el middleware.
		
		Args:
			get_response: Callable para obtener la respuesta
		"""
		self.get_response = get_response
		self.jwt_authenticator = JWTAuthentication()
	
	def __call__(self, request):
		"""
		Procesa el request e inyecta el tenant.
		
		Args:
			request: HttpRequest
		
		Returns:
			HttpResponse
		"""
		# Inicializar valores por defecto
		request.tenant = None
		request.user_type = None
		
		# DEBUG
		print(f"\n=== DEBUG TenantMiddleware ===")
		print(f"Path: {request.path}")
		
		# Limpiar tenant anterior del thread-local
		clear_current_tenant()
		
		# Intentar autenticar con JWT si hay token
		if 'Authorization' in request.headers or 'HTTP_AUTHORIZATION' in request.META:
			try:
				# Intentar autenticar con JWT
				auth_result = self.jwt_authenticator.authenticate(request)
				if auth_result is not None:
					user, token = auth_result
					request.user = user
					print(f"JWT Auth successful: {user.email}")
				else:
					print(f"JWT Auth returned None")
			except AuthenticationFailed as e:
				print(f"JWT Auth failed: {e}")
			except Exception as e:
				print(f"JWT Auth error: {e}")
		
		print(f"User authenticated: {request.user.is_authenticated}")
		
		# Solo procesar si el usuario está autenticado
		if request.user.is_authenticated:
			print(f"User: {request.user.email}")
			
			# Verificar si el usuario tiene perfil
			if hasattr(request.user, 'profile'):
				print(f"Has profile: True")
				print(f"User type: {request.user.profile.user_type}")
				
				# Verificar si es superadmin SaaS
				if request.user.profile.is_saas_admin():
					request.tenant = None
					request.user_type = 'saas_admin'
					print(f"Is SaaS admin - tenant set to None")
					# Superadmin no tiene tenant - puede ver todo
					set_current_tenant(None)
				else:
					# Usuario de tenant - obtener su institución activa
					membership = request.user.institution_memberships.filter(
						is_active=True
					).first()
					
					print(f"Membership query executed")
					print(f"Membership found: {membership is not None}")
					
					if membership:
						request.tenant = membership.institution
						request.user_type = 'tenant_user'
						print(f"Tenant set to: {membership.institution.name} (ID: {membership.institution.id})")
						# Establecer tenant en thread-local para TenantManager
						set_current_tenant(membership.institution)
					else:
						# Usuario sin membership activa
						request.tenant = None
						request.user_type = 'tenant_user'
						print(f"No active membership - tenant is None")
						set_current_tenant(None)
			else:
				# Usuario sin perfil (caso edge - no debería ocurrir con signals)
				request.tenant = None
				request.user_type = None
				print(f"User has no profile")
				set_current_tenant(None)
		else:
			print(f"User not authenticated")
		
		print(f"Final tenant value: {request.tenant}")
		print(f"Final user_type: {request.user_type}")
		print("=== END DEBUG TenantMiddleware ===\n")
		
		try:
			# Procesar request
			response = self.get_response(request)
		finally:
			# Limpiar tenant del thread-local después del request
			clear_current_tenant()
		
		return response
