from django.core import mail
from django.test import TestCase, override_settings

from api.services.email_service import EmailInput, EmailService


class EmailServiceTestCase(TestCase):
    """Tests para EmailService."""

    def setUp(self):
        self.email_service = EmailService()

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_email_success(self):
        """Test envío exitoso de email."""
        # Arrange
        email_input = EmailInput(
            to_email='test@ejemplo.com',
            subject='Test Email',
            template_name='emails/test_email.html',
            context={'name': ' Usuario Test'},
        )

        # Act
        result = self.email_service.execute(email_input)

        # Assert
        self.assertTrue(result.success)
        self.assertEqual(result.email_sent_to, 'test@ejemplo.com')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Test Email')
        self.assertEqual(mail.outbox[0].to, ['test@ejemplo.com'])

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_email_with_custom_from(self):
        """Test envío de email con remitente personalizado."""
        # Arrange
        email_input = EmailInput(
            to_email='test@ejemplo.com',
            subject='Test Email',
            template_name='emails/test_email.html',
            context={'name': ' Usuario Test'},
            from_email='custom@ejemplo.com',
            from_name='Custom Sender',
        )

        # Act
        result = self.email_service.execute(email_input)

        # Assert
        self.assertTrue(result.success)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Custom Sender', mail.outbox[0].from_email)

    def test_send_email_with_invalid_template(self):
        """Test envío de email con template inválido."""
        # Arrange
        email_input = EmailInput(
            to_email='test@ejemplo.com',
            subject='Test Email',
            template_name='emails/nonexistent.html',
            context={},
        )

        # Act
        result = self.email_service.execute(email_input)

        # Assert
        self.assertFalse(result.success)
        self.assertIn('Error al enviar email', result.message)
