"""
Tests simples para verificar que el middleware de auditoría funciona.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date, timedelta

from api.audit.models import AuditLog, SecurityEvent
from api.audit.services import AuditService, SecurityEventService

User = get_user_model()


class AuditServiceTestCase(TestCase):
    """
    Tests para verificar que el servicio de auditoría funciona correctamente.
    """
    
    def setUp(self):
        """Configuración inicial."""
        # Limpiar logs anteriores
        AuditLog.objects.all().delete()
        SecurityEvent.objects.all().delete()
        
        # Crear usuario de prueba
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_audit_service_log_action(self):
        """Verifica que AuditService.log_action crea un registro."""
        initial_count = AuditLog.objects.count()
        
        # Registrar una acción
        log = AuditService.log_action(
            action='create',
            resource_type='TestResource',
            resource_id=1,
            description='Test action',
            user=self.user,
            severity='info'
        )
        
        # Verificar que se creó el log
        self.assertIsNotNone(log)
        self.assertEqual(AuditLog.objects.count(), initial_count + 1)
        
        # Verificar el contenido
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action, 'create')
        self.assertEqual(log.resource_type, 'TestResource')
        self.assertEqual(log.resource_id, 1)
        self.assertEqual(log.description, 'Test action')
        self.assertEqual(log.severity, 'info')
        
        print(f"✅ Log creado correctamente: {log}")
    
    def test_audit_service_log_create(self):
        """Verifica que log_create funciona."""
        initial_count = AuditLog.objects.count()
        
        log = AuditService.log_create(
            user=self.user,
            resource_type='User',
            resource_id=self.user.id,
            description=f'Usuario {self.user.email} creado'
        )
        
        self.assertIsNotNone(log)
        self.assertEqual(AuditLog.objects.count(), initial_count + 1)
        self.assertEqual(log.action, 'create')
        
        print(f"✅ Log de creación registrado: {log}")
    
    def test_audit_service_log_update(self):
        """Verifica que log_update funciona."""
        initial_count = AuditLog.objects.count()
        
        log = AuditService.log_update(
            user=self.user,
            resource_type='User',
            resource_id=self.user.id,
            description=f'Usuario {self.user.email} actualizado'
        )
        
        self.assertIsNotNone(log)
        self.assertEqual(AuditLog.objects.count(), initial_count + 1)
        self.assertEqual(log.action, 'update')
        
        print(f"✅ Log de actualización registrado: {log}")
    
    def test_audit_service_log_delete(self):
        """Verifica que log_delete funciona."""
        initial_count = AuditLog.objects.count()
        
        log = AuditService.log_delete(
            user=self.user,
            resource_type='User',
            resource_id=self.user.id,
            description=f'Usuario {self.user.email} eliminado'
        )
        
        self.assertIsNotNone(log)
        self.assertEqual(AuditLog.objects.count(), initial_count + 1)
        self.assertEqual(log.action, 'delete')
        self.assertEqual(log.severity, 'warning')  # Las eliminaciones son warning
        
        print(f"✅ Log de eliminación registrado: {log}")
    
    def test_multiple_logs_created(self):
        """Verifica que se pueden crear múltiples logs."""
        initial_count = AuditLog.objects.count()
        
        # Crear varios logs
        for i in range(5):
            AuditService.log_action(
                action='create',
                resource_type='TestResource',
                resource_id=i,
                description=f'Test action {i}',
                user=self.user
            )
        
        # Verificar que se crearon todos
        final_count = AuditLog.objects.count()
        self.assertEqual(final_count, initial_count + 5)
        
        print(f"✅ Múltiples logs creados: {final_count - initial_count}")
    
    def test_logs_ordered_by_timestamp(self):
        """Verifica que los logs están ordenados por timestamp."""
        # Crear varios logs
        for i in range(3):
            AuditService.log_action(
                action='create',
                resource_type='TestResource',
                resource_id=i,
                description=f'Test action {i}',
                user=self.user
            )
        
        # Obtener logs
        logs = AuditLog.objects.all()
        timestamps = [log.timestamp for log in logs]
        
        # Verificar que están en orden descendente (más reciente primero)
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))
        
        print(f"✅ Logs ordenados correctamente por timestamp")
    
    def test_filter_logs_by_user(self):
        """Verifica que se pueden filtrar logs por usuario."""
        # Crear otro usuario
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        
        # Crear logs para ambos usuarios
        AuditService.log_action(
            action='create',
            resource_type='TestResource',
            resource_id=1,
            description='Action by test user',
            user=self.user
        )
        
        AuditService.log_action(
            action='create',
            resource_type='TestResource',
            resource_id=2,
            description='Action by other user',
            user=other_user
        )
        
        # Filtrar por usuario
        user_logs = AuditLog.objects.filter(user=self.user)
        other_logs = AuditLog.objects.filter(user=other_user)
        
        self.assertGreaterEqual(user_logs.count(), 1)
        self.assertGreaterEqual(other_logs.count(), 1)
        
        print(f"✅ Filtrado por usuario funciona: {user_logs.count()} logs para test user")
    
    def test_filter_logs_by_action(self):
        """Verifica que se pueden filtrar logs por acción."""
        # Crear logs con diferentes acciones
        AuditService.log_create(
            user=self.user,
            resource_type='TestResource',
            resource_id=1,
            description='Create action'
        )
        
        AuditService.log_update(
            user=self.user,
            resource_type='TestResource',
            resource_id=1,
            description='Update action'
        )
        
        AuditService.log_delete(
            user=self.user,
            resource_type='TestResource',
            resource_id=1,
            description='Delete action'
        )
        
        # Filtrar por acción
        create_logs = AuditLog.objects.filter(action='create')
        update_logs = AuditLog.objects.filter(action='update')
        delete_logs = AuditLog.objects.filter(action='delete')
        
        self.assertGreaterEqual(create_logs.count(), 1)
        self.assertGreaterEqual(update_logs.count(), 1)
        self.assertGreaterEqual(delete_logs.count(), 1)
        
        print(f"✅ Filtrado por acción funciona: create={create_logs.count()}, update={update_logs.count()}, delete={delete_logs.count()}")
    
    def test_filter_logs_by_severity(self):
        """Verifica que se pueden filtrar logs por severidad."""
        # Crear logs con diferentes severidades
        AuditService.log_action(
            action='create',
            resource_type='TestResource',
            resource_id=1,
            description='Info action',
            user=self.user,
            severity='info'
        )
        
        AuditService.log_action(
            action='update',
            resource_type='TestResource',
            resource_id=1,
            description='Warning action',
            user=self.user,
            severity='warning'
        )
        
        # Filtrar por severidad
        info_logs = AuditLog.objects.filter(severity='info')
        warning_logs = AuditLog.objects.filter(severity='warning')
        
        self.assertGreaterEqual(info_logs.count(), 1)
        self.assertGreaterEqual(warning_logs.count(), 1)
        
        print(f"✅ Filtrado por severidad funciona: info={info_logs.count()}, warning={warning_logs.count()}")


class SecurityEventServiceTestCase(TestCase):
    """
    Tests para verificar que el servicio de eventos de seguridad funciona.
    """
    
    def setUp(self):
        """Configuración inicial."""
        SecurityEvent.objects.all().delete()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_get_unresolved_events(self):
        """Verifica que se pueden obtener eventos no resueltos."""
        # Crear eventos resueltos y no resueltos
        SecurityEvent.objects.create(
            event_type='failed_login',
            email='test@example.com',
            ip_address='127.0.0.1',
            description='Failed login attempt',
            resolved=False
        )
        
        SecurityEvent.objects.create(
            event_type='failed_login',
            email='test2@example.com',
            ip_address='127.0.0.1',
            description='Failed login attempt',
            resolved=True
        )
        
        # Obtener eventos no resueltos
        unresolved = SecurityEventService.get_unresolved_events()
        
        self.assertGreaterEqual(unresolved.count(), 1)
        for event in unresolved:
            self.assertFalse(event.resolved)
        
        print(f"✅ Eventos no resueltos obtenidos: {unresolved.count()}")
    
    def test_resolve_event(self):
        """Verifica que se puede resolver un evento."""
        # Crear evento no resuelto
        event = SecurityEvent.objects.create(
            event_type='failed_login',
            email='test@example.com',
            ip_address='127.0.0.1',
            description='Failed login attempt',
            resolved=False
        )
        
        self.assertFalse(event.resolved)
        
        # Resolver el evento
        resolved_event = SecurityEventService.resolve_event(
            event_id=event.id,
            resolved_by=self.user
        )
        
        self.assertTrue(resolved_event.resolved)
        self.assertEqual(resolved_event.resolved_by, self.user)
        self.assertIsNotNone(resolved_event.resolved_at)
        
        print(f"✅ Evento resuelto correctamente: {resolved_event}")


class AuditLogModelTestCase(TestCase):
    """
    Tests para verificar el modelo AuditLog.
    """
    
    def setUp(self):
        """Configuración inicial."""
        AuditLog.objects.all().delete()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_audit_log_str(self):
        """Verifica el método __str__ del modelo."""
        log = AuditLog.objects.create(
            user=self.user,
            action='create',
            resource_type='TestResource',
            resource_id=1,
            description='Test action'
        )
        
        str_repr = str(log)
        self.assertIn(self.user.email, str_repr)
        self.assertIn('create', str_repr)
        self.assertIn('TestResource', str_repr)
        
        print(f"✅ Representación string del log: {str_repr}")
    
    def test_audit_log_metadata(self):
        """Verifica que se puede guardar metadata."""
        metadata = {
            'method': 'POST',
            'path': '/api/test/',
            'status_code': 201,
            'duration_ms': 150
        }
        
        log = AuditLog.objects.create(
            user=self.user,
            action='create',
            resource_type='TestResource',
            resource_id=1,
            description='Test action',
            metadata=metadata
        )
        
        self.assertEqual(log.metadata, metadata)
        self.assertEqual(log.metadata['method'], 'POST')
        self.assertEqual(log.metadata['status_code'], 201)
        
        print(f"✅ Metadata guardada correctamente: {log.metadata}")
    
    def test_audit_log_without_user(self):
        """Verifica que se puede crear un log sin usuario (sistema)."""
        log = AuditLog.objects.create(
            user=None,
            action='create',
            resource_type='TestResource',
            resource_id=1,
            description='System action'
        )
        
        self.assertIsNone(log.user)
        self.assertEqual(log.description, 'System action')
        
        print(f"✅ Log del sistema creado sin usuario: {log}")


class SecurityEventModelTestCase(TestCase):
    """
    Tests para verificar el modelo SecurityEvent.
    """
    
    def setUp(self):
        """Configuración inicial."""
        SecurityEvent.objects.all().delete()
    
    def test_security_event_str(self):
        """Verifica el método __str__ del modelo."""
        event = SecurityEvent.objects.create(
            event_type='failed_login',
            email='test@example.com',
            ip_address='127.0.0.1',
            description='Failed login attempt'
        )
        
        str_repr = str(event)
        self.assertIn('failed_login', str_repr)
        self.assertIn('127.0.0.1', str_repr)
        
        print(f"✅ Representación string del evento: {str_repr}")
    
    def test_security_event_metadata(self):
        """Verifica que se puede guardar metadata."""
        metadata = {
            'reason': 'Invalid password',
            'attempts': 3
        }
        
        event = SecurityEvent.objects.create(
            event_type='failed_login',
            email='test@example.com',
            ip_address='127.0.0.1',
            description='Failed login attempt',
            metadata=metadata
        )
        
        self.assertEqual(event.metadata, metadata)
        self.assertEqual(event.metadata['reason'], 'Invalid password')
        
        print(f"✅ Metadata del evento guardada: {event.metadata}")
