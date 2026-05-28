"""Tests para CU-11: Gestionar Originación de Créditos."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from api.audit.models import AuditLog
from api.branches.models import Branch
from api.clients.models import Client
from api.identity_verification.models import IdentityVerification
from api.loans.models import LoanApplication, LoanApplicationStatusHistory
from api.loans.originacion.services import (
    CreditApplicationService,
    CreditApplicationValidationError,
    InvalidStatusTransitionError,
)
from api.products.models import CreditProduct
from api.roles.models import Role, UserRole
from api.tenants.models import FinancialInstitution, FinancialInstitutionMembership

User = get_user_model()

pytestmark = pytest.mark.django_db


def _create_user(email: str, first_name: str, last_name: str, *, is_staff: bool = False):
    return User.objects.create_user(
        username=email,
        email=email,
        password='testpass123',
        first_name=first_name,
        last_name=last_name,
        is_staff=is_staff,
    )


def _create_client(user: User, institution: FinancialInstitution) -> Client:
    return Client.objects.create(
        institution=institution,
        user=user,
        client_type='NATURAL',
        document_type='CI',
        document_number=f"CI-{uuid4().hex[:10].upper()}",
        birth_date=date(1990, 1, 1),
        mobile_phone='+59170000000',
        address='Av. Principal 123',
        city='La Paz',
        department='La Paz',
        country='Bolivia',
        employment_status='EMPLOYED',
        monthly_income=Decimal('3000.00'),
        additional_income=Decimal('0.00'),
        is_active=True,
        kyc_status='VERIFIED',
    )


def _create_product(institution: FinancialInstitution, *, active: bool = True) -> CreditProduct:
    suffix = uuid4().hex[:8]
    return CreditProduct.objects.create(
        institution=institution,
        name=f'Crédito Personal {suffix}',
        code=f'CR-{suffix.upper()}',
        product_type='PERSONAL',
        description='Producto de prueba para CU-11',
        is_active=active,
        min_amount=Decimal('1000.00'),
        max_amount=Decimal('50000.00'),
        min_term_months=6,
        max_term_months=60,
        interest_rate=Decimal('12.50'),
        interest_type='FIXED',
        payment_frequency='MONTHLY',
        amortization_system='FRENCH',
    )


def _create_branch(institution: FinancialInstitution, name: str) -> Branch:
    return Branch.objects.create(
        institution=institution,
        name=name,
        address='Calle 1',
        city='La Paz',
        is_active=True,
    )


def _create_identity(user: User, institution: FinancialInstitution, status: str = 'APPROVED'):
    return IdentityVerification.objects.create(
        institution=institution,
        user=user,
        provider_session_id=f'session-{uuid4().hex}',
        verification_url='https://example.com/verification',
        status=status,
        decision=status if status in {'APPROVED', 'DECLINED', 'MANUAL_REVIEW'} else 'PENDING',
    )


def _create_application(
    *,
    institution: FinancialInstitution,
    client: Client,
    product: CreditProduct,
    creator: User,
    branch: Branch | None = None,
    status: str = LoanApplication.Status.DRAFT,
    requested_amount: Decimal = Decimal('5000.00'),
    term_months: int = 24,
    purpose: str = 'Necesidad de capital',
    monthly_income: Decimal = Decimal('3000.00'),
    employment_type: str = LoanApplication.EmploymentType.EMPLOYED,
):
    application = LoanApplication.objects.create(
        institution=institution,
        client=client,
        product=product,
        branch=branch,
        requested_amount=requested_amount,
        term_months=term_months,
        purpose=purpose,
        monthly_income=monthly_income,
        employment_type=employment_type,
        status=status,
        created_by=creator,
        updated_by=creator,
    )
    if status == LoanApplication.Status.SUBMITTED:
        application.submitted_at = application.created_at
        application.save(update_fields=['submitted_at'])
    return application


class TestCreditApplicationService:
    def setup_method(self):
        self.service = CreditApplicationService()

    @pytest.fixture
    def institution(self):
        return FinancialInstitution.objects.create(
            name='Banco CU11',
            slug=f'banco-cu11-{uuid4().hex[:6]}',
            institution_type='banking',
            is_active=True,
        )

    @pytest.fixture
    def branch(self, institution):
        return _create_branch(institution, 'Sucursal Central')

    @pytest.fixture
    def product(self, institution):
        return _create_product(institution)

    @pytest.fixture
    def inactive_product(self, institution):
        return _create_product(institution, active=False)

    @pytest.fixture
    def borrower_user(self):
        return _create_user('borrower@example.com', 'Ana', 'Pérez')

    @pytest.fixture
    def borrower_client(self, borrower_user, institution):
        return _create_client(borrower_user, institution)

    @pytest.fixture
    def staff_user(self, institution):
        user = _create_user('staff@example.com', 'Luis', 'Gómez')
        FinancialInstitutionMembership.objects.create(
            institution=institution,
            user=user,
            is_active=True,
        )
        role = Role.objects.create(
            institution=institution,
            name='Analista CU11',
            description='Rol interno para CU-11',
            is_active=True,
        )
        UserRole.objects.create(
            user=user,
            role=role,
            institution=institution,
            is_active=True,
        )
        return user

    @pytest.fixture
    def outsider_user(self):
        return _create_user('outsider@example.com', 'No', 'Role')

    def test_create_draft_success_records_audit(self, borrower_user, borrower_client, institution, product, branch):
        application = self.service.create_draft(
            borrower_user,
            institution,
            {
                'product_id': product.id,
                'requested_amount': Decimal('5000.00'),
                'term_months': 24,
                'purpose': 'Compra de equipo',
                'monthly_income': Decimal('3000.00'),
                'employment_type': LoanApplication.EmploymentType.EMPLOYED,
                'employment_description': 'Empleado fijo',
                'branch_id': branch.id,
                'additional_data': {'source': 'web'},
            },
        )

        assert application.status == LoanApplication.Status.DRAFT
        assert application.created_by == borrower_user
        assert application.updated_by == borrower_user
        assert application.client == borrower_client
        assert AuditLog.objects.filter(action='create', resource_id=application.id).count() == 1

    def test_submit_blocks_missing_required_fields(self, borrower_user, borrower_client, institution, product):
        _create_identity(borrower_user, institution, status='APPROVED')
        application = _create_application(
            institution=institution,
            client=borrower_client,
            product=product,
            creator=borrower_user,
        )
        application.monthly_income = None
        application.save(update_fields=['monthly_income'])

        with pytest.raises(CreditApplicationValidationError):
            self.service.submit_application(borrower_user, application)

    def test_submit_blocks_inactive_product(self, borrower_user, borrower_client, institution, inactive_product):
        _create_identity(borrower_user, institution, status='APPROVED')
        application = _create_application(
            institution=institution,
            client=borrower_client,
            product=inactive_product,
            creator=borrower_user,
        )

        with pytest.raises(CreditApplicationValidationError):
            self.service.submit_application(borrower_user, application)

    def test_submit_blocks_amount_out_of_range(self, borrower_user, borrower_client, institution, product):
        _create_identity(borrower_user, institution, status='APPROVED')
        application = _create_application(
            institution=institution,
            client=borrower_client,
            product=product,
            creator=borrower_user,
            requested_amount=Decimal('900.00'),
        )

        with pytest.raises(CreditApplicationValidationError):
            self.service.submit_application(borrower_user, application)

    def test_submit_blocks_term_out_of_range(self, borrower_user, borrower_client, institution, product):
        _create_identity(borrower_user, institution, status='APPROVED')
        application = _create_application(
            institution=institution,
            client=borrower_client,
            product=product,
            creator=borrower_user,
            term_months=4,
        )

        with pytest.raises(CreditApplicationValidationError):
            self.service.submit_application(borrower_user, application)

    def test_submit_blocks_without_identity_verification(self, borrower_user, borrower_client, institution, product):
        application = _create_application(
            institution=institution,
            client=borrower_client,
            product=product,
            creator=borrower_user,
        )

        with pytest.raises(CreditApplicationValidationError):
            self.service.submit_application(borrower_user, application)

    def test_submit_allows_approved_identity(self, borrower_user, borrower_client, institution, product):
        _create_identity(borrower_user, institution, status='APPROVED')
        application = _create_application(
            institution=institution,
            client=borrower_client,
            product=product,
            creator=borrower_user,
        )

        submitted = self.service.submit_application(borrower_user, application)

        assert submitted.status == LoanApplication.Status.SUBMITTED
        assert submitted.submitted_at is not None
        assert LoanApplicationStatusHistory.objects.filter(
            application=application,
            new_status=LoanApplication.Status.SUBMITTED,
        ).exists()
        assert AuditLog.objects.filter(action='system_action', resource_id=application.id).exists()

    def test_change_status_requires_internal_role(self, outsider_user, borrower_client, institution, product):
        application = _create_application(
            institution=institution,
            client=borrower_client,
            product=product,
            creator=outsider_user,
            status=LoanApplication.Status.SUBMITTED,
        )

        with pytest.raises(CreditApplicationValidationError):
            self.service.change_status(
                outsider_user,
                application,
                LoanApplication.Status.IN_REVIEW,
                reason='Revisión inicial',
            )

    def test_change_status_creates_timeline_and_audit(self, staff_user, borrower_client, institution, product):
        application = _create_application(
            institution=institution,
            client=borrower_client,
            product=product,
            creator=staff_user,
            status=LoanApplication.Status.SUBMITTED,
        )

        updated = self.service.change_status(
            staff_user,
            application,
            LoanApplication.Status.OBSERVED,
            reason='Falta adjuntar respaldo',
        )

        assert updated.status == LoanApplication.Status.OBSERVED
        assert updated.observation_reason == 'Falta adjuntar respaldo'
        assert LoanApplicationStatusHistory.objects.filter(
            application=application,
            new_status=LoanApplication.Status.OBSERVED,
        ).exists()
        assert AuditLog.objects.filter(action='update_full', resource_id=application.id).exists()

    def test_change_status_rejects_invalid_transition(self, staff_user, borrower_client, institution, product):
        application = _create_application(
            institution=institution,
            client=borrower_client,
            product=product,
            creator=staff_user,
            status=LoanApplication.Status.APPROVED,
        )

        with pytest.raises(InvalidStatusTransitionError):
            self.service.change_status(
                staff_user,
                application,
                LoanApplication.Status.DRAFT,
                reason='No permitido',
            )


class TestCreditApplicationAPI:
    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def institution(self):
        return FinancialInstitution.objects.create(
            name='Banco API CU11',
            slug=f'banco-api-cu11-{uuid4().hex[:6]}',
            institution_type='banking',
            is_active=True,
        )

    @pytest.fixture
    def other_institution(self):
        return FinancialInstitution.objects.create(
            name='Banco API CU11 2',
            slug=f'banco-api-cu11-2-{uuid4().hex[:6]}',
            institution_type='banking',
            is_active=True,
        )

    @pytest.fixture
    def branch(self, institution):
        return _create_branch(institution, 'Sucursal Central')

    @pytest.fixture
    def other_branch(self, other_institution):
        return _create_branch(other_institution, 'Sucursal Sur')

    @pytest.fixture
    def product(self, institution):
        return _create_product(institution)

    @pytest.fixture
    def other_product(self, other_institution):
        return _create_product(other_institution)

    @pytest.fixture
    def borrower_user(self):
        return _create_user('borrower.api@example.com', 'Ana', 'Pérez')

    @pytest.fixture
    def borrower_client(self, borrower_user, institution):
        return _create_client(borrower_user, institution)

    @pytest.fixture
    def other_borrower_user(self):
        return _create_user('other.api@example.com', 'Omar', 'Ruiz')

    @pytest.fixture
    def other_borrower_client(self, other_borrower_user, institution):
        return _create_client(other_borrower_user, institution)

    @pytest.fixture
    def staff_user(self, institution):
        user = _create_user('staff.api@example.com', 'Luis', 'Gómez')
        FinancialInstitutionMembership.objects.create(
            institution=institution,
            user=user,
            is_active=True,
        )
        role = Role.objects.create(
            institution=institution,
            name='Analista API',
            description='Rol para API CU-11',
            is_active=True,
        )
        UserRole.objects.create(
            user=user,
            role=role,
            institution=institution,
            is_active=True,
        )
        return user

    @pytest.fixture
    def approved_identity(self, borrower_user, institution):
        return _create_identity(borrower_user, institution, status='APPROVED')

    @pytest.fixture
    def create_payload(self, product, branch):
        return {
            'product_id': product.id,
            'requested_amount': '5000.00',
            'term_months': 24,
            'purpose': 'Compra de equipo',
            'monthly_income': '3000.00',
            'employment_type': LoanApplication.EmploymentType.EMPLOYED,
            'employment_description': 'Empleado fijo',
            'branch_id': branch.id,
            'additional_data': {'source': 'web'},
        }

    def test_borrower_creates_draft_application(self, api_client, borrower_user, borrower_client, create_payload):
        api_client.force_authenticate(user=borrower_user)
        response = api_client.post(reverse('loans:credit-application-list'), create_payload, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['status'] == LoanApplication.Status.DRAFT
        assert LoanApplication.objects.count() == 1

    def test_borrower_lists_only_own_applications(self, api_client, borrower_user, borrower_client, other_borrower_user, other_borrower_client, institution, product, branch):
        own_app = _create_application(
            institution=institution,
            client=borrower_client,
            product=product,
            creator=borrower_user,
            branch=branch,
        )
        _create_application(
            institution=institution,
            client=other_borrower_client,
            product=product,
            creator=other_borrower_user,
            branch=branch,
        )

        api_client.force_authenticate(user=borrower_user)
        response = api_client.get(reverse('loans:credit-application-list'))

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['id'] == own_app.id

    def test_staff_lists_tenant_applications(self, api_client, staff_user, borrower_client, institution, other_institution, product, other_product, branch, other_branch):
        first_app = _create_application(
            institution=institution,
            client=borrower_client,
            product=product,
            creator=staff_user,
            branch=branch,
        )
        outsider_client = _create_client(_create_user('other.tenant@example.com', 'Sara', 'Lopez'), other_institution)
        _create_application(
            institution=other_institution,
            client=outsider_client,
            product=other_product,
            creator=staff_user,
            branch=other_branch,
        )

        api_client.force_authenticate(user=staff_user)
        response = api_client.get(reverse('loans:credit-application-list'))

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['id'] == first_app.id

    def test_cross_tenant_detail_access_is_blocked(self, api_client, staff_user, other_institution, other_product, other_branch):
        outsider_client = _create_client(_create_user('tenant2@example.com', 'Tania', 'Mora'), other_institution)
        other_app = _create_application(
            institution=other_institution,
            client=outsider_client,
            product=other_product,
            creator=staff_user,
            branch=other_branch,
        )

        api_client.force_authenticate(user=staff_user)
        response = api_client.get(reverse('loans:credit-application-detail', kwargs={'pk': other_app.id}))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_submit_endpoint_success(self, api_client, borrower_user, borrower_client, institution, product, branch, approved_identity):
        application = _create_application(
            institution=institution,
            client=borrower_client,
            product=product,
            creator=borrower_user,
            branch=branch,
        )

        api_client.force_authenticate(user=borrower_user)
        response = api_client.post(reverse('loans:credit-application-submit', kwargs={'pk': application.id}))

        assert response.status_code == status.HTTP_200_OK
        application.refresh_from_db()
        assert application.status == LoanApplication.Status.SUBMITTED

    def test_change_status_requires_role(self, api_client, borrower_user, borrower_client, institution, product, branch):
        application = _create_application(
            institution=institution,
            client=borrower_client,
            product=product,
            creator=borrower_user,
            branch=branch,
            status=LoanApplication.Status.SUBMITTED,
        )

        api_client.force_authenticate(user=borrower_user)
        response = api_client.post(
            reverse('loans:credit-application-change-status', kwargs={'pk': application.id}),
            {'new_status': LoanApplication.Status.IN_REVIEW},
            format='json',
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_staff_can_change_status_and_borrower_sees_visible_timeline(
        self,
        api_client,
        staff_user,
        borrower_user,
        borrower_client,
        institution,
        product,
        branch,
    ):
        application = _create_application(
            institution=institution,
            client=borrower_client,
            product=product,
            creator=borrower_user,
            branch=branch,
            status=LoanApplication.Status.SUBMITTED,
        )

        api_client.force_authenticate(user=staff_user)
        response = api_client.post(
            reverse('loans:credit-application-change-status', kwargs={'pk': application.id}),
            {'new_status': LoanApplication.Status.OBSERVED, 'reason': 'Falta respaldo'},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        application.refresh_from_db()
        assert application.status == LoanApplication.Status.OBSERVED

        api_client.force_authenticate(user=borrower_user)
        timeline_response = api_client.get(reverse('loans:credit-application-timeline', kwargs={'pk': application.id}))

        assert timeline_response.status_code == status.HTTP_200_OK
        assert len(timeline_response.data) == 1
        assert timeline_response.data[0]['new_status'] == LoanApplication.Status.OBSERVED

    def test_comments_visibility_for_borrower(self, api_client, staff_user, borrower_user, borrower_client, institution, product, branch):
        application = _create_application(
            institution=institution,
            client=borrower_client,
            product=product,
            creator=borrower_user,
            branch=branch,
            status=LoanApplication.Status.IN_REVIEW,
        )

        api_client.force_authenticate(user=staff_user)
        staff_comment = api_client.post(
            reverse('loans:credit-application-comments', kwargs={'pk': application.id}),
            {'comment': 'Comentario interno', 'is_internal': True},
            format='json',
        )

        api_client.force_authenticate(user=borrower_user)
        borrower_comment = api_client.post(
            reverse('loans:credit-application-comments', kwargs={'pk': application.id}),
            {'comment': 'Comentario del cliente', 'is_internal': True},
            format='json',
        )

        comments_response = api_client.get(reverse('loans:credit-application-comments', kwargs={'pk': application.id}))

        assert staff_comment.status_code == status.HTTP_201_CREATED
        assert borrower_comment.status_code == status.HTTP_201_CREATED
        assert borrower_comment.data['is_internal'] is False
        assert comments_response.status_code == status.HTTP_200_OK
        assert len(comments_response.data) == 1
        assert comments_response.data[0]['comment'] == 'Comentario del cliente'

    def test_filters_and_pagination_work(self, api_client, borrower_user, borrower_client, institution, product, branch):
        for index in range(11):
            _create_application(
                institution=institution,
                client=borrower_client,
                product=product,
                creator=borrower_user,
                branch=branch,
                status=LoanApplication.Status.SUBMITTED,
                purpose=f'Submitted {index}',
            )

        for index in range(11):
            _create_application(
                institution=institution,
                client=borrower_client,
                product=product,
                creator=borrower_user,
                branch=branch,
                status=LoanApplication.Status.DRAFT,
                purpose=f'Draft {index}',
            )

        api_client.force_authenticate(user=borrower_user)
        response = api_client.get(
            reverse('loans:credit-application-list'),
            {'status': LoanApplication.Status.SUBMITTED, 'page_size': 5, 'page': 2},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 11
        assert response.data['current_page'] == 2
        assert response.data['page_size'] == 5
        assert len(response.data['results']) == 5