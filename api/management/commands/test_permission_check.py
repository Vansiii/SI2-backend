"""
Management command para probar la verificación de permisos
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from api.models import FinancialInstitution
from api.permissions import HasPermission

User = get_user_model()


class Command(BaseCommand):
    help = 'Prueba la verificación de permisos simulando un request'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email del usuario')
        parser.add_argument('permission', type=str, help='Código del permiso a verificar')

    def handle(self, *args, **options):
        email = options['email']
        permission_code = options['permission']
        
        self.stdout.write("=" * 70)
        self.stdout.write(f"TEST DE VERIFICACIÓN DE PERMISO")
        self.stdout.write("=" * 70)
        self.stdout.write(f"Usuario: {email}")
        self.stdout.write(f"Permiso: {permission_code}")
        self.stdout.write("")
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ Usuario no encontrado"))
            return
        
        # Crear un request simulado
        factory = RequestFactory()
        request = factory.get('/api/test/')
        request.user = user
        
        # Obtener tenant del usuario
        membership = user.institution_memberships.filter(is_active=True).first()
        if membership:
            request.tenant = membership.institution
            self.stdout.write(f"✅ Tenant: {request.tenant.name}")
        else:
            request.tenant = None
            self.stdout.write(f"⚠️  Sin tenant")
        
        self.stdout.write("")
        
        # Crear instancia de permiso
        permission_checker = HasPermission(permission_code)
        
        # Verificar permiso
        has_perm = permission_checker.has_permission(request, None)
        
        self.stdout.write("=" * 70)
        if has_perm:
            self.stdout.write(self.style.SUCCESS(f"✅ PERMISO CONCEDIDO"))
        else:
            self.stdout.write(self.style.ERROR(f"❌ PERMISO DENEGADO"))
        self.stdout.write("=" * 70)
        self.stdout.write("")
        
        # Diagnóstico adicional
        self.stdout.write("Diagnóstico:")
        self.stdout.write(f"  - Usuario autenticado: {request.user.is_authenticated}")
        self.stdout.write(f"  - Tiene perfil: {hasattr(request.user, 'profile')}")
        
        if hasattr(request.user, 'profile'):
            profile = request.user.profile
            self.stdout.write(f"  - Es SaaS Admin: {profile.is_saas_admin()}")
            self.stdout.write(f"  - Tipo de usuario: {profile.user_type}")
            
            if request.tenant:
                perms = profile.get_permissions_in_institution(request.tenant)
                self.stdout.write(f"  - Permisos en institución: {perms.count()}")
                has_specific = profile.has_permission(permission_code, request.tenant)
                self.stdout.write(f"  - Tiene '{permission_code}': {has_specific}")
