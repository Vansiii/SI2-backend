"""
Tests para verificar que el middleware de auditoría registra automáticamente las acciones.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import date, timedelta

from api.audit.models import AuditLog, SecurityEvent
from api.tenants.models import FinancialInstitution, FinancialInstitutionMembership
from api.users.models import UserProfile
from api.roles.models import Role, Permission, UserRole
from api.saas.models import SubscriptionPlan, Subscription

User = get_user_model()


class AuditMiddlewareTestCase(TestCase):
    """
    Tests para verificar que el middleware registra automáticamente las acciones.
    """
    
    def setUp(self):
        """Configuración inicial para los tests."""
        # Limpiar logs anteriores
        AuditLog.objects.all().delete()
        SecurityEvent.objects.all().delete()
        
        # Crear institución financiera
        self.institution = FinancialInstitution.objects.create(
            name='Banco Test',
            slug='banco-test',
            institution_type='bank',
            is_active=True
        )
        
        # Crear plan de suscripción
        self.plan = SubscriptionPlan.objects.create(
            name='Plan Test',
            slug='plan-test',
            price=100.00,
            max_users=10,
            max_products=5,
            max_loans_per_month=50
        )
        
        # Crear suscripción
        self.subscription, _ = Subscription.objects.get_or_create(
            institution=self.institution,
            defaults={
                'plan': self.plan,
                'status': 'ACTIVE',
                'start_date': date.today(),
                'trial_end_date': date.today() + timedelta(days=30),
                'next_billing_date': date.today() + timedelta(days=30)
            }
        )
        
        # Crear usuario administrador
        self.admin_user = User.objects.create_user(
            username='admin@test.com',
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='Test'
        )
        
        # Crear perfil de usuario
        self.admin_profile = UserProfile.objects.create(
            user=self.admin_user,
            type='tenant_user'
        )
        
        # Crear membresía
        self.membership = FinancialInstitutionMembership.objects.create(
            user=self.admin_user,
            institution=self.institution,
            is_active=True
        )
        
        # Crear permisos
        self.permission_users_view = Permission.objects.create(
            code='users.view',
            name='Ver Usuarios',
            description='Permite ver usuarios'
        )
        
        self.permission_users_create = Permission.objects.create(
            code='users.create',
            name='Crear Usuarios',
            description='Permite crear usuarios'
        )
        
        self.permission_users_update = Permission.objects.create(
            code='users.update',
            name='Actualizar Usuarios',
            description='Permite actualizar usuarios'
        )
        
        self.permission_users_delete = Permission.objects.create(
            code='users.delete',
            name='Eliminar Usuarios',
            description='Permite eliminar usuarios'
        )
        
        self.permission_roles_view = Permission.objects.create(
            code='roles.view',
            name='Ver Roles',
            description='Permite ver roles'
        )
        
        self.permission_roles_create = Permission.objects.create(
            code='roles.create',
            name='Crear Roles',
            description='Permite crear roles'
        )
        
        # Crear rol de administrador
        self.admin_role = Role.objects.create(
            institution=self.institution,
            name='Administrador',
            description='Rol de administrador con todos los permisos'
        )
        
        # Asignar permisos al rol
        self.admin_role.permissions.add(
            self.permission_users_view,
            self.permission_users_create,
            self.permission_users_update,
            self.permission_users_delete,
            self.permission_roles_view,
            self.permission_roles_create
        )
        
        # Asignar rol al usuario
        UserRole.objects.create(
            user=self.admin_user,
            role=self.admin_role,
            institution=self.institution,
            is_active=True
        )
        
        # Crear cliente HTTP
        self.client = Client()
        
        # Obtener token JWT
        refresh = RefreshToken.for_user(self.admin_user)
        self.access_token = str(refresh.access_token)
        
        # Headers con autenticación
        self.auth_headers = {
            'HTTP_AUTHORIZATION': f'Bearer {self.access_token}',
            'HTTP_X_INSTITUTION_SLUG': 'banco-test'
        }
    
    def test_login_creates_audit_log(self):
        """Verifica que el login crea un log de auditoría."""
        initial_count = AuditLog.objects.count()
        
        # Realizar login
        response = self.client.post(
            '/api/auth/login/',
            {
                'email': 'admin@test.com',
                'password': 'testpass123',
                'institution_slug': 'banco-test'
            },
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verificar que se creó un log
        final_count = AuditLog.objects.count()
        self.assertGreater(final_count, initial_count)
        
        # Verificar el contenido del log
        log = AuditLog.objects.latest('timestamp')
        self.assertEqual(log.user, self.admin_user)
        self.assertEqual(log.action, 'login')
        self.assertEqual(log.resource_type, 'User')
        self.assertIsNotNone(log.ip_address)
        
        print(f"✅ Login registrado: {log}")
    
    def test_create_user_creates_audit_log(self):
        """Verifica que crear un usuario crea un log de auditoría."""
        initial_count = AuditLog.objects.count()
        
        # Crear usuario
        response = self.client.post(
            '/api/users/',
            {
                'email': 'newuser@test.com',
                'password': 'testpass123',
                'first_name': 'New',
                'last_name': 'User',
                'position': 'Empleado'
            },
            content_type='application/json',
            **self.auth_headers
        )
        
        self.assertEqual(response.status_code, 201)
        
        # Verificar que se creó un log
        final_count = AuditLog.objects.count()
        self.assertGreater(final_count, initial_count)
        
        # Verificar el contenido del log
        log = AuditLog.objects.latest('timestamp')
        self.assertEqual(log.user, self.admin_user)
        self.assertEqual(log.action, 'create')
        self.assertEqual(log.resource_type, 'User')
        self.assertEqual(log.institution, self.institution)
        
        print(f"✅ Creación de usuario registrada: {log}")
    
    def test_update_user_creates_audit_log(self):
        """Verifica que actualizar un usuario crea un log de auditoría."""
        # Crear usuario para actualizar
        user = User.objects.create_user(
            username='updateuser@test.com',
            email='updateuser@test.com',
            password='testpass123',
            first_name='Update',
            last_name='User'
        )
        
        UserProfile.objects.create(
            user=user,
            type='tenant_user'
        )
        
        FinancialInstitutionMembership.objects.create(
            user=user,
            institution=self.institution,
            is_active=True
        )
        
        initial_count = AuditLog.objects.count()
        
        # Actualizar usuario
        response = self.client.patch(
            f'/api/users/{user.id}/',
            {
                'first_name': 'Updated'
            },
            content_type='application/json',
            **self.auth_headers
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verificar que se creó un log
        final_count = AuditLog.objects.count()
        self.assertGreater(final_count, initial_count)
        
        # Verificar el contenido del log
        log = AuditLog.objects.latest('timestamp')
        self.assertEqual(log.user, self.admin_user)
        self.assertEqual(log.action, 'update')
        self.assertEqual(log.resource_type, 'User')
        
        print(f"✅ Actualización de usuario registrada: {log}")
    
    def test_delete_user_creates_audit_log(self):
        """Verifica que eliminar un usuario crea un log de auditoría."""
        # Crear usuario para eliminar
        user = User.objects.create_user(
            username='deleteuser@test.com',
            email='deleteuser@test.com',
            password='testpass123',
            first_name='Delete',
            last_name='User'
        )
        
        UserProfile.objects.create(
            user=user,
            type='tenant_user'
        )
        
        FinancialInstitutionMembership.objects.create(
            user=user,
            institution=self.institution,
            is_active=True
        )
        
        initial_count = AuditLog.objects.count()
        
        # Eliminar usuario
        response = self.client.delete(
            f'/api/users/{user.id}/',
            **self.auth_headers
        )
        
        self.assertEqual(response.status_code, 204)
        
        # Verificar que se creó un log
        final_count = AuditLog.objects.count()
        self.assertGreater(final_count, initial_count)
        
        # Verificar el contenido del log
        log = AuditLog.objects.latest('timestamp')
        self.assertEqual(log.user, self.admin_user)
        self.assertEqual(log.action, 'delete')
        self.assertEqual(log.resource_type, 'User')
        self.assertEqual(log.severity, 'warning')
        
        print(f"✅ Eliminación de usuario registrada: {log}")
    
    def test_create_role_creates_audit_log(self):
        """Verifica que crear un rol crea un log de auditoría."""
        initial_count = AuditLog.objects.count()
        
        # Crear rol
        response = self.client.post(
            '/api/roles/',
            {
                'name': 'Nuevo Rol',
                'description': 'Descripción del nuevo rol'
            },
            content_type='application/json',
            **self.auth_headers
        )
        
        self.assertEqual(response.status_code, 201)
        
        # Verificar que se creó un log
        final_count = AuditLog.objects.count()
        self.assertGreater(final_count, initial_count)
        
        # Verificar el contenido del log
        log = AuditLog.objects.latest('timestamp')
        self.assertEqual(log.user, self.admin_user)
        self.assertEqual(log.action, 'create')
        self.assertEqual(log.resource_type, 'Role')
        
        print(f"✅ Creación de rol registrada: {log}")
    
    def test_failed_login_creates_security_event(self):
        """Verifica que un login fallido crea un evento de seguridad."""
        initial_count = SecurityEvent.objects.count()
        
        # Intentar login con credenciales incorrectas
        response = self.client.post(
            '/api/auth/login/',
            {
                'email': 'admin@test.com',
                'password': 'wrongpassword',
                'institution_slug': 'banco-test'
            },
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
        
        # Verificar que se creó un evento de seguridad
        final_count = SecurityEvent.objects.count()
        self.assertGreater(final_count, initial_count)
        
        # Verificar el contenido del evento
        event = SecurityEvent.objects.latest('timestamp')
        self.assertEqual(event.event_type, 'failed_login')
        self.assertEqual(event.email, 'admin@test.com')
        self.assertIsNotNone(event.ip_address)
        self.assertFalse(event.resolved)
        
        print(f"✅ Login fallido registrado: {event}")
    
    def test_unauthorized_access_creates_security_event(self):
        """Verifica que un acceso no autorizado crea un evento de seguridad."""
        # Crear usuario sin permisos
        user_no_perms = User.objects.create_user(
            username='noperms@test.com',
            email='noperms@test.com',
            password='testpass123',
            first_name='No',
            last_name='Perms'
        )
        
        UserProfile.objects.create(
            user=user_no_perms,
            type='tenant_user'
        )
        
        FinancialInstitutionMembership.objects.create(
            user=user_no_perms,
            institution=self.institution,
            is_active=True
        )
        
        # Obtener token para usuario sin permisos
        refresh = RefreshToken.for_user(user_no_perms)
        access_token = str(refresh.access_token)
        
        initial_count = SecurityEvent.objects.count()
        
        # Intentar crear usuario sin permisos
        response = self.client.post(
            '/api/users/',
            {
                'email': 'test@test.com',
                'password': 'testpass123',
                'first_name': 'Test',
                'last_name': 'User',
                'position': 'Empleado'
            },
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {access_token}',
            HTTP_X_INSTITUTION_SLUG='banco-test'
        )
        
        self.assertEqual(response.status_code, 403)
        
        # Verificar que se creó un evento de seguridad
        final_count = SecurityEvent.objects.count()
        self.assertGreater(final_count, initial_count)
        
        # Verificar el contenido del evento
        event = SecurityEvent.objects.latest('timestamp')
        self.assertEqual(event.event_type, 'unauthorized_access')
        self.assertEqual(event.user, user_no_perms)
        
        print(f"✅ Acceso no autorizado registrado: {event}")
    
    def test_multiple_actions_create_multiple_logs(self):
        """Verifica que múltiples acciones crean múltiples logs."""
        initial_count = AuditLog.objects.count()
        
        # Realizar múltiples acciones
        actions = [
            ('POST', '/api/roles/', {'name': 'Rol 1', 'description': 'Desc 1'}),
            ('POST', '/api/roles/', {'name': 'Rol 2', 'description': 'Desc 2'}),
            ('POST', '/api/roles/', {'name': 'Rol 3', 'description': 'Desc 3'}),
        ]
        
        for method, url, data in actions:
            response = self.client.post(
                url,
                data,
                content_type='application/json',
                **self.auth_headers
            )
            self.assertEqual(response.status_code, 201)
        
        # Verificar que se crearon múltiples logs
        final_count = AuditLog.objects.count()
        self.assertEqual(final_count, initial_count + 3)
        
        print(f"✅ Múltiples acciones registradas: {final_count - initial_count} logs")
    
    def test_audit_log_contains_metadata(self):
        """Verifica que los logs contienen metadata útil."""
        # Crear usuario
        response = self.client.post(
            '/api/users/',
            {
                'email': 'metadata@test.com',
                'password': 'testpass123',
                'first_name': 'Meta',
                'last_name': 'Data',
                'position': 'Empleado'
            },
            content_type='application/json',
            **self.auth_headers
        )
        
        self.assertEqual(response.status_code, 201)
        
        # Verificar metadata del log
        log = AuditLog.objects.latest('timestamp')
        self.assertIsNotNone(log.metadata)
        self.assertIn('method', log.metadata)
        self.assertIn('path', log.metadata)
        self.assertIn('status_code', log.metadata)
        self.assertIn('duration_ms', log.metadata)
        
        print(f"✅ Metadata registrada: {log.metadata}")
    
    def test_audit_log_captures_ip_and_user_agent(self):
        """Verifica que los logs capturan IP y user agent."""
        # Crear usuario con headers personalizados
        response = self.client.post(
            '/api/users/',
            {
                'email': 'iptest@test.com',
                'password': 'testpass123',
                'first_name': 'IP',
                'last_name': 'Test',
                'position': 'Empleado'
            },
            content_type='application/json',
            HTTP_USER_AGENT='Mozilla/5.0 Test Browser',
            HTTP_X_FORWARDED_FOR='192.168.1.100',
            **self.auth_headers
        )
        
        self.assertEqual(response.status_code, 201)
        
        # Verificar IP y user agent
        log = AuditLog.objects.latest('timestamp')
        self.assertIsNotNone(log.ip_address)
        self.assertIsNotNone(log.user_agent)
        self.assertIn('Mozilla', log.user_agent)
        
        print(f"✅ IP y User Agent capturados: IP={log.ip_address}, UA={log.user_agent[:50]}...")


class AuditLogQueryTestCase(TestCase):
    """
    Tests para verificar las consultas de logs de auditoría.
    """
    
    def setUp(self):
        """Configuración inicial."""
        # Crear institución
        self.institution = FinancialInstitution.objects.create(
            name='Banco Query Test',
            slug='banco-query-test',
            institution_type='bank',
            is_active=True
        )
        
        # Crear usuario
        self.user = User.objects.create_user(
            username='query@test.com',
            email='query@test.com',
            password='testpass123',
            first_name='Query',
            last_name='Test'
        )
        
        # Crear logs de prueba
        for i in range(10):
            AuditLog.objects.create(
                user=self.user,
                action='create',
                resource_type='User',
                resource_id=i,
                description=f'Test log {i}',
                ip_address='127.0.0.1',
                institution=self.institution,
                severity='info' if i % 2 == 0 else 'warning'
            )
    
    def test_filter_logs_by_user(self):
        """Verifica que se pueden filtrar logs por usuario."""
        logs = AuditLog.objects.filter(user=self.user)
        self.assertEqual(logs.count(), 10)
        
        print(f"✅ Filtrado por usuario: {logs.count()} logs")
    
    def test_filter_logs_by_institution(self):
        """Verifica que se pueden filtrar logs por institución."""
        logs = AuditLog.objects.filter(institution=self.institution)
        self.assertEqual(logs.count(), 10)
        
        print(f"✅ Filtrado por institución: {logs.count()} logs")
    
    def test_filter_logs_by_severity(self):
        """Verifica que se pueden filtrar logs por severidad."""
        info_logs = AuditLog.objects.filter(severity='info')
        warning_logs = AuditLog.objects.filter(severity='warning')
        
        self.assertEqual(info_logs.count(), 5)
        self.assertEqual(warning_logs.count(), 5)
        
        print(f"✅ Filtrado por severidad: Info={info_logs.count()}, Warning={warning_logs.count()}")
    
    def test_logs_ordered_by_timestamp(self):
        """Verifica que los logs están ordenados por timestamp."""
        logs = AuditLog.objects.all()
        timestamps = [log.timestamp for log in logs]
        
        # Verificar que están en orden descendente
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))
        
        print(f"✅ Logs ordenados correctamente por timestamp")
