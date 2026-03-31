from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import LoginSerializer


@method_decorator(ratelimit(key='ip', rate='10/15m', method='POST'), name='dispatch')
class LoginAPIView(APIView):
    """Vista para login de usuario."""
    
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Autentica un usuario y retorna tokens JWT.

        Request body:
            {
                "email": "usuario@ejemplo.com",
                "password": "contraseña"
            }

        Response (200 OK):
            {
                "access": "token...",
                "refresh": "token...",
                "user": {
                    "id": 1,
                    "email": "usuario@ejemplo.com",
                    "first_name": "Juan",
                    "last_name": "Pérez"
                },
                "institution": {
                    "id": 1,
                    "name": "Banco Ejemplo",
                    "slug": "banco-ejemplo",
                    "institution_type": "banking"
                },
                "role": "admin",
                "requires_2fa": false
            }

        Response (400 Bad Request):
            {
                "email": ["mensaje de error"],
                "password": ["mensaje de error"]
            }

        Response (401 Unauthorized):
            {
                "detail": "Credenciales inválidas."
            }
        """
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        # Si requiere 2FA, retornar respuesta especial
        if result.requires_2fa:
            return Response({
                'requires_2fa': True,
                'challenge_token': result.challenge_token,
                'expires_in': result.expires_in,
                'method': result.method,  # Incluir método de 2FA
                'message': 'Se requiere código de autenticación de dos factores.',
                'user': {
                    'id': result.user.id,
                    'email': result.user.email,
                },
            }, status=status.HTTP_200_OK)

        # Login normal sin 2FA
        response_payload = {
            'access': result.access_token,
            'refresh': result.refresh_token,
            'user': {
                'id': result.user.id,
                'email': result.user.email,
                'first_name': result.user.first_name,
                'last_name': result.user.last_name,
            },
            'institution': {
                'id': result.institution.id,
                'name': result.institution.name,
                'slug': result.institution.slug,
                'institution_type': result.institution.institution_type,
            },
            'role': result.role,
            'user_type': result.user_type,
            'roles': result.roles,
            'permissions': result.permissions,
            'requires_2fa': result.requires_2fa,
        }

        return Response(response_payload, status=status.HTTP_200_OK)



# ============================================================
# LOGOUT
# ============================================================

class LogoutAPIView(APIView):
    """Vista para logout de usuario."""
    
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Cierra la sesión del usuario agregando el refresh token a la blacklist.

        Request body:
            {
                "refresh": "token..."
            }

        Response (200 OK):
            {
                "message": "Sesión cerrada exitosamente."
            }

        Response (400 Bad Request):
            {
                "detail": "Token inválido o ya ha sido revocado."
            }
        """
        from .serializers import LogoutSerializer
        
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        return Response(result, status=status.HTTP_200_OK)



# ============================================================
# PASSWORD RESET
# ============================================================

@method_decorator(ratelimit(key='ip', rate='5/1h', method='POST'), name='dispatch')
class PasswordResetRequestAPIView(APIView):
    """Vista para solicitar recuperación de contraseña."""
    
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Solicita recuperación de contraseña.

        Request body:
            {
                "email": "usuario@ejemplo.com"
            }

        Response (200 OK):
            {
                "message": "Si el correo existe, recibirás instrucciones para recuperar tu contraseña."
            }
        """
        from .serializers import PasswordResetRequestSerializer
        
        serializer = PasswordResetRequestSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        return Response({'message': result.message}, status=status.HTTP_200_OK)


class PasswordResetValidateAPIView(APIView):
    """Vista para validar token de recuperación."""
    
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Valida un token de recuperación.

        Request body:
            {
                "token": "token..."
            }

        Response (200 OK):
            {
                "valid": true,
                "message": "Token válido."
            }
        """
        from .serializers import PasswordResetValidateSerializer
        
        serializer = PasswordResetValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response({
            'valid': serializer.validated_data['valid'],
            'message': serializer.validated_data['message']
        }, status=status.HTTP_200_OK)


