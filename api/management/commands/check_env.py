from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Verifica la configuración de email desde .env'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Verificando configuración de email...'))
        self.stdout.write(f'EMAIL_HOST: {settings.EMAIL_HOST}')
        self.stdout.write(f'EMAIL_PORT: {settings.EMAIL_PORT}')
        self.stdout.write(f'EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}')
        self.stdout.write(f'EMAIL_HOST_PASSWORD: {"*" * 10 if settings.EMAIL_HOST_PASSWORD else "NO CONFIGURADO"}')
        self.stdout.write(f'DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}')
        self.stdout.write(f'DEFAULT_FROM_NAME: {settings.DEFAULT_FROM_NAME}')
        self.stdout.write(f'FRONTEND_URL: {settings.FRONTEND_URL}')

        if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            self.stdout.write(
                self.style.ERROR(
                    'ERROR: Faltan credenciales SMTP (BREVO_SMTP_USER/BREVO_SMTP_KEY o EMAIL_HOST_USER/EMAIL_HOST_PASSWORD).'
                )
            )

        if settings.DEFAULT_FROM_EMAIL == 'noreply@ejemplo.com':
            self.stdout.write(
                self.style.ERROR(
                    'ERROR: DEFAULT_FROM_EMAIL sigue con valor de ejemplo. Configura un remitente válido y verificado.'
                )
            )
