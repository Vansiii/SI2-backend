"""
Servicios para recuperación de contraseña.
"""
import secrets
from dataclasses import dataclass
from typing import Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from api.models import PasswordResetToken
from api.services.email_service import EmailInput, EmailService


@dataclass(frozen=True)
class PasswordResetRequestInput:
    """Input para solicitud de recuperación de contraseña."""
    email: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


@dataclass(frozen=True)
class PasswordResetRequestResult:
    """Resultado de solicitud de recuperación."""
    success: bool
    message: str


class PasswordResetRequestService:
    """Servicio para solicitar recuperación de contraseña."""

    def execute(self, payload: PasswordResetRequestInput) -> PasswordResetRequestResult:
        """
        Procesa una solicitud de recuperación de contraseña.

        Por seguridad, siempre retorna success=True incluso si el email no existe.
        Esto previene la enumeración de usuarios.

        Args:
            payload: PasswordResetRequestInput con email

        Returns:
            PasswordResetRequestResult con resultado
        """
        User = get_user_model()
        email = payload.email.strip().lower()

        # Buscar usuario por email (case-insensitive)
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            # Por seguridad, retornar success=True aunque el usuario no exista
            return PasswordResetRequestResult(
                success=True,
                message='Si el correo existe, recibirás instrucciones para recuperar tu contraseña.'
            )

        # Verificar que el usuario esté activo
        if not user.is_active:
            # Por seguridad, retornar el mismo mensaje
            return PasswordResetRequestResult(
                success=True,
                message='Si el correo existe, recibirás instrucciones para recuperar tu contraseña.'
            )

        # Generar token único
        token = secrets.token_urlsafe(32)

        # Calcular fecha de expiración (1 hora)
        expires_at = timezone.now() + timezone.timedelta(hours=1)

        # Crear registro de token
        reset_token = PasswordResetToken.objects.create(
            user=user,
            token=token,
            expires_at=expires_at,
            ip_address=payload.ip_address,
            user_agent=payload.user_agent,
        )

        # Construir link de recuperación
        reset_link = f'{settings.FRONTEND_URL}/reset-password?token={token}'

        # Enviar email
        email_service = EmailService()
        email_input = EmailInput(
            to_email=user.email,
            subject='Recuperación de contraseña',
            template_name='emails/password_reset.html',
            context={
                'user_name': user.first_name or user.email,
                'reset_link': reset_link,
                'expires_in_minutes': 60,
            }
        )

        email_result = email_service.execute(email_input)

        if not email_result.success:
            # Si falla el envío de email, eliminar el token
            reset_token.delete()
            raise serializers.ValidationError(
                {'detail': 'Error al enviar el correo. Intenta nuevamente.'},
                code='email_send_failed'
            )

        return PasswordResetRequestResult(
            success=True,
            message='Si el correo existe, recibirás instrucciones para recuperar tu contraseña.'
        )


@dataclass(frozen=True)
class PasswordResetValidateInput:
    """Input para validar token de recuperación."""
    token: str


@dataclass(frozen=True)
class PasswordResetValidateResult:
    """Resultado de validación de token."""
    valid: bool
    message: str


class PasswordResetValidateService:
    """Servicio para validar token de recuperación."""

    def execute(self, payload: PasswordResetValidateInput) -> PasswordResetValidateResult:
        """
        Valida un token de recuperación de contraseña.

        Args:
            payload: PasswordResetValidateInput con token

        Returns:
            PasswordResetValidateResult con resultado
        """
        token = payload.token.strip()

        try:
            reset_token = PasswordResetToken.objects.get(token=token)
        except PasswordResetToken.DoesNotExist:
            return PasswordResetValidateResult(
                valid=False,
                message='Token inválido o expirado.'
            )

        if not reset_token.is_valid():
            return PasswordResetValidateResult(
                valid=False,
                message='Token inválido o expirado.'
            )

        return PasswordResetValidateResult(
            valid=True,
            message='Token válido.'
        )


@dataclass(frozen=True)
class PasswordResetConfirmInput:
    """Input para confirmar nueva contraseña."""
    token: str
    new_password: str


@dataclass(frozen=True)
class PasswordResetConfirmResult:
    """Resultado de confirmación de nueva contraseña."""
    success: bool
    user: object


class PasswordResetConfirmService:
    """Servicio para confirmar nueva contraseña."""

    def execute(self, payload: PasswordResetConfirmInput) -> PasswordResetConfirmResult:
        """
        Confirma el cambio de contraseña.

        Args:
            payload: PasswordResetConfirmInput con token y nueva contraseña

        Returns:
            PasswordResetConfirmResult con resultado

        Raises:
            serializers.ValidationError: Si el token es inválido o la contraseña no cumple requisitos
        """
        from django.contrib.auth.password_validation import validate_password

        token = payload.token.strip()

        # Buscar token
        try:
            reset_token = PasswordResetToken.objects.select_related('user').get(token=token)
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError(
                {'detail': 'Token inválido o expirado.'},
                code='invalid_token'
            )

        # Validar token
        if not reset_token.is_valid():
            raise serializers.ValidationError(
                {'detail': 'Token inválido o expirado.'},
                code='invalid_token'
            )

        user = reset_token.user

        # Validar nueva contraseña con validadores de Django
        try:
            validate_password(payload.new_password, user=user)
        except Exception as e:
            raise serializers.ValidationError(
                {'new_password': list(e.messages)},
                code='invalid_password'
            )

        # Actualizar contraseña
        user.set_password(payload.new_password)
        user.save(update_fields=['password'])

        # Marcar token como usado
        reset_token.mark_as_used()

        # Enviar email de confirmación
        email_service = EmailService()
        email_input = EmailInput(
            to_email=user.email,
            subject='Contraseña actualizada',
            template_name='emails/password_changed.html',
            context={
                'user_name': user.first_name or user.email,
            }
        )
        email_service.execute(email_input)

        return PasswordResetConfirmResult(
            success=True,
            user=user
        )
