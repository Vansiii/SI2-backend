"""
Tests para verificar el flujo completo de registro de administrador de tenant.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model

from api.models import (
    FinancialInstitution,
    FinancialInstitutionMembership,
    Role,
    UserRole,
    Permission,
    UserProfile
)
from api.registration.services import RegisterUserInput, RegisterUserService

User = get_user_model()


class RegistrationFlowTestCase(TestCase):
    """
    Tests para verificar que el flujo de registro asigna correctamente
    todos los permisos al administrador del tenant.
    """
    
    def setUp(self):
        """Crear permisos necesarios para las pruebas."""
        # Crear permisos de prueba (simulando seed_permissions)
        self.permission_codes = [
            # Usuarios
            'users.view', 'users.create', 'users.edit', 'users.delete',
            'users.assign_roles', 'users.view_audit',
            # Roles
            'roles.view', 'roles.create', 'roles.edit', 'roles.delete',
            'roles.assign_permissions',
            # Institución
            'institution.view', 'institution.edit', 'institution.view_stats',
            # Créditos
            'credits.view', 'credits.create', 'credits.edit', 'credits.delete',
            'credits.approve', 'credits.reject', 'credits.disburse',
            'credits.view_documents', 'credits.upload_documents',
            # Clientes
            'borrowers.view', 'borrowers.create', 'borrowers.edit', 'borrowers.delete',
            'borrowers.view_history', 'borrowers.view_documents',
            # Cobranza
            'collection.view', 'collection.create_payment', 'collection.send_reminders',
            'collection.manage_overdue', 'collection.restructure', 'collection.write_off',
            # Reportes
            'reports.view', 'reports.create', 'reports.export',
            'reports.financial', 'reports.audit',
            # Configuración
            'config.view', 'config.edit', 'config.products', 'config.interest_rates',
            # Auditoría
            'audit.view', 'audit.export',
            'security.view_events', 'security.resolve_events',
        ]
        
        for code in self.permission_codes:
            Permission.objects.get_or_create(
                code=code,
                defaults={
                    'name': code.replace('.', ' ').title(),
                    'description': f'Permiso para {code}',
                    'is_active': True
                }
            )
    
    def test_registration_creates_user(self):
        """Verificar que el registro crea el usuario correctamente."""
        service = RegisterUserService()
        input_data = RegisterUserInput(
            company_name='Banco de Prueba',
            institution_type='commercial_bank',
            first_name='Juan',
            last_name='Pérez',
            email='juan.perez@test.com',
            password='TestPassword123!'
        )
        
        result = service.execute(input_data)
        
        # Verificar usuario creado
        self.assertIsNotNone(result.user)
        self.assertEqual(result.user.email, 'juan.perez@test.com')
        self.assertEqual(result.user.first_name, 'Juan')
        self.assertEqual(result.user.last_name, 'Pérez')
        self.assertTrue(result.user.is_active)
    
    def test_registration_creates_institution(self):
        """Verificar que el registro crea la institución correctamente."""
        service = RegisterUserService()
        input_data = RegisterUserInput(
            company_name='Banco de Prueba',
            institution_type='commercial_bank',
            first_name='Juan',
            last_name='Pérez',
            email='juan.perez@test.com',
            password='TestPassword123!'
        )
        
        result = service.execute(input_data)
        
        # Verificar institución creada
        self.assertIsNotNone(result.institution)
        self.assertEqual(result.institution.name, 'Banco de Prueba')
        self.assertEqual(result.institution.institution_type, 'commercial_bank')
        self.assertTrue(result.institution.is_active)
    
    def test_registration_creates_membership(self):
        """Verificar que el registro crea la membresía correctamente."""
        service = RegisterUserService()
        input_data = RegisterUserInput(
            company_name='Banco de Prueba',
            institution_type='commercial_bank',
            first_name='Juan',
            last_name='Pérez',
            email='juan.perez@test.com',
            password='TestPassword123!'
        )
        
        result = service.execute(input_data)
        
        # Verificar membresía creada
        self.assertIsNotNone(result.membership)
        self.assertEqual(result.membership.user, result.user)
        self.assertEqual(result.membership.institution, result.institution)
    
    def test_registration_creates_admin_role(self):
        """Verificar que el registro crea el rol de administrador."""
        service = RegisterUserService()
        input_data = RegisterUserInput(
            company_name='Banco de Prueba',
            institution_type='commercial_bank',
            first_name='Juan',
            last_name='Pérez',
            email='juan.perez@test.com',
            password='TestPassword123!'
        )
        
        result = service.execute(input_data)
        
        # Verificar rol creado
        admin_role = Role.objects.filter(
            institution=result.institution,
            name='Administrador de Institución'
        ).first()
        
        self.assertIsNotNone(admin_role)
        self.assertTrue(admin_role.is_active)
        self.assertEqual(
            admin_role.description,
            'Administrador con acceso completo a la gestión de la institución'
        )
    
    def test_registration_assigns_all_permissions_to_admin_role(self):
        """
        TEST CRÍTICO: Verificar que el registro asigna TODOS los permisos
        al rol de administrador, no solo los básicos.
        """
        service = RegisterUserService()
        input_data = RegisterUserInput(
            company_name='Banco de Prueba',
            institution_type='commercial_bank',
            first_name='Juan',
            last_name='Pérez',
            email='juan.perez@test.com',
            password='TestPassword123!'
        )
        
        result = service.execute(input_data)
        
        # Obtener el rol de administrador
        admin_role = Role.objects.get(
            institution=result.institution,
            name='Administrador de Institución'
        )
        
        # Verificar que tiene permisos asignados
        assigned_permissions = admin_role.permissions.all()
        assigned_count = assigned_permissions.count()
        
        # Debe tener al menos 40 permisos (considerando que algunos pueden no existir)
        self.assertGreaterEqual(
            assigned_count,
            40,
            f'El rol de administrador solo tiene {assigned_count} permisos. '
            f'Debería tener al menos 40 permisos completos.'
        )
        
        # Verificar que tiene permisos de diferentes categorías
        permission_codes = list(assigned_permissions.values_list('code', flat=True))
        
        # Verificar permisos de usuarios
        self.assertIn('users.view', permission_codes)
        self.assertIn('users.create', permission_codes)
        self.assertIn('users.edit', permission_codes)
        
        # Verificar permisos de roles (CRÍTICO - antes faltaban)
        self.assertIn('roles.view', permission_codes)
        self.assertIn('roles.create', permission_codes)
        
        # Verificar permisos de reportes (CRÍTICO - antes faltaban)
        self.assertIn('reports.view', permission_codes)
        
        # Verificar permisos de configuración (CRÍTICO - antes faltaban)
        self.assertIn('config.view', permission_codes)
        
        # Verificar permisos de créditos
        self.assertIn('credits.view', permission_codes)
        self.assertIn('credits.create', permission_codes)
        
        # Verificar permisos de clientes
        self.assertIn('borrowers.view', permission_codes)
        
        # Verificar permisos de cobranza
        self.assertIn('collection.view', permission_codes)
        
        # Verificar permisos de auditoría
        self.assertIn('audit.view', permission_codes)
    
    def test_registration_assigns_role_to_user(self):
        """Verificar que el registro asigna el rol al usuario."""
        service = RegisterUserService()
        input_data = RegisterUserInput(
            company_name='Banco de Prueba',
            institution_type='commercial_bank',
            first_name='Juan',
            last_name='Pérez',
            email='juan.perez@test.com',
            password='TestPassword123!'
        )
        
        result = service.execute(input_data)
        
        # Verificar UserRole creado
        user_role = UserRole.objects.filter(
            user=result.user,
            institution=result.institution
        ).first()
        
        self.assertIsNotNone(user_role)
        self.assertTrue(user_role.is_active)
        self.assertEqual(user_role.role.name, 'Administrador de Institución')
        self.assertEqual(user_role.assigned_by, result.user)  # Auto-asignado
    
    def test_user_has_all_permissions_after_registration(self):
        """
        TEST CRÍTICO: Verificar que el usuario tiene acceso a todos los
        permisos después del registro.
        """
        service = RegisterUserService()
        input_data = RegisterUserInput(
            company_name='Banco de Prueba',
            institution_type='commercial_bank',
            first_name='Juan',
            last_name='Pérez',
            email='juan.perez@test.com',
            password='TestPassword123!'
        )
        
        result = service.execute(input_data)
        
        # Obtener perfil del usuario
        profile = result.user.profile
        
        # Verificar permisos críticos que antes faltaban
        critical_permissions = [
            'users.view',
            'roles.view',      # CRÍTICO
            'roles.create',    # CRÍTICO
            'reports.view',    # CRÍTICO
            'config.view',     # CRÍTICO
            'credits.view',
            'borrowers.view',
            'collection.view',
            'audit.view',
        ]
        
        for perm_code in critical_permissions:
            has_perm = profile.has_permission(perm_code, result.institution)
            self.assertTrue(
                has_perm,
                f'El usuario NO tiene el permiso {perm_code} después del registro. '
                f'Esto causará que no vea opciones del menú en el frontend.'
            )
    
    def test_registration_with_existing_permissions(self):
        """Verificar que el registro funciona incluso si ya existen algunos permisos."""
        # Crear algunos permisos adicionales
        Permission.objects.create(
            code='custom.permission',
            name='Custom Permission',
            description='Permiso personalizado',
            is_active=True
        )
        
        service = RegisterUserService()
        input_data = RegisterUserInput(
            company_name='Banco de Prueba 2',
            institution_type='fintech',
            first_name='María',
            last_name='González',
            email='maria.gonzalez@test.com',
            password='TestPassword123!'
        )
        
        result = service.execute(input_data)
        
        # Verificar que el registro fue exitoso
        self.assertIsNotNone(result.user)
        self.assertIsNotNone(result.institution)
        
        # Verificar que el rol tiene permisos
        admin_role = Role.objects.get(
            institution=result.institution,
            name='Administrador de Institución'
        )
        
        self.assertGreater(admin_role.permissions.count(), 0)
    
    def test_multiple_registrations_create_separate_roles(self):
        """Verificar que múltiples registros crean roles separados por institución."""
        service = RegisterUserService()
        
        # Primer registro
        result1 = service.execute(RegisterUserInput(
            company_name='Banco A',
            institution_type='commercial_bank',
            first_name='Usuario',
            last_name='Uno',
            email='usuario1@test.com',
            password='TestPassword123!'
        ))
        
        # Segundo registro
        result2 = service.execute(RegisterUserInput(
            company_name='Banco B',
            institution_type='commercial_bank',
            first_name='Usuario',
            last_name='Dos',
            email='usuario2@test.com',
            password='TestPassword123!'
        ))
        
        # Verificar que se crearon roles separados
        role1 = Role.objects.get(
            institution=result1.institution,
            name='Administrador de Institución'
        )
        role2 = Role.objects.get(
            institution=result2.institution,
            name='Administrador de Institución'
        )
        
        self.assertNotEqual(role1.id, role2.id)
        self.assertEqual(role1.permissions.count(), role2.permissions.count())