class PasswordResetConfirmAPIView(APIView):
    """Vista para confirmar nueva contraseña."""
    
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Confirma el cambio de contraseña.

        Request body:
            {
                "token": "token...",
                "new_password": "NuevaPassword123!",
                "confirm_password": "NuevaPassword123!"
            }

        Response (200 OK):
            {
                "message": "Contraseña actualizada exitosamente."
            }
        """
        from .serializers import PasswordResetConfirmSerializer
        
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            'message': 'Contraseña actualizada exitosamente.'
        }, status=status.HTTP_200_OK)



# ============================================================
# TWO-FACTOR AUTHENTICATION (2FA)
# ============================================================

from rest_framework.permissions import IsAuthenticated


class TwoFactorEnableAPIView(APIView):
    """Vista para iniciar habilitación de 2FA."""
    
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Inicia el proceso de habilitación de 2FA.

        Response (200 OK):
            {
                "secret": "JBSWY3DPEHPK3PXP",
                "qr_code": "data:image/png;base64,iVBORw0KGgo...",
                "backup_codes": ["ABCD-1234", "EFGH-5678", ...]
            }
        """
        from .serializers import TwoFactorEnableSerializer
        
        serializer = TwoFactorEnableSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        return Response({
            'secret': result.secret,
            'qr_code': f'data:image/png;base64,{result.qr_code_base64}',
            'backup_codes': result.backup_codes,
        }, status=status.HTTP_200_OK)


@method_decorator(ratelimit(key='user', rate='5/5m', method='POST'), name='dispatch')
class TwoFactorVerifyAPIView(APIView):
    """Vista para verificar y activar 2FA."""
    
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Verifica el código TOTP y activa 2FA.

        Request body:
            {
                "token": "123456"
            }

        Response (200 OK):
            {
                "message": "Autenticación de dos factores activada exitosamente."
            }
        """
        from .serializers import TwoFactorVerifySerializer
        
        serializer = TwoFactorVerifySerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        return Response({
            'message': result.message
        }, status=status.HTTP_200_OK)


class TwoFactorDisableAPIView(APIView):
    """Vista para deshabilitar 2FA."""
    
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Deshabilita 2FA después de verificar la contraseña.

        Request body:
            {
                "password": "contraseña"
            }

        Response (200 OK):
            {
                "message": "Autenticación de dos factores deshabilitada exitosamente."
            }
        """
        from .serializers import TwoFactorDisableSerializer
        
        serializer = TwoFactorDisableSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        return Response({
            'message': result.message
        }, status=status.HTTP_200_OK)


class TwoFactorStatusAPIView(APIView):
    """Vista para obtener el estado de 2FA del usuario."""
    
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Obtiene el estado de 2FA del usuario.

        Response (200 OK):
            {
                "is_enabled": true,
                "enabled_at": "2026-03-28T10:30:00Z",
                "backup_codes_remaining": 8,
                "method": "totp" | "email"
            }
        """
        from api.models import TwoFactorAuth
        
        try:
            two_factor = TwoFactorAuth.objects.get(user=request.user)
            return Response({
                'is_enabled': two_factor.is_enabled,
                'enabled_at': two_factor.enabled_at,
                'backup_codes_remaining': len(two_factor.backup_codes) if two_factor.is_enabled else 0,
                'method': two_factor.method,
            }, status=status.HTTP_200_OK)
        except TwoFactorAuth.DoesNotExist:
            return Response({
                'is_enabled': False,
                'enabled_at': None,
                'backup_codes_remaining': 0,
                'method': 'totp',
            }, status=status.HTTP_200_OK)



@method_decorator(ratelimit(key='ip', rate='5/5m', method='POST'), name='dispatch')
class TwoFactorLoginVerifyAPIView(APIView):
    """Vista para verificar código 2FA durante login."""
    
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Verifica el código 2FA y completa el login.

        Request body:
            {
                "challenge_token": "token...",
                "totp_code": "123456",
                "is_backup_code": false
            }

        Response (200 OK):
            {
                "access": "token...",
                "refresh": "token...",
                "user": {...},
                "institution": {...},
                "role": "admin"
            }
        """
        from .serializers import TwoFactorLoginVerifySerializer
        
        serializer = TwoFactorLoginVerifySerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        response_payload = {
            'access': result.access_token,
            'refresh': result.refresh_token,
            'user': {
                'id': result.user.id,
                'email': result.user.email,
                'first_name': result.user.first_name,
                'last_name': result.user.last_name,
            },
            'institution': {
                'id': result.institution.id,
                'name': result.institution.name,
                'slug': result.institution.slug,
                'institution_type': result.institution.institution_type,
            },
            'role': result.role,
            'user_type': result.user_type,
            'roles': result.roles,
            'permissions': result.permissions,
        }

        return Response(response_payload, status=status.HTTP_200_OK)



