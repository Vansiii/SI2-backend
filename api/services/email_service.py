import logging
from dataclasses import dataclass
from typing import Optional

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailInput:
    """Input para envío de email."""
    to_email: str
    subject: str
    template_name: str
    context: dict
    from_email: Optional[str] = None
    from_name: Optional[str] = None


@dataclass(frozen=True)
class EmailResult:
    """Resultado del envío de email."""
    success: bool
    message: str
    email_sent_to: str


class EmailService:
    """Servicio para envío de emails usando Brevo SMTP."""

    def execute(self, payload: EmailInput) -> EmailResult:
        """
        Envía un email usando una plantilla HTML.

        Args:
            payload: EmailInput con los datos del email

        Returns:
            EmailResult con el resultado del envío
        """
        try:
            if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
                logger.warning(
                    'Email no enviado: faltan credenciales SMTP',
                    extra={'to_email': payload.to_email},
                )
                return EmailResult(
                    success=False,
                    message='Configuración SMTP incompleta: faltan credenciales de email.',
                    email_sent_to=payload.to_email,
                )

            # Determinar remitente
            from_email = payload.from_email or settings.DEFAULT_FROM_EMAIL
            from_name = payload.from_name or settings.DEFAULT_FROM_NAME

            if from_email == 'noreply@ejemplo.com':
                logger.warning(
                    'Email no enviado: DEFAULT_FROM_EMAIL mantiene valor de ejemplo',
                    extra={'to_email': payload.to_email},
                )
                return EmailResult(
                    success=False,
                    message='DEFAULT_FROM_EMAIL no está configurado para producción.',
                    email_sent_to=payload.to_email,
                )

            from_address = f'{from_name} <{from_email}>'

            # Renderizar template HTML
            template_context = {'frontend_url': settings.FRONTEND_URL}
            template_context.update(payload.context or {})
            html_content = render_to_string(payload.template_name, template_context)

            # Crear email
            email = EmailMultiAlternatives(
                subject=payload.subject,
                body='',  # Texto plano vacío, usaremos HTML
                from_email=from_address,
                to=[payload.to_email],
            )

            # Adjuntar contenido HTML
            email.attach_alternative(html_content, 'text/html')

            # Enviar
            email.send(fail_silently=False)

            return EmailResult(
                success=True,
                message='Email enviado exitosamente.',
                email_sent_to=payload.to_email,
            )

        except Exception as e:
            logger.exception(
                'Error al enviar email',
                extra={
                    'to_email': payload.to_email,
                    'template_name': payload.template_name,
                },
            )
            return EmailResult(
                success=False,
                message=f'Error al enviar email: {str(e)}',
                email_sent_to=payload.to_email,
            )
