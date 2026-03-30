from django.conf import settings
from django.db import models
from api.managers import TenantManager


class TimeStampedModel(models.Model):
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		abstract = True


class TenantModel(TimeStampedModel):
	"""
	Modelo base abstracto para modelos multi-tenant.
	
	Proporciona:
	- Campo institution (ForeignKey a FinancialInstitution)
	- Manager objects que filtra automáticamente por tenant
	- Manager all_objects sin filtrar (para superadmin)
	
	Uso:
		class MyModel(TenantModel):
			name = models.CharField(max_length=100)
			# ... otros campos ...
	
	Los queries usando objects se filtrarán automáticamente por tenant:
		MyModel.objects.all()  # Solo del tenant actual
		MyModel.all_objects.all()  # Todos los tenants
	"""
	
	institution = models.ForeignKey(
		'FinancialInstitution',
		on_delete=models.CASCADE,
		related_name='%(class)s_set',
		help_text='Institución financiera a la que pertenece este registro'
	)
	
	# Manager con filtrado automático por tenant
	objects = TenantManager()
	
	# Manager sin filtrar (para superadmin y casos especiales)
	all_objects = models.Manager()
	
	class Meta:
		abstract = True


class FinancialInstitution(TimeStampedModel):
	class InstitutionType(models.TextChoices):
		BANKING = 'banking', 'Banco Comercial'
		MICROFINANCE = 'microfinance', 'Microfinanciera'
		COOPERATIVE = 'cooperative', 'Cooperativa de Credito'
		FINTECH = 'fintech', 'Fintech'

	name = models.CharField(max_length=255)
	slug = models.SlugField(max_length=100, unique=True)
	institution_type = models.CharField(
		max_length=20,
		choices=InstitutionType.choices,
		default=InstitutionType.BANKING,
	)
	is_active = models.BooleanField(default=True)
	created_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='created_financial_institutions',
	)

	class Meta:
		db_table = 'financial_institutions'
		ordering = ['-created_at']

	def __str__(self) -> str:
		return f'{self.name} ({self.slug})'


class FinancialInstitutionMembership(TimeStampedModel):
	institution = models.ForeignKey(
		FinancialInstitution,
		on_delete=models.CASCADE,
		related_name='memberships',
	)
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='institution_memberships',
	)
	is_active = models.BooleanField(default=True)

	class Meta:
		db_table = 'financial_institution_memberships'
		constraints = [
			models.UniqueConstraint(
				fields=['institution', 'user'],
				name='uniq_institution_user_membership',
			)
		]
		ordering = ['-created_at']

	def __str__(self) -> str:
		return f'{self.user} -> {self.institution}'



class PasswordResetToken(TimeStampedModel):
	"""
	Modelo para almacenar tokens de recuperación de contraseña.
	
	Los tokens tienen una duración de 1 hora y solo pueden usarse una vez.
	"""
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='password_reset_tokens',
	)
	token = models.CharField(max_length=64, unique=True, db_index=True)
	expires_at = models.DateTimeField()
	is_used = models.BooleanField(default=False)
	used_at = models.DateTimeField(null=True, blank=True)
	ip_address = models.GenericIPAddressField(null=True, blank=True)
	user_agent = models.TextField(blank=True)

	class Meta:
		db_table = 'password_reset_tokens'
		ordering = ['-created_at']
		indexes = [
			models.Index(fields=['token', 'is_used']),
			models.Index(fields=['user', 'is_used']),
			models.Index(fields=['expires_at']),
		]

	def __str__(self) -> str:
		return f'PasswordResetToken for {self.user.email} (used: {self.is_used})'

	def is_valid(self) -> bool:
		"""
		Verifica si el token es válido.
		
		Un token es válido si:
		- No ha sido usado
		- No ha expirado
		
		Returns:
			bool: True si el token es válido, False en caso contrario
		"""
		from django.utils import timezone
		
		if self.is_used:
			return False
		
		if timezone.now() > self.expires_at:
			return False
		
		return True

	def mark_as_used(self) -> None:
		"""
		Marca el token como usado.
		
		Actualiza is_used=True y used_at con la fecha/hora actual.
		"""
		from django.utils import timezone
		
		self.is_used = True
		self.used_at = timezone.now()
		self.save(update_fields=['is_used', 'used_at'])



