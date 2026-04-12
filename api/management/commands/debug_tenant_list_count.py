"""
Comando para debuggear el conteo de usuarios en la lista de tenants
"""
from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from api.tenants.models import FinancialInstitution


class Command(BaseCommand):
    help = 'Debuggea el conteo de usuarios en la lista de tenants'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== DEBUGGEANDO CONTEO DE USUARIOS ===\n'))
        
        # Obtener Banco Union con la misma anotación que usa la vista (CORREGIDA)
        banco_union = FinancialInstitution.objects.annotate(
            users_count=Count('memberships', filter=Q(memberships__is_active=True), distinct=True),
            roles_count=Count('role_set', distinct=True)
        ).get(slug='banco-union')
        
        self.stdout.write(f'Banco Union (ID: {banco_union.id})')
        self.stdout.write(f'users_count (con anotación): {banco_union.users_count}')
        self.stdout.write(f'roles_count (con anotación): {banco_union.roles_count}')
        
        # Contar manualmente
        manual_count = banco_union.memberships.filter(is_active=True).count()
        self.stdout.write(f'Conteo manual de memberships activas: {manual_count}')
        
        # Verificar si hay problema con joins
        self.stdout.write(self.style.SUCCESS('\n=== PROBANDO DIFERENTES ANOTACIONES ===\n'))
        
        # Sin distinct
        test1 = FinancialInstitution.objects.annotate(
            users_count=Count('memberships', filter=Q(memberships__is_active=True))
        ).get(slug='banco-union')
        self.stdout.write(f'Sin distinct: {test1.users_count}')
        
        # Con distinct
        test2 = FinancialInstitution.objects.annotate(
            users_count=Count('memberships', filter=Q(memberships__is_active=True), distinct=True)
        ).get(slug='banco-union')
        self.stdout.write(f'Con distinct: {test2.users_count}')
        
        # Verificar si el problema es el select_related
        test3 = FinancialInstitution.objects.annotate(
            users_count=Count('memberships', filter=Q(memberships__is_active=True)),
            roles_count=Count('role_set', distinct=True)
        ).select_related('subscription').get(slug='banco-union')
        self.stdout.write(f'Con select_related(subscription): {test3.users_count}')
        
        # Listar todas las instituciones como lo hace la vista (CORREGIDA)
        self.stdout.write(self.style.SUCCESS('\n=== TODAS LAS INSTITUCIONES (como en la vista CORREGIDA) ===\n'))
        
        institutions = FinancialInstitution.objects.annotate(
            users_count=Count('memberships', filter=Q(memberships__is_active=True), distinct=True),
            roles_count=Count('role_set', distinct=True)
        ).select_related('subscription').all()
        
        for inst in institutions:
            manual = inst.memberships.filter(is_active=True).count()
            match = '✓' if inst.users_count == manual else '✗ DIFERENTE'
            self.stdout.write(
                f'{match} {inst.name}: anotación={inst.users_count}, manual={manual}'
            )