class TwoFactorRegenerateBackupCodesAPIView(APIView):
    """Vista para regenerar códigos de respaldo."""
    
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Regenera los códigos de respaldo después de verificar la contraseña.

        Request body:
            {
                "password": "contraseña"
            }

        Response (200 OK):
            {
                "backup_codes": ["ABCD-1234", "EFGH-5678", ...],
                "message": "Códigos de respaldo regenerados exitosamente."
            }
        """
        from .serializers import TwoFactorRegenerateBackupCodesSerializer
        
        serializer = TwoFactorRegenerateBackupCodesSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        return Response({
            'backup_codes': result.backup_codes,
            'message': result.message
        }, status=status.HTTP_200_OK)


# ============================================================
# EMAIL TWO-FACTOR AUTHENTICATION
# ============================================================

@method_decorator(ratelimit(key='user_or_ip', rate='3/5m', method='POST'), name='dispatch')
class EmailTwoFactorResendAPIView(APIView):
    """Vista para reenviar código 2FA por email."""
    
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Reenvía código de verificación por email.
        
        Request body:
            {
                "challenge_token": "token..."
            }
        
        Response (200 OK):
            {
                "challenge_token": "new_token...",
                "message": "Código reenviado exitosamente.",
                "expires_in": 5
            }
        """
        from .serializers import EmailTwoFactorResendSerializer
        
        serializer = EmailTwoFactorResendSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        
        return Response({
            'challenge_token': result.challenge_token,
            'message': result.message,
            'expires_in': result.expires_in_minutes
        }, status=status.HTTP_200_OK)


class TwoFactorSetMethodAPIView(APIView):
    """Vista para cambiar el método de 2FA."""
    
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Cambia el método de 2FA entre TOTP y Email.
        
        Request body:
            {
                "method": "totp" | "email",
                "password": "contraseña"
            }
        
        Response (200 OK):
            {
                "method": "email",
                "message": "Método de 2FA cambiado a: Código por Email"
            }
        """
        from .serializers import TwoFactorSetMethodSerializer
        
        serializer = TwoFactorSetMethodSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        
        return Response({
            'method': result['method'],
            'message': result['message']
        }, status=status.HTTP_200_OK)


class TwoFactorGetMethodAPIView(APIView):
    """Vista para obtener el método de 2FA actual."""
    
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Obtiene el método de 2FA actual del usuario.
        
        Response (200 OK):
            {
                "method": "totp" | "email",
                "is_enabled": true
            }
        """
        from api.models import TwoFactorAuth
        
        try:
            two_factor = TwoFactorAuth.objects.get(user=request.user)
            return Response({
                'method': two_factor.method,
                'is_enabled': two_factor.is_enabled,
            }, status=status.HTTP_200_OK)
        except TwoFactorAuth.DoesNotExist:
            return Response({
                'method': 'totp',
                'is_enabled': False,
            }, status=status.HTTP_200_OK)



class EmailTwoFactorEnableAPIView(APIView):
    """Vista para habilitar 2FA directamente con email."""
    
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Habilita 2FA con método email directamente.
        
        Request body:
            {
                "password": "contraseña"
            }
        
        Response (200 OK):
            {
                "method": "email",
                "message": "Autenticación de dos factores habilitada con método email."
            }
        """
        from .serializers import EmailTwoFactorEnableSerializer
        
        serializer = EmailTwoFactorEnableSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        
        return Response(result, status=status.HTTP_200_OK)