class LoginAttempt(TimeStampedModel):
	"""
	Modelo para rastrear intentos de login (exitosos y fallidos).
	
	Se usa para implementar protección contra brute force attacks.
	"""
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='login_attempts',
	)
	email_attempted = models.EmailField()
	ip_address = models.GenericIPAddressField()
	user_agent = models.TextField(blank=True)
	was_successful = models.BooleanField(default=False)
	failure_reason = models.CharField(max_length=50, blank=True)
	attempted_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = 'login_attempts'
		ordering = ['-attempted_at']
		indexes = [
			models.Index(fields=['email_attempted', 'attempted_at']),
			models.Index(fields=['ip_address', 'attempted_at']),
			models.Index(fields=['was_successful', 'attempted_at']),
		]

	def __str__(self) -> str:
		status = 'SUCCESS' if self.was_successful else 'FAILED'
		return f'{status}: {self.email_attempted} from {self.ip_address}'

	@staticmethod
	def get_recent_failures(email: str, minutes: int = 5) -> int:
		"""
		Obtiene el número de intentos fallidos recientes para un email.

		Args:
			email: Email del usuario
			minutes: Ventana de tiempo en minutos (default: 5)

		Returns:
			int: Número de intentos fallidos
		"""
		from django.utils import timezone

		time_threshold = timezone.now() - timezone.timedelta(minutes=minutes)
		
		return LoginAttempt.objects.filter(
			email_attempted__iexact=email,
			was_successful=False,
			attempted_at__gte=time_threshold,
		).count()

	@staticmethod
	def is_blocked(email: str, max_attempts: int = 5, window_minutes: int = 5) -> tuple[bool, int]:
		"""
		Verifica si un email está bloqueado por intentos fallidos.

		Args:
			email: Email del usuario
			max_attempts: Número máximo de intentos permitidos (default: 5)
			window_minutes: Ventana de tiempo en minutos (default: 5)

		Returns:
			tuple: (is_blocked: bool, remaining_minutes: int)
		"""
		from django.utils import timezone
		import math

		time_threshold = timezone.now() - timezone.timedelta(minutes=window_minutes)
		
		# Contar intentos fallidos en la ventana de tiempo
		failed_attempts = LoginAttempt.objects.filter(
			email_attempted__iexact=email,
			was_successful=False,
			attempted_at__gte=time_threshold,
		).count()

		if failed_attempts >= max_attempts:
			# Obtener el intento más antiguo en la ventana
			oldest_attempt = LoginAttempt.objects.filter(
				email_attempted__iexact=email,
				was_successful=False,
				attempted_at__gte=time_threshold,
			).order_by('attempted_at').first()

			if oldest_attempt:
				# Calcular minutos restantes hasta que expire el bloqueo
				unlock_time = oldest_attempt.attempted_at + timezone.timedelta(minutes=window_minutes)
				remaining = (unlock_time - timezone.now()).total_seconds() / 60
				remaining_minutes = max(1, math.ceil(remaining))  # Redondear hacia arriba
				return True, remaining_minutes

		return False, 0

	@staticmethod
	def clear_failed_attempts(email: str) -> None:
		"""
		Limpia los intentos fallidos de un email después de un login exitoso.

		Args:
			email: Email del usuario
		"""
		LoginAttempt.objects.filter(
			email_attempted__iexact=email,
			was_successful=False,
		).delete()



