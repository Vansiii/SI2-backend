from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from api.services.auth_service import LoginInput, LoginService


# ============================================================
# LOGIN
# ============================================================

class LoginSerializer(serializers.Serializer):
    """Serializer para login de usuario."""
    
    email = serializers.EmailField(
        max_length=254,
        required=True,
        error_messages={
            'required': 'El correo electrónico es obligatorio.',
            'invalid': 'Ingresa un correo electrónico válido.',
            'blank': 'El correo electrónico no puede estar vacío.',
        }
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        trim_whitespace=False,
        error_messages={
            'required': 'La contraseña es obligatoria.',
            'blank': 'La contraseña no puede estar vacía.',
        }
    )

    def validate_email(self, value):
        """Normalizar y validar email."""
        normalized = value.strip().lower()
        if not normalized:
            raise serializers.ValidationError('El correo electrónico no puede estar vacío.')
        return normalized

    def validate_password(self, value):
        """Validar que la contraseña no esté vacía."""
        if not value:
            raise serializers.ValidationError('La contraseña no puede estar vacía.')
        return value

    def create(self, validated_data):
        """Ejecutar el servicio de login."""
        # Obtener IP y user agent del contexto
        request = self.context.get('request')
        ip_address = None
        user_agent = None
        
        if request:
            ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')

        # Crear input para el servicio
        login_input = LoginInput(
            email=validated_data['email'],
            password=validated_data['password'],
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Ejecutar servicio
        service = LoginService()
        return service.execute(login_input)


# ============================================================
# LOGOUT
# ============================================================

class LogoutSerializer(serializers.Serializer):
    """Serializer para logout de usuario."""
    
    refresh = serializers.CharField(
        required=True,
        error_messages={
            'required': 'El token de actualización es obligatorio.',
            'blank': 'El token de actualización no puede estar vacío.',
        }
    )

    def validate_refresh(self, value):
        """Validar que el token no esté vacío."""
        if not value or not value.strip():
            raise serializers.ValidationError('El token de actualización no puede estar vacío.')
        return value.strip()

    def save(self):
        """Agregar el refresh token a la blacklist."""
        try:
            token = RefreshToken(self.validated_data['refresh'])
            token.blacklist()
            return {'message': 'Sesión cerrada exitosamente.'}
        except Exception as e:
            raise serializers.ValidationError(
                {'detail': 'Token inválido o ya ha sido revocado.'},
                code='invalid_token'
            )


# ============================================================
# PASSWORD RESET
# ============================================================

class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer para solicitar recuperación de contraseña."""
    
    email = serializers.EmailField(
        max_length=254,
        required=True,
        error_messages={
            'required': 'El correo electrónico es obligatorio.',
            'invalid': 'Ingresa un correo electrónico válido.',
            'blank': 'El correo electrónico no puede estar vacío.',
        }
    )

    def validate_email(self, value):
        """Normalizar email."""
        normalized = value.strip().lower()
        if not normalized:
            raise serializers.ValidationError('El correo electrónico no puede estar vacío.')
        return normalized

    def create(self, validated_data):
        """Ejecutar el servicio de solicitud de recuperación."""
        from api.services.password_reset_service import (
            PasswordResetRequestInput,
            PasswordResetRequestService,
        )
        
        # Obtener IP y user agent del contexto
        request = self.context.get('request')
        ip_address = None
        user_agent = None
        
        if request:
            ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')

        # Crear input para el servicio
        reset_input = PasswordResetRequestInput(
            email=validated_data['email'],
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Ejecutar servicio
        service = PasswordResetRequestService()
        return service.execute(reset_input)


class PasswordResetValidateSerializer(serializers.Serializer):
    """Serializer para validar token de recuperación."""
    
    token = serializers.CharField(
        required=True,
        error_messages={
            'required': 'El token es obligatorio.',
            'blank': 'El token no puede estar vacío.',
        }
    )

    def validate_token(self, value):
        """Validar que el token no esté vacío."""
        if not value or not value.strip():
            raise serializers.ValidationError('El token no puede estar vacío.')
        return value.strip()

    def validate(self, attrs):
        """Validar el token con el servicio."""
        from api.services.password_reset_service import (
            PasswordResetValidateInput,
            PasswordResetValidateService,
        )
        
        validate_input = PasswordResetValidateInput(token=attrs['token'])
        service = PasswordResetValidateService()
        result = service.execute(validate_input)
        
        attrs['valid'] = result.valid
        attrs['message'] = result.message
        
        return attrs


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer para confirmar nueva contraseña."""
    
    token = serializers.CharField(
        required=True,
        error_messages={
            'required': 'El token es obligatorio.',
            'blank': 'El token no puede estar vacío.',
        }
    )
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        trim_whitespace=False,
        error_messages={
            'required': 'La nueva contraseña es obligatoria.',
            'blank': 'La nueva contraseña no puede estar vacía.',
        }
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        trim_whitespace=False,
        error_messages={
            'required': 'La confirmación de contraseña es obligatoria.',
            'blank': 'La confirmación de contraseña no puede estar vacía.',
        }
    )

    def validate_token(self, value):
        """Validar que el token no esté vacío."""
        if not value or not value.strip():
            raise serializers.ValidationError('El token no puede estar vacío.')
        return value.strip()

    def validate_new_password(self, value):
        """Validar que la contraseña no esté vacía."""
        if not value:
            raise serializers.ValidationError('La nueva contraseña no puede estar vacía.')
        return value

    def validate(self, attrs):
        """Validar que las contraseñas coincidan."""
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': 'Las contraseñas no coinciden.'
            })
        return attrs

    def create(self, validated_data):
        """Ejecutar el servicio de confirmación de contraseña."""
        from api.services.password_reset_service import (
            PasswordResetConfirmInput,
            PasswordResetConfirmService,
        )
        
        confirm_input = PasswordResetConfirmInput(
            token=validated_data['token'],
            new_password=validated_data['new_password'],
        )

        service = PasswordResetConfirmService()
        return service.execute(confirm_input)


