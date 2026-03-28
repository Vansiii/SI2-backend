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
            role=FinancialInstitutionMembership.Role.ADMIN,
        )

        return RegisterUserResult(user=user, institution=institution, membership=membership)

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