class AuthChallenge(TimeStampedModel):
	"""
	Modelo para almacenar tokens temporales de autenticación.
	
	Se usa para vincular el paso de login inicial con la verificación 2FA,
	evitando que el usuario tenga que enviar email+password dos veces.
	"""
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='auth_challenges',
	)
	challenge_token = models.CharField(max_length=64, unique=True, db_index=True)
	purpose = models.CharField(max_length=20, default='2fa_login')
	expires_at = models.DateTimeField()
	is_used = models.BooleanField(default=False)
	used_at = models.DateTimeField(null=True, blank=True)
	ip_address = models.GenericIPAddressField(null=True, blank=True)
	user_agent = models.TextField(blank=True)
	# Datos adicionales para completar el login después de 2FA
	institution_id = models.IntegerField(null=True, blank=True)
	role = models.CharField(max_length=100, blank=True)

	class Meta:
		db_table = 'auth_challenges'
		ordering = ['-created_at']
		indexes = [
			models.Index(fields=['challenge_token', 'is_used']),
			models.Index(fields=['user', 'is_used', 'expires_at']),
		]

	def __str__(self) -> str:
		return f'AuthChallenge for {self.user.email} (used: {self.is_used})'

	def is_valid(self) -> bool:
		"""
		Verifica si el challenge token es válido.
		
		Un token es válido si:
		- No ha sido usado
		- No ha expirado
		
		Returns:
			bool: True si el token es válido
		"""
		from django.utils import timezone
		
		if self.is_used:
			return False
		
		if timezone.now() > self.expires_at:
			return False
		
		return True

	def mark_as_used(self) -> None:
		"""
		Marca el challenge token como usado.
		"""
		from django.utils import timezone
		
		self.is_used = True
		self.used_at = timezone.now()
		self.save(update_fields=['is_used', 'used_at'])


class EmailTwoFactorCode(TimeStampedModel):
	"""
	Modelo para almacenar códigos OTP enviados por email para 2FA.
	
	Los códigos tienen una duración de 5 minutos y máximo 3 intentos.
	"""
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='email_2fa_codes',
	)
	code_hash = models.CharField(max_length=128)  # SHA256 hash del código
	purpose = models.CharField(max_length=20, default='login')
	expires_at = models.DateTimeField()
	attempts = models.IntegerField(default=0)
	max_attempts = models.IntegerField(default=3)
	is_used = models.BooleanField(default=False)
	used_at = models.DateTimeField(null=True, blank=True)
	challenge_token = models.CharField(max_length=64, unique=True, db_index=True)
	ip_address = models.GenericIPAddressField(null=True, blank=True)
	user_agent = models.TextField(blank=True, default='')

	class Meta:
		db_table = 'email_two_factor_codes'
		ordering = ['-created_at']
		indexes = [
			models.Index(fields=['challenge_token', 'is_used']),
			models.Index(fields=['user', 'is_used', 'expires_at']),
		]

	def __str__(self) -> str:
		return f'EmailTwoFactorCode for {self.user.email} (used: {self.is_used})'

	def is_valid(self) -> bool:
		"""
		Verifica si el código es válido.
		
		Un código es válido si:
		- No ha sido usado
		- No ha expirado
		- No ha excedido el máximo de intentos
		
		Returns:
			bool: True si el código es válido
		"""
		from django.utils import timezone
		
		if self.is_used:
			return False
		
		if timezone.now() > self.expires_at:
			return False
		
		if self.attempts >= self.max_attempts:
			return False
		
		return True

	def mark_as_used(self) -> None:
		"""
		Marca el código como usado.
		"""
		from django.utils import timezone
		
		self.is_used = True
		self.used_at = timezone.now()
		self.save(update_fields=['is_used', 'used_at'])


