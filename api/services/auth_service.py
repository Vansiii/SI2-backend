from dataclasses import dataclass
from typing import Optional

from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from api.models import FinancialInstitutionMembership, LoginAttempt, TwoFactorAuth


@dataclass(frozen=True)
class LoginInput:
    """Input para login de usuario."""
    email: str
    password: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


@dataclass(frozen=True)
class LoginResult:
    """Resultado del login."""
    user: object
    access_token: str
    refresh_token: str
    institution: object
    role: str
    requires_2fa: bool = False
    challenge_token: str = ''
    expires_in: int = 0
    method: str = 'totp'  # Método de 2FA: 'totp' o 'email'


class LoginService:
    """Servicio para autenticación de usuarios."""

    def execute(self, payload: LoginInput) -> LoginResult:
        """
        Autentica un usuario y genera tokens JWT.

        Args:
            payload: LoginInput con credenciales

        Returns:
            LoginResult con tokens y datos del usuario

        Raises:
            serializers.ValidationError: Si las credenciales son inválidas o la cuenta está bloqueada
        """
        User = get_user_model()

        # Normalizar email
        email = payload.email.strip().lower()

        # Verificar si la cuenta está bloqueada por intentos fallidos
        is_blocked, remaining_minutes = LoginAttempt.is_blocked(email)
        if is_blocked:
            # Enviar email de notificación de bloqueo
            try:
                user_for_notification = User.objects.filter(email__iexact=email).first()
                if user_for_notification:
                    from api.services.email_service import EmailInput, EmailService
                    from django.utils import timezone
                    
                    # Obtener el último intento para información del email
                    last_attempt = LoginAttempt.objects.filter(
                        email_attempted__iexact=email,
                        was_successful=False
                    ).order_by('-attempted_at').first()
                    
                    email_service = EmailService()
                    email_input = EmailInput(
                        to_email=user_for_notification.email,
                        subject='Alerta de seguridad: Cuenta bloqueada',
                        template_name='emails/account_locked.html',
                        context={
                            'user_name': user_for_notification.first_name or user_for_notification.email,
                            'failed_attempts': LoginAttempt.get_recent_failures(email),
                            'lockout_minutes': remaining_minutes,
                            'ip_address': last_attempt.ip_address if last_attempt else 'Desconocida',
                            'attempted_at': last_attempt.attempted_at.strftime('%d/%m/%Y %H:%M:%S') if last_attempt else 'Desconocido',
                        }
                    )
                    # No fallar si el email no se envía
                    email_service.execute(email_input)
            except Exception:
                # Silenciar errores de email para no bloquear el flujo
                pass
            
            raise serializers.ValidationError(
                {
                    'detail': f'Cuenta bloqueada temporalmente por múltiples intentos fallidos. '
                              f'Intenta nuevamente en {remaining_minutes} minuto(s).'
                },
                code='account_locked'
            )

        # Buscar usuario por email
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            # Registrar intento fallido
            LoginAttempt.objects.create(
                user=None,
                email_attempted=email,
                ip_address=payload.ip_address or '0.0.0.0',
                user_agent=payload.user_agent or '',
                was_successful=False,
                failure_reason='user_not_found',
            )
            raise serializers.ValidationError(
                {'detail': 'Credenciales inválidas.'},
                code='invalid_credentials'
            )

        # Autenticar con username (Django usa username para authenticate)
        authenticated_user = authenticate(
            username=user.username,
            password=payload.password
        )

        if authenticated_user is None:
            # Registrar intento fallido
            LoginAttempt.objects.create(
                user=user,
                email_attempted=email,
                ip_address=payload.ip_address or '0.0.0.0',
                user_agent=payload.user_agent or '',
                was_successful=False,
                failure_reason='invalid_password',
            )
            raise serializers.ValidationError(
                {'detail': 'Credenciales inválidas.'},
                code='invalid_credentials'
            )

        # Verificar que el usuario esté activo
        if not authenticated_user.is_active:
            # Registrar intento fallido
            LoginAttempt.objects.create(
                user=authenticated_user,
                email_attempted=email,
                ip_address=payload.ip_address or '0.0.0.0',
                user_agent=payload.user_agent or '',
                was_successful=False,
                failure_reason='inactive_account',
            )
            raise serializers.ValidationError(
                {'detail': 'Esta cuenta está inactiva.'},
                code='inactive_account'
            )

        # Obtener membership activa del usuario
        try:
            membership = FinancialInstitutionMembership.objects.select_related(
                'institution'
            ).get(
                user=authenticated_user,
                is_active=True
            )
        except FinancialInstitutionMembership.DoesNotExist:
            # Registrar intento fallido
            LoginAttempt.objects.create(
                user=authenticated_user,
                email_attempted=email,
                ip_address=payload.ip_address or '0.0.0.0',
                user_agent=payload.user_agent or '',
                was_successful=False,
                failure_reason='no_active_membership',
            )
            raise serializers.ValidationError(
                {'detail': 'No tienes una membresía activa en ninguna institución.'},
                code='no_active_membership'
            )

        # Generar tokens JWT
        refresh = RefreshToken.for_user(authenticated_user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        # Registrar intento exitoso
        LoginAttempt.objects.create(
            user=authenticated_user,
            email_attempted=email,
            ip_address=payload.ip_address or '0.0.0.0',
            user_agent=payload.user_agent or '',
            was_successful=True,
            failure_reason='',
        )

        # Limpiar intentos fallidos anteriores
        LoginAttempt.clear_failed_attempts(email)

        # Verificar si el usuario tiene 2FA habilitado
        try:
            two_factor = TwoFactorAuth.objects.get(user=authenticated_user, is_enabled=True)
            # Usuario tiene 2FA habilitado - Generar challenge token
            from api.models import AuthChallenge
            from django.utils import timezone
            import secrets
            
            # Generar challenge token único
            challenge_token = secrets.token_urlsafe(32)
            
            # Calcular expiración (5 minutos)
            expires_at = timezone.now() + timezone.timedelta(minutes=5)
            
            # Invalidar challenges anteriores no usados del mismo usuario
            AuthChallenge.objects.filter(
                user=authenticated_user,
                is_used=False,
                purpose='2fa_login'
            ).update(is_used=True)
            
            # Crear nuevo challenge
            AuthChallenge.objects.create(
                user=authenticated_user,
                challenge_token=challenge_token,
                purpose='2fa_login',
                expires_at=expires_at,
                ip_address=payload.ip_address or '0.0.0.0',
                user_agent=payload.user_agent or '',
                institution_id=membership.institution.id,
                role=membership.role,
            )
            
            # Si el método es EMAIL, generar y enviar código
            if two_factor.method == 'email':
                from api.services.email_two_factor_service import (
                    EmailTwoFactorSendInput,
                    EmailTwoFactorSendService
                )
                
                send_service = EmailTwoFactorSendService()
                send_result = send_service.execute(
                    EmailTwoFactorSendInput(
                        user=authenticated_user,
                        challenge_token=challenge_token,
                        purpose='login',
                        ip_address=payload.ip_address,
                        user_agent=payload.user_agent,
                    )
                )
            
            return LoginResult(
                user=authenticated_user,
                access_token='',  # Vacío hasta verificar 2FA
                refresh_token='',  # Vacío hasta verificar 2FA
                institution=membership.institution,
                role=membership.role,
                requires_2fa=True,
                challenge_token=challenge_token,
                expires_in=300,  # 5 minutos en segundos
                method=two_factor.method,  # Incluir método de 2FA
            )
        except TwoFactorAuth.DoesNotExist:
            # Usuario NO tiene 2FA - retornar tokens normalmente
            pass

        return LoginResult(
            user=authenticated_user,
            access_token=access_token,
            refresh_token=refresh_token,
            institution=membership.institution,
            role=membership.role,
            requires_2fa=False,
        )



@dataclass(frozen=True)
class TwoFactorLoginInput:
    """Input para verificar 2FA en login."""
    challenge_token: str
    totp_code: str
    is_backup_code: bool = False
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


@dataclass(frozen=True)
class TwoFactorLoginResult:
    """Resultado de login con 2FA."""
    user: object
    access_token: str
    refresh_token: str
    institution: object
    role: str


class TwoFactorLoginService:
    """Servicio para login con verificación 2FA."""

    def execute(self, payload: TwoFactorLoginInput) -> TwoFactorLoginResult:
        """
        Verifica el código 2FA y completa el login usando challenge token.

        Args:
            payload: TwoFactorLoginInput con challenge token y código 2FA

        Returns:
            TwoFactorLoginResult con tokens JWT

        Raises:
            serializers.ValidationError: Si el challenge token o el código son inválidos
        """
        from django.utils import timezone
        from api.models import AuthChallenge
        
        User = get_user_model()

        # Buscar challenge token
        try:
            challenge = AuthChallenge.objects.select_related('user').get(
                challenge_token=payload.challenge_token,
                purpose='2fa_login',
                is_used=False
            )
        except AuthChallenge.DoesNotExist:
            raise serializers.ValidationError(
                {'detail': 'Token de autenticación inválido o expirado.'},
                code='invalid_challenge'
            )

        # Verificar que no haya expirado
        if not challenge.is_valid():
            raise serializers.ValidationError(
                {'detail': 'Token de autenticación expirado. Inicia sesión nuevamente.'},
                code='challenge_expired'
            )

        # Obtener usuario del challenge
        authenticated_user = challenge.user

        # Verificar que el usuario esté activo
        if not authenticated_user.is_active:
            raise serializers.ValidationError(
                {'detail': 'Esta cuenta está inactiva.'},
                code='inactive_account'
            )

        # Obtener configuración 2FA
        try:
            two_factor = TwoFactorAuth.objects.get(user=authenticated_user, is_enabled=True)
        except TwoFactorAuth.DoesNotExist:
            raise serializers.ValidationError(
                {'detail': '2FA no está habilitado para este usuario.'},
                code='2fa_not_enabled'
            )

        # Verificar código 2FA según el método
        if two_factor.method == 'email':
            # Verificar código de email
            from api.services.email_two_factor_service import (
                EmailTwoFactorVerifyInput,
                EmailTwoFactorVerifyService
            )
            
            verify_service = EmailTwoFactorVerifyService()
            verify_result = verify_service.execute(
                EmailTwoFactorVerifyInput(
                    challenge_token=payload.challenge_token,
                    code=payload.totp_code,
                )
            )
        else:
            # Verificar código TOTP o backup code
            if payload.is_backup_code:
                # Verificar código de respaldo
                if not two_factor.verify_backup_code(payload.totp_code):
                    raise serializers.ValidationError(
                        {'detail': 'Código de respaldo inválido.'},
                        code='invalid_backup_code'
                    )
            else:
                # Verificar código TOTP
                if not two_factor.verify_token(payload.totp_code):
                    raise serializers.ValidationError(
                        {'detail': 'Código inválido. Verifica e intenta nuevamente.'},
                        code='invalid_token'
                    )

        # Actualizar último uso de 2FA
        two_factor.last_used_at = timezone.now()
        two_factor.save(update_fields=['last_used_at'])

        # Marcar challenge como usado
        challenge.mark_as_used()

        # Obtener membership activa (usar datos del challenge)
        try:
            membership = FinancialInstitutionMembership.objects.select_related(
                'institution'
            ).get(
                user=authenticated_user,
                institution_id=challenge.institution_id,
                is_active=True
            )
        except FinancialInstitutionMembership.DoesNotExist:
            raise serializers.ValidationError(
                {'detail': 'No tienes una membresía activa en ninguna institución.'},
                code='no_active_membership'
            )

        # Generar tokens JWT
        refresh = RefreshToken.for_user(authenticated_user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        # Registrar intento exitoso
        LoginAttempt.objects.create(
            user=authenticated_user,
            email_attempted=authenticated_user.email,
            ip_address=payload.ip_address or '0.0.0.0',
            user_agent=payload.user_agent or '',
            was_successful=True,
            failure_reason='',
        )

        # Limpiar intentos fallidos anteriores
        LoginAttempt.clear_failed_attempts(authenticated_user.email)

        return TwoFactorLoginResult(
            user=authenticated_user,
            access_token=access_token,
            refresh_token=refresh_token,
            institution=membership.institution,
            role=membership.role,
        )