# ============================================================
# TWO-FACTOR AUTHENTICATION (2FA)
# ============================================================

class TwoFactorEnableSerializer(serializers.Serializer):
    """Serializer para habilitar 2FA."""
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        trim_whitespace=False,
        error_messages={
            'required': 'La contraseña es obligatoria.',
            'blank': 'La contraseña no puede estar vacía.',
        }
    )

    def validate_password(self, value):
        """Validar que la contraseña no esté vacía."""
        if not value:
            raise serializers.ValidationError('La contraseña no puede estar vacía.')
        return value

    def validate(self, attrs):
        """Validar la contraseña del usuario."""
        from django.contrib.auth import authenticate
        
        request = self.context.get('request')
        user = request.user
        
        # Verificar contraseña
        authenticated_user = authenticate(
            username=user.username,
            password=attrs['password']
        )
        
        if authenticated_user is None:
            raise serializers.ValidationError('Contraseña incorrecta.')
        
        return attrs

    def create(self, validated_data):
        """Ejecutar el servicio de habilitación de 2FA."""
        from api.services.two_factor_service import (
            TwoFactorEnableInput,
            TwoFactorEnableService,
        )
        
        # Obtener usuario del contexto
        request = self.context.get('request')
        user = request.user

        # Crear input para el servicio
        enable_input = TwoFactorEnableInput(user=user)

        # Ejecutar servicio
        service = TwoFactorEnableService()
        return service.execute(enable_input)


class TwoFactorVerifySerializer(serializers.Serializer):
    """Serializer para verificar y activar 2FA."""
    
    token = serializers.CharField(
        min_length=6,
        max_length=6,
        required=True,
        error_messages={
            'required': 'El código es obligatorio.',
            'blank': 'El código no puede estar vacío.',
            'min_length': 'El código debe tener 6 dígitos.',
            'max_length': 'El código debe tener 6 dígitos.',
        }
    )

    def validate_token(self, value):
        """Validar que el token sea numérico."""
        if not value.isdigit():
            raise serializers.ValidationError('El código debe contener solo números.')
        return value

    def create(self, validated_data):
        """Ejecutar el servicio de verificación de 2FA."""
        from api.services.two_factor_service import (
            TwoFactorVerifyInput,
            TwoFactorVerifyService,
        )
        
        # Obtener usuario del contexto
        request = self.context.get('request')
        user = request.user

        # Crear input para el servicio
        verify_input = TwoFactorVerifyInput(
            user=user,
            token=validated_data['token'],
        )

        # Ejecutar servicio
        service = TwoFactorVerifyService()
        return service.execute(verify_input)