class TwoFactorAuth(TimeStampedModel):
	"""
	Modelo para almacenar configuración de autenticación de dos factores (2FA).
	
	Cada usuario puede tener una configuración 2FA con:
	- Secret key para TOTP
	- Códigos de respaldo
	- Estado de habilitación
	"""
	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='two_factor',
	)
	secret_key = models.CharField(max_length=32)
	is_enabled = models.BooleanField(default=False)
	backup_codes = models.JSONField(default=list)
	enabled_at = models.DateTimeField(null=True, blank=True)
	last_used_at = models.DateTimeField(null=True, blank=True)
	# Método de 2FA: 'totp' (app autenticadora) o 'email' (código por correo)
	method = models.CharField(
		max_length=20,
		choices=[
			('totp', 'App Autenticadora'),
			('email', 'Código por Email'),
		],
		default='totp'
	)

	class Meta:
		db_table = 'two_factor_auth'
		ordering = ['-created_at']

	def __str__(self) -> str:
		status = 'ENABLED' if self.is_enabled else 'DISABLED'
		return f'2FA for {self.user.email}: {status}'

	def generate_secret(self) -> str:
		"""
		Genera una nueva secret key para TOTP.

		Returns:
			str: Secret key en formato base32
		"""
		import pyotp
		self.secret_key = pyotp.random_base32()
		return self.secret_key

	def verify_token(self, token: str) -> bool:
		"""
		Verifica un código TOTP.

		Args:
			token: Código de 6 dígitos

		Returns:
			bool: True si el token es válido
		"""
		import pyotp
		totp = pyotp.TOTP(self.secret_key)
		return totp.verify(token, valid_window=1)

	def generate_backup_codes(self, count: int = 10) -> list[str]:
		"""
		Genera códigos de respaldo.

		Args:
			count: Número de códigos a generar (default: 10)

		Returns:
			list[str]: Lista de códigos de respaldo
		"""
		import secrets
		codes = []
		for _ in range(count):
			# Generar código de 8 caracteres alfanuméricos
			code = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(8))
			# Formatear como XXXX-XXXX
			formatted_code = f'{code[:4]}-{code[4:]}'
			codes.append(formatted_code)
		
		self.backup_codes = codes
		return codes

	def verify_backup_code(self, code: str) -> bool:
		"""
		Verifica y consume un código de respaldo.

		Args:
			code: Código de respaldo

		Returns:
			bool: True si el código es válido
		"""
		# Normalizar código (remover espacios y guiones)
		normalized_code = code.replace(' ', '').replace('-', '').upper()
		
		for backup_code in self.backup_codes:
			normalized_backup = backup_code.replace(' ', '').replace('-', '').upper()
			if normalized_code == normalized_backup:
				# Remover el código usado
				self.backup_codes.remove(backup_code)
				self.save(update_fields=['backup_codes'])
				return True
		
		return False

	def get_provisioning_uri(self, user_email: str, issuer_name: str = 'Sistema Bancario') -> str:
		"""
		Genera la URI de provisioning para QR code.

		Args:
			user_email: Email del usuario
			issuer_name: Nombre de la aplicación (default: 'Sistema Bancario')

		Returns:
			str: URI de provisioning
		"""
		import pyotp
		totp = pyotp.TOTP(self.secret_key)
		return totp.provisioning_uri(name=user_email, issuer_name=issuer_name)
# Parte erick sprint 0
class Permission(TimeStampedModel):
	code = models.CharField(max_length=80, unique=True)
	name = models.CharField(max_length=120)
	description = models.TextField(blank=True)
	is_active = models.BooleanField(default=True)

	class Meta:
		db_table = 'permissions'
		ordering = ['name']

	def __str__(self) -> str:
		return f'{self.code} - {self.name}'


class Role(TenantModel):
	"""
	Rol dinámico con permisos asignables.
	
	Hereda de TenantModel para aislamiento automático por tenant.
	El campo institution se hereda de TenantModel.
	"""
	name = models.CharField(max_length=100)
	description = models.TextField(blank=True)
	is_active = models.BooleanField(default=True)
	permissions = models.ManyToManyField(
		Permission,
		blank=True,
		related_name='roles',
	)

	class Meta:
		db_table = 'roles'
		ordering = ['name']
		constraints = [
			models.UniqueConstraint(
				fields=['institution', 'name'],
				name='uniq_role_name_per_institution',
			)
		]

	def __str__(self) -> str:
		return f'{self.name} ({self.institution.slug})'


