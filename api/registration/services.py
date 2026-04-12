from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.text import slugify

from api.models import FinancialInstitution, FinancialInstitutionMembership


@dataclass(frozen=True)
class RegisterUserInput:
    company_name: str
    institution_type: str
    first_name: str
    last_name: str
    email: str
    password: str
    selected_plan_id: int = None


@dataclass(frozen=True)
class RegisterUserResult:
    user: object
    institution: FinancialInstitution
    membership: FinancialInstitutionMembership


class RegisterUserService:
    @transaction.atomic
    def execute(self, payload: RegisterUserInput) -> RegisterUserResult:
        user_model = get_user_model()
        normalized_email = payload.email.strip().lower()

        user = user_model.objects.create_user(
            username=normalized_email,
            email=normalized_email,
            first_name=payload.first_name.strip(),
            last_name=payload.last_name.strip(),
            password=payload.password,
        )

        institution = FinancialInstitution.objects.create(
            name=payload.company_name.strip(),
            slug=self._build_unique_slug(payload.company_name),
            institution_type=payload.institution_type,
            created_by=user,
        )

        membership = FinancialInstitutionMembership.objects.create(
            institution=institution,
            user=user,
        )
        
        # Crear o obtener rol de Administrador para la institución
        from api.models import Role, UserRole, Permission
        from api.roles.services import PermissionService
        
        admin_role, created = Role.objects.get_or_create(
            institution=institution,
            name='Administrador de Institución',
            defaults={
                'description': 'Administrador con acceso completo a la gestión de la institución',
                'is_active': True
            }
        )
        
        # Si el rol fue creado, asignar TODOS los permisos disponibles
        if created:
            # Obtener todos los permisos activos del catálogo
            all_permissions = Permission.objects.filter(is_active=True)
            
            # Asignar todos los permisos disponibles
            admin_role.permissions.set(all_permissions)
            
            print(f"✓ Rol 'Administrador de Institución' creado con {all_permissions.count()} permisos")
        
        # Asignar rol al usuario
        UserRole.objects.create(
            user=user,
            role=admin_role,
            institution=institution,
            assigned_by=user,  # Auto-asignado en registro
            is_active=True
        )

        # Crear suscripción con el plan seleccionado o plan gratuito por defecto
        self._create_subscription(institution, payload.selected_plan_id)

        return RegisterUserResult(user=user, institution=institution, membership=membership)

    def _create_subscription(self, institution: FinancialInstitution, selected_plan_id: int = None):
        """Crea una suscripción para la institución con el plan seleccionado o el plan gratuito por defecto"""
        from api.saas.models import SubscriptionPlan, Subscription
        from datetime import datetime, timedelta
        
        try:
            if selected_plan_id:
                # Usar el plan seleccionado
                plan = SubscriptionPlan.objects.get(id=selected_plan_id, is_active=True)
            else:
                # Buscar el plan gratuito (precio = 0) o el primer plan activo
                plan = SubscriptionPlan.objects.filter(
                    is_active=True, 
                    price=0
                ).order_by('display_order').first()
                
                if not plan:
                    # Si no hay plan gratuito, usar el primer plan activo
                    plan = SubscriptionPlan.objects.filter(
                        is_active=True
                    ).order_by('display_order').first()
            
            if plan:
                # Determinar fechas según el plan
                start_date = datetime.now().date()
                
                if plan.trial_days > 0:
                    # Plan con período de prueba
                    trial_end_date = start_date + timedelta(days=plan.trial_days)
                    status = 'TRIAL'
                    end_date = None
                elif float(plan.price) == 0:
                    # Plan gratuito permanente
                    trial_end_date = None
                    status = 'ACTIVE'
                    end_date = None
                else:
                    # Plan de pago sin prueba
                    trial_end_date = None
                    status = 'PENDING'  # Requiere activación de pago
                    end_date = None
                
                subscription = Subscription.objects.create(
                    institution=institution,
                    plan=plan,
                    status=status,
                    start_date=start_date,
                    end_date=end_date,
                    trial_end_date=trial_end_date,
                )
                
                print(f"✓ Suscripción creada: {plan.name} para {institution.name} (Estado: {status})")
                return subscription
            else:
                print("⚠ No se encontró ningún plan activo para asignar")
                
        except Exception as e:
            print(f"❌ Error creando suscripción: {e}")
            # No fallar el registro si hay error en la suscripción
            pass

    def _build_unique_slug(self, company_name: str) -> str:
        base_slug = slugify(company_name)[:90] or 'entidad-financiera'
        candidate = base_slug
        suffix = 1

        while FinancialInstitution.objects.filter(slug=candidate).exists():
            suffix += 1
            suffix_label = f'-{suffix}'
            available_chars = max(1, 100 - len(suffix_label))
            candidate = f'{base_slug[:available_chars]}{suffix_label}'

        return candidate