class TwoFactorDisableSerializer(serializers.Serializer):
    """Serializer para deshabilitar 2FA."""
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        trim_whitespace=False,
        error_messages={
            'required': 'La contraseña es obligatoria.',
            'blank': 'La contraseña no puede estar vacía.',
        }
    )

    def validate_password(self, value):
        """Validar que la contraseña no esté vacía."""
        if not value:
            raise serializers.ValidationError('La contraseña no puede estar vacía.')
        return value

    def create(self, validated_data):
        """Ejecutar el servicio de deshabilitación de 2FA."""
        from api.services.two_factor_service import (
            TwoFactorDisableInput,
            TwoFactorDisableService,
        )
        
        # Obtener usuario del contexto
        request = self.context.get('request')
        user = request.user

        # Crear input para el servicio
        disable_input = TwoFactorDisableInput(
            user=user,
            password=validated_data['password'],
        )

        # Ejecutar servicio
        service = TwoFactorDisableService()
        return service.execute(disable_input)


class TwoFactorLoginSerializer(serializers.Serializer):
    """Serializer para verificar código 2FA en login."""
    
    token = serializers.CharField(
        required=True,
        error_messages={
            'required': 'El código es obligatorio.',
            'blank': 'El código no puede estar vacío.',
        }
    )
    is_backup_code = serializers.BooleanField(default=False)

    def validate_token(self, value):
        """Validar que el token no esté vacío."""
        if not value or not value.strip():
            raise serializers.ValidationError('El código no puede estar vacío.')
        return value.strip()



class TwoFactorLoginVerifySerializer(serializers.Serializer):
    """Serializer para verificar código 2FA durante login."""
    
    challenge_token = serializers.CharField(
        required=True,
        error_messages={
            'required': 'El token de autenticación es obligatorio.',
            'blank': 'El token de autenticación no puede estar vacío.',
        }
    )
    totp_code = serializers.CharField(
        required=True,
        error_messages={
            'required': 'El código 2FA es obligatorio.',
            'blank': 'El código 2FA no puede estar vacío.',
        }
    )
    is_backup_code = serializers.BooleanField(default=False)

    def validate_challenge_token(self, value):
        """Validar que el token no esté vacío."""
        if not value or not value.strip():
            raise serializers.ValidationError('El token de autenticación no puede estar vacío.')
        return value.strip()

    def validate_totp_code(self, value):
        """Validar que el código no esté vacío."""
        if not value or not value.strip():
            raise serializers.ValidationError('El código 2FA no puede estar vacío.')
        return value.strip()

    def create(self, validated_data):
        """Ejecutar el servicio de login con 2FA."""
        from api.services.auth_service import (
            TwoFactorLoginInput,
            TwoFactorLoginService,
        )
        
        # Obtener IP y user agent del contexto
        request = self.context.get('request')
        ip_address = None
        user_agent = None
        
        if request:
            ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')

        # Crear input para el servicio
        login_input = TwoFactorLoginInput(
            challenge_token=validated_data['challenge_token'],
            totp_code=validated_data['totp_code'],
            is_backup_code=validated_data.get('is_backup_code', False),
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Ejecutar servicio
        service = TwoFactorLoginService()
        return service.execute(login_input)



class TwoFactorRegenerateBackupCodesSerializer(serializers.Serializer):
    """Serializer para regenerar códigos de respaldo."""
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        trim_whitespace=False,
        error_messages={
            'required': 'La contraseña es obligatoria.',
            'blank': 'La contraseña no puede estar vacía.',
        }
    )

    def validate_password(self, value):
        """Validar que la contraseña no esté vacía."""
        if not value:
            raise serializers.ValidationError('La contraseña no puede estar vacía.')
        return value

    def create(self, validated_data):
        """Ejecutar el servicio de regeneración de códigos."""
        from api.services.two_factor_service import (
            TwoFactorRegenerateBackupCodesInput,
            TwoFactorRegenerateBackupCodesService,
        )
        
        # Obtener usuario del contexto
        request = self.context.get('request')
        user = request.user

        # Crear input para el servicio
        regenerate_input = TwoFactorRegenerateBackupCodesInput(
            user=user,
            password=validated_data['password'],
        )

        # Ejecutar servicio
        service = TwoFactorRegenerateBackupCodesService()
        return service.execute(regenerate_input)


# ============================================================
# EMAIL TWO-FACTOR AUTHENTICATION
# ============================================================

