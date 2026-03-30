"""
Management command para diagnosticar permisos de usuario
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from api.models import UserRole, FinancialInstitution, Permission

User = get_user_model()


class Command(BaseCommand):
    help = 'Diagnostica permisos de un usuario específico'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email del usuario a diagnosticar')

    def handle(self, *args, **options):
        email = options['email']
        
        self.stdout.write("=" * 70)
        self.stdout.write(f"DIAGNÓSTICO DE PERMISOS: {email}")
        self.stdout.write("=" * 70)
        self.stdout.write("")
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ Usuario no encontrado: {email}"))
            return
        
        self.stdout.write(self.style.SUCCESS(f"✅ Usuario encontrado: {user.email}"))
        self.stdout.write(f"   ID: {user.id}")
        self.stdout.write(f"   Nombre: {user.first_name} {user.last_name}")
        self.stdout.write(f"   Activo: {user.is_active}")
        self.stdout.write("")
        
        # Verificar perfil
        if not hasattr(user, 'profile'):
            self.stdout.write(self.style.ERROR("❌ Usuario no tiene perfil (UserProfile)"))
            return
        
        profile = user.profile
        self.stdout.write(self.style.SUCCESS(f"✅ Perfil encontrado"))
        self.stdout.write(f"   Tipo: {profile.user_type}")
        self.stdout.write(f"   Es SaaS Admin: {profile.is_saas_admin()}")
        self.stdout.write("")
        
        # Verificar memberships
        memberships = user.institution_memberships.filter(is_active=True)
        self.stdout.write(f"📋 Memberships activos: {memberships.count()}")
        for membership in memberships:
            self.stdout.write(f"   - {membership.institution.name} ({membership.institution.slug})")
        self.stdout.write("")
        
        # Verificar roles
        user_roles = UserRole.objects.filter(user=user, is_active=True)
        self.stdout.write(f"🎭 Roles asignados: {user_roles.count()}")
        for ur in user_roles:
            self.stdout.write(f"   - {ur.role.name}")
            self.stdout.write(f"     Institución: {ur.institution.name}")
            self.stdout.write(f"     Permisos en rol: {ur.role.permissions.count()}")
        self.stdout.write("")
        
        # Verificar permisos por institución
        for membership in memberships:
            institution = membership.institution
            self.stdout.write(f"🔑 Permisos en {institution.name}:")
            
            permissions = profile.get_permissions_in_institution(institution)
            self.stdout.write(f"   Total: {permissions.count()}")
            
            # Verificar permiso específico users.view
            has_users_view = profile.has_permission('users.view', institution)
            status_icon = '✅ SÍ' if has_users_view else '❌ NO'
            self.stdout.write(f"   users.view: {status_icon}")
            
            # Mostrar primeros 10 permisos
            if permissions.count() > 0:
                self.stdout.write(f"   Primeros permisos:")
                for perm in permissions[:10]:
                    self.stdout.write(f"     - {perm.code}: {perm.name}")
            self.stdout.write("")
        
        # Verificar si el permiso users.view existe
        self.stdout.write("🔍 Verificando permiso 'users.view' en sistema:")
        try:
            perm = Permission.objects.get(code='users.view')
            self.stdout.write(self.style.SUCCESS(f"   ✅ Permiso existe"))
            self.stdout.write(f"      ID: {perm.id}")
            self.stdout.write(f"      Nombre: {perm.name}")
            self.stdout.write(f"      Activo: {perm.is_active}")
            self.stdout.write(f"      En roles: {perm.roles.count()}")
            
            # Mostrar qué roles tienen este permiso
            roles_with_perm = perm.roles.all()[:5]
            if roles_with_perm:
                self.stdout.write(f"      Roles con este permiso:")
                for role in roles_with_perm:
                    self.stdout.write(f"        - {role.name} ({role.institution.name})")
        except Permission.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"   ❌ Permiso NO existe en la base de datos"))
        self.stdout.write("")
        
        self.stdout.write("=" * 70)
        self.stdout.write(self.style.SUCCESS("FIN DEL DIAGNÓSTICO"))
        self.stdout.write("=" * 70)
