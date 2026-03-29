from django.core.management.base import BaseCommand

from api.services.email_service import EmailInput, EmailService


class Command(BaseCommand):
    help = 'Envía un email de prueba usando Brevo SMTP'

    def add_arguments(self, parser):
        parser.add_argument(
            'email',
            type=str,
            help='Email de destino para la prueba',
        )
        parser.add_argument(
            '--name',
            type=str,
            default='',
            help='Nombre del destinatario (opcional)',
        )

    def handle(self, *args, **options):
        email_to = options['email']
        name = options.get('name', '')

        self.stdout.write(self.style.WARNING(f'Enviando email de prueba a: {email_to}'))

        # Crear input para el servicio
        email_input = EmailInput(
            to_email=email_to,
            subject='Prueba de Email - Sistema Bancario',
            template_name='emails/test_email.html',
            context={'name': f' {name}' if name else ''},
        )

        # Ejecutar servicio
        email_service = EmailService()
        result = email_service.execute(email_input)

        if result.success:
            self.stdout.write(
                self.style.SUCCESS(f'✅ {result.message}')
            )
            self.stdout.write(
                self.style.SUCCESS(f'Email enviado a: {result.email_sent_to}')
            )
        else:
            self.stdout.write(
                self.style.ERROR(f'❌ {result.message}')
            )