class EmailTwoFactorResendSerializer(serializers.Serializer):
    """Serializer para reenviar código 2FA por email."""
    
    challenge_token = serializers.CharField(
        required=True,
        error_messages={
            'required': 'El token de autenticación es obligatorio.',
            'blank': 'El token de autenticación no puede estar vacío.',
        }
    )

    def validate_challenge_token(self, value):
        """Validar que el token no esté vacío."""
        if not value or not value.strip():
            raise serializers.ValidationError('El token de autenticación no puede estar vacío.')
        return value.strip()

    def create(self, validated_data):
        """Ejecutar el servicio de reenvío de código."""
        from api.services.email_two_factor_service import (
            EmailTwoFactorResendInput,
            EmailTwoFactorResendService,
        )
        
        # Obtener IP y user agent del contexto
        request = self.context.get('request')
        ip_address = None
        user_agent = None
        
        if request:
            ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')

        # Crear input para el servicio
        resend_input = EmailTwoFactorResendInput(
            challenge_token=validated_data['challenge_token'],
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Ejecutar servicio
        service = EmailTwoFactorResendService()
        return service.execute(resend_input)


class TwoFactorSetMethodSerializer(serializers.Serializer):
    """Serializer para cambiar el método de 2FA."""
    
    method = serializers.ChoiceField(
        choices=['totp', 'email'],
        required=True,
        error_messages={
            'required': 'El método es obligatorio.',
            'invalid_choice': 'Método inválido. Debe ser "totp" o "email".',
        }
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        trim_whitespace=False,
        error_messages={
            'required': 'La contraseña es obligatoria.',
            'blank': 'La contraseña no puede estar vacía.',
        }
    )

    def validate_password(self, value):
        """Validar que la contraseña no esté vacía."""
        if not value:
            raise serializers.ValidationError('La contraseña no puede estar vacía.')
        return value

    def validate(self, attrs):
        """Validar que el usuario tenga 2FA habilitado."""
        from api.models import TwoFactorAuth
        from django.contrib.auth import authenticate
        
        request = self.context.get('request')
        user = request.user
        
        # Verificar contraseña
        authenticated_user = authenticate(
            username=user.username,
            password=attrs['password']
        )
        
        if authenticated_user is None:
            raise serializers.ValidationError('Contraseña incorrecta.')
        
        # Verificar que tenga 2FA habilitado
        try:
            two_factor = TwoFactorAuth.objects.get(user=user, is_enabled=True)
            attrs['two_factor'] = two_factor
        except TwoFactorAuth.DoesNotExist:
            raise serializers.ValidationError('2FA no está habilitado. Habilítalo primero.')
        
        return attrs

    def create(self, validated_data):
        """Cambiar el método de 2FA."""
        two_factor = validated_data['two_factor']
        new_method = validated_data['method']
        
        # Actualizar método
        two_factor.method = new_method
        two_factor.save(update_fields=['method'])
        
        method_name = 'App Autenticadora' if new_method == 'totp' else 'Código por Email'
        
        return {
            'method': new_method,
            'message': f'Método de 2FA cambiado a: {method_name}'
        }



class EmailTwoFactorEnableSerializer(serializers.Serializer):
    """Serializer para habilitar 2FA directamente con email."""
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        trim_whitespace=False,
        error_messages={
            'required': 'La contraseña es obligatoria.',
            'blank': 'La contraseña no puede estar vacía.',
        }
    )

    def validate_password(self, value):
        """Validar que la contraseña no esté vacía."""
        if not value:
            raise serializers.ValidationError('La contraseña no puede estar vacía.')
        return value

    def validate(self, attrs):
        """Validar la contraseña del usuario."""
        from django.contrib.auth import authenticate
        
        request = self.context.get('request')
        user = request.user
        
        # Verificar contraseña
        authenticated_user = authenticate(
            username=user.username,
            password=attrs['password']
        )
        
        if authenticated_user is None:
            raise serializers.ValidationError('Contraseña incorrecta.')
        
        return attrs

    def create(self, validated_data):
        """Habilitar 2FA con método email."""
        from api.models import TwoFactorAuth
        from django.utils import timezone
        
        request = self.context.get('request')
        user = request.user
        
        # Crear o actualizar configuración 2FA
        two_factor, created = TwoFactorAuth.objects.get_or_create(
            user=user,
            defaults={'secret_key': ''}
        )
        
        # Generar secret key (aunque no se use para email)
        if not two_factor.secret_key:
            two_factor.generate_secret()
        
        # Configurar método email y habilitar
        two_factor.method = 'email'
        two_factor.is_enabled = True
        two_factor.enabled_at = timezone.now()
        two_factor.backup_codes = []  # Email no usa backup codes
        two_factor.save()
        
        return {
            'method': 'email',
            'message': 'Autenticación de dos factores habilitada con método email.'
        }