# ============================================================
# SPRINT 1: UserProfile y UserRole
# Sistema de perfiles de usuario y asignación de roles dinámicos
# ============================================================

class UserProfile(TimeStampedModel):
	"""
	Perfil extendido de usuario con tipo de usuario y datos adicionales.
	
	Tipos de usuario:
	- saas_admin: Superadministrador SaaS (gestiona toda la plataforma)
	- tenant_user: Usuario de tenant (pertenece a una institución financiera)
	"""
	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='profile'
	)
	user_type = models.CharField(
		max_length=20,
		choices=[
			('saas_admin', 'Superadministrador SaaS'),
			('tenant_user', 'Usuario de Tenant'),
		],
		default='tenant_user',
		help_text='Tipo de usuario en el sistema'
	)
	
	# Datos de contacto
	phone = models.CharField(max_length=20, blank=True)
	
	# Datos laborales
	position = models.CharField(max_length=100, blank=True, help_text='Cargo o posición')
	department = models.CharField(max_length=100, blank=True, help_text='Departamento')
	
	# Preferencias
	avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
	timezone = models.CharField(max_length=50, default='America/La_Paz')
	language = models.CharField(max_length=10, default='es')
	notification_preferences = models.JSONField(default=dict, blank=True)
	
	class Meta:
		db_table = 'user_profiles'
		ordering = ['-created_at']
	
	def __str__(self) -> str:
		return f'Profile: {self.user.email} ({self.user_type})'
	
	def is_saas_admin(self) -> bool:
		"""
		Verifica si el usuario es superadministrador SaaS.
		
		Returns:
			bool: True si es superadmin SaaS
		"""
		return self.user_type == 'saas_admin'
	
	def get_permissions_in_institution(self, institution):
		"""
		Obtiene todos los permisos del usuario en una institución específica.
		
		Args:
			institution: Instancia de FinancialInstitution
		
		Returns:
			QuerySet de Permission
		"""
		if self.is_saas_admin():
			# Superadmin tiene todos los permisos
			return Permission.objects.filter(is_active=True)
		
		# Obtener roles activos del usuario en la institución
		user_roles = self.user.user_roles.filter(
			institution=institution,
			is_active=True
		)
		
		# Obtener permisos únicos de todos los roles
		return Permission.objects.filter(
			roles__user_assignments__in=user_roles,
			is_active=True
		).distinct()
	
	def has_permission(self, permission_code: str, institution) -> bool:
		"""
		Verifica si el usuario tiene un permiso específico en una institución.
		
		Args:
			permission_code: Código del permiso (ej: 'users.view')
			institution: Instancia de FinancialInstitution
		
		Returns:
			bool: True si tiene el permiso
		"""
		if self.is_saas_admin():
			return True
		
		return self.get_permissions_in_institution(institution).filter(
			code=permission_code
		).exists()


class UserRole(TimeStampedModel):
	"""
	Asignación de roles a usuarios en instituciones específicas.
	
	Un usuario puede tener múltiples roles en una institución.
	Reemplaza el campo 'role' hardcoded de FinancialInstitutionMembership.
	"""
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='user_roles'
	)
	role = models.ForeignKey(
		Role,
		on_delete=models.CASCADE,
		related_name='user_assignments'
	)
	institution = models.ForeignKey(
		FinancialInstitution,
		on_delete=models.CASCADE,
		related_name='user_role_assignments'
	)
	is_active = models.BooleanField(default=True)
	assigned_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='role_assignments_made',
		help_text='Usuario que asignó este rol'
	)
	
	class Meta:
		db_table = 'user_roles'
		ordering = ['-created_at']
		constraints = [
			models.UniqueConstraint(
				fields=['user', 'role', 'institution'],
				name='uniq_user_role_institution'
			)
		]
		indexes = [
			models.Index(fields=['user', 'institution', 'is_active']),
			models.Index(fields=['role', 'is_active']),
		]
	
	def __str__(self) -> str:
		return f'{self.user.email} -> {self.role.name} @ {self.institution.slug}'
