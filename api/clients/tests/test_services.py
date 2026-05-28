"""
Tests para servicios de clientes.
"""

import pytest
from decimal import Decimal
from datetime import date
from django.contrib.auth import get_user_model
from api.clients.models import Client
from api.clients.services import (
    ClientManagementService,
    CreateClientInput,
    UpdateClientInput,
)
from api.tenants.models import FinancialInstitution

User = get_user_model()


@pytest.mark.django_db
class TestClientManagementService:
    """Tests para ClientManagementService."""
    
    @pytest.fixture
    def institution(self):
        return FinancialInstitution.objects.create(
            name='Banco Test',
            slug='banco-test',
            
            is_active=True
        )
    
    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
    
    @pytest.fixture
    def service(self):
        return ClientManagementService()
    
    @pytest.fixture
    def client_input(self):
        return CreateClientInput(
            client_type='NATURAL',
            first_name='Juan',
            last_name='Pérez',
            document_type='CI',
            document_number='12345678',
            document_extension='LP',
            birth_date=date(1990, 1, 15),
            gender='M',
            email='juan.perez@example.com',
            phone='+591 70123456',
            mobile_phone='+591 71234567',
            address='Av. Principal 123',
            city='La Paz',
            department='La Paz',
            
            postal_code='0000',
            employment_status='EMPLOYED',
            employer_name='Empresa ABC',
            employer_nit='1234567890',
            job_title='Ingeniero',
            employment_start_date=date(2015, 1, 1),
            monthly_income=Decimal('5000.00'),
            additional_income=Decimal('500.00'),
            notes='Cliente de prueba',
        )
    
    # ============================================================
    # TESTS DE CREACIÓN
    # ============================================================
    
    def test_create_client_success(self, service, institution, client_input, user):
        """Test crear cliente exitosamente."""
        result = service.create_client(
            institution_id=institution.id,
            input_data=client_input,
            created_by=user
        )
        
        assert result.success is True
        assert result.client is not None
        assert result.client.first_name == 'Juan'
        assert result.client.last_name == 'Pérez'
        assert result.client.document_number == '12345678'
        assert result.client.institution == institution
        assert 'exitosamente' in result.message.lower()
    
    def test_create_client_duplicate_document(self, service, institution, client_input):
        """Test crear cliente con documento duplicado debe fallar."""
        # Crear primer cliente
        result1 = service.create_client(
            institution_id=institution.id,
            input_data=client_input
        )
        assert result1.success is True
        
        # Intentar crear segundo con mismo documento
        result2 = service.create_client(
            institution_id=institution.id,
            input_data=client_input
        )
        
        assert result2.success is False
        assert result2.client is None
        assert 'duplicado' in result2.message.lower() or 'existe' in result2.message.lower()
        assert result2.errors is not None
    
    def test_create_client_minimal_data(self, service, institution):
        """Test crear cliente con datos mínimos."""
        minimal_input = CreateClientInput(
            client_type='NATURAL',
            first_name='Juan',
            last_name='Pérez',
            document_type='CI',
            document_number='99999999',
            birth_date=date(1990, 1, 15),
            phone='70123456',
            address='Dirección',
            city='La Paz',
            department='La Paz',
            employment_status='EMPLOYED',
            monthly_income=Decimal('5000.00'),
        )
        
        result = service.create_client(
            institution_id=institution.id,
            input_data=minimal_input
        )
        
        assert result.success is True
        assert result.client is not None
        assert result.client.first_name == 'Juan'
    
    # ============================================================
    # TESTS DE ACTUALIZACIÓN
    # ============================================================
    
    def test_update_client_success(self, service, institution, client_input):
        """Test actualizar cliente exitosamente."""
        # Crear cliente
        create_result = service.create_client(
            institution_id=institution.id,
            input_data=client_input
        )
        client_id = create_result.client.id
        
        # Actualizar
        update_input = UpdateClientInput(
            phone='+591 70999999',
            address='Nueva Dirección 456',
            monthly_income=Decimal('6000.00'),
        )
        
        result = service.update_client(
            client_id=client_id,
            institution_id=institution.id,
            input_data=update_input
        )
        
        assert result.success is True
        assert result.client.phone == '+591 70999999'
        assert result.client.address == 'Nueva Dirección 456'
        assert result.client.monthly_income == Decimal('6000.00')
    
    def test_update_client_not_found(self, service, institution):
        """Test actualizar cliente inexistente debe fallar."""
        update_input = UpdateClientInput(phone='+591 70999999')
        
        result = service.update_client(
            client_id=99999,  # ID inexistente
            institution_id=institution.id,
            input_data=update_input
        )
        
        assert result.success is False
        assert result.client is None
        assert 'no encontrado' in result.message.lower()
    
    def test_update_client_partial(self, service, institution, client_input):
        """Test actualización parcial de cliente."""
        # Crear cliente
        create_result = service.create_client(
            institution_id=institution.id,
            input_data=client_input
        )
        client_id = create_result.client.id
        original_address = create_result.client.address
        
        # Actualizar solo el teléfono
        update_input = UpdateClientInput(phone='+591 70888888')
        
        result = service.update_client(
            client_id=client_id,
            institution_id=institution.id,
            input_data=update_input
        )
        
        assert result.success is True
        assert result.client.phone == '+591 70888888'
        assert result.client.address == original_address  # No cambió
    
    # ============================================================
    # TESTS DE CONSULTA
    # ============================================================
    
    def test_get_client_success(self, service, institution, client_input):
        """Test obtener cliente por ID."""
        # Crear cliente
        create_result = service.create_client(
            institution_id=institution.id,
            input_data=client_input
        )
        client_id = create_result.client.id
        
        # Obtener
        client = service.get_client(
            client_id=client_id,
            institution_id=institution.id
        )
        
        assert client is not None
        assert client.id == client_id
        assert client.first_name == 'Juan'
    
    def test_get_client_not_found(self, service, institution):
        """Test obtener cliente inexistente."""
        client = service.get_client(
            client_id=99999,
            institution_id=institution.id
        )
        
        assert client is None
    
    def test_list_clients(self, service, institution):
        """Test listar clientes."""
        # Crear varios clientes
        for i in range(5):
            input_data = CreateClientInput(
                client_type='NATURAL',
                first_name=f'Cliente{i}',
                last_name='Test',
                document_type='CI',
                document_number=f'1234567{i}',
                birth_date=date(1990, 1, 1),
                phone='70123456',
                address='Address',
                city='La Paz',
                department='La Paz',
                employment_status='EMPLOYED',
                monthly_income=Decimal('5000.00'),
            )
            service.create_client(institution_id=institution.id, input_data=input_data)
        
        # Listar
        clients = service.list_clients(institution_id=institution.id)
        
        assert clients.count() == 5
    
    def test_list_clients_filter_active(self, service, institution):
        """Test listar clientes filtrados por estado activo."""
        # Crear clientes activos e inactivos
        for i in range(5):
            input_data = CreateClientInput(
                client_type='NATURAL',
                first_name=f'Cliente{i}',
                last_name='Test',
                document_type='CI',
                document_number=f'1234567{i}',
                birth_date=date(1990, 1, 1),
                phone='70123456',
                address='Address',
                city='La Paz',
                department='La Paz',
                employment_status='EMPLOYED',
                monthly_income=Decimal('5000.00'),
            )
            result = service.create_client(institution_id=institution.id, input_data=input_data)
            
            # Desactivar algunos
            if i % 2 == 0:
                result.client.is_active = False
                result.client.save()
        
        # Listar solo activos
        active_clients = service.list_clients(institution_id=institution.id, is_active=True)
        assert active_clients.count() == 2
        
        # Listar solo inactivos
        inactive_clients = service.list_clients(institution_id=institution.id, is_active=False)
        assert inactive_clients.count() == 3
    
    def test_list_clients_filter_kyc_status(self, service, institution):
        """Test listar clientes filtrados por estado KYC."""
        # Crear clientes con diferentes estados KYC
        for i in range(5):
            input_data = CreateClientInput(
                client_type='NATURAL',
                first_name=f'Cliente{i}',
                last_name='Test',
                document_type='CI',
                document_number=f'1234567{i}',
                birth_date=date(1990, 1, 1),
                phone='70123456',
                address='Address',
                city='La Paz',
                department='La Paz',
                employment_status='EMPLOYED',
                monthly_income=Decimal('5000.00'),
            )
            result = service.create_client(institution_id=institution.id, input_data=input_data)
            
            # Cambiar estado KYC
            if i < 3:
                result.client.kyc_status = 'VERIFIED'
                result.client.save()
        
        # Listar verificados
        verified = service.list_clients(institution_id=institution.id, kyc_status='VERIFIED')
        assert verified.count() == 3
        
        # Listar pendientes
        pending = service.list_clients(institution_id=institution.id, kyc_status='PENDING')
        assert pending.count() == 2
    
    def test_list_clients_search(self, service, institution):
        """Test búsqueda de clientes."""
        # Crear clientes
        input_data1 = CreateClientInput(
            client_type='NATURAL',
            first_name='Juan',
            last_name='Pérez',
            document_type='CI',
            document_number='11111111',
            birth_date=date(1990, 1, 1),
            phone='70123456',
            address='Address',
            city='La Paz',
            department='La Paz',
            employment_status='EMPLOYED',
            monthly_income=Decimal('5000.00'),
        )
        service.create_client(institution_id=institution.id, input_data=input_data1)
        
        input_data2 = CreateClientInput(
            client_type='NATURAL',
            first_name='María',
            last_name='García',
            document_type='CI',
            document_number='22222222',
            birth_date=date(1990, 1, 1),
            phone='70123456',
            address='Address',
            city='La Paz',
            department='La Paz',
            employment_status='EMPLOYED',
            monthly_income=Decimal('5000.00'),
        )
        service.create_client(institution_id=institution.id, input_data=input_data2)
        
        # Buscar por nombre
        results = service.list_clients(institution_id=institution.id, search='Juan')
        assert results.count() == 1
        assert results.first().first_name == 'Juan'
        
        # Buscar por documento
        results = service.list_clients(institution_id=institution.id, search='22222222')
        assert results.count() == 1
        assert results.first().document_number == '22222222'
    
    # ============================================================
    # TESTS DE DESACTIVACIÓN
    # ============================================================
    
    def test_deactivate_client_success(self, service, institution, client_input):
        """Test desactivar cliente exitosamente."""
        # Crear cliente
        create_result = service.create_client(
            institution_id=institution.id,
            input_data=client_input
        )
        client_id = create_result.client.id
        
        # Desactivar
        result = service.deactivate_client(
            client_id=client_id,
            institution_id=institution.id,
            reason='Cliente solicitó baja'
        )
        
        assert result.success is True
        assert result.client.is_active is False
        assert 'Cliente solicitó baja' in result.client.notes
    
    def test_deactivate_client_not_found(self, service, institution):
        """Test desactivar cliente inexistente debe fallar."""
        result = service.deactivate_client(
            client_id=99999,
            institution_id=institution.id
        )
        
        assert result.success is False
        assert result.client is None
        assert 'no encontrado' in result.message.lower()
    
    # ============================================================
    # TESTS DE MULTI-TENANCY
    # ============================================================
    
    def test_client_isolation_between_institutions(self, service):
        """Test que los clientes están aislados entre instituciones."""
        # Crear dos instituciones
        institution1 = FinancialInstitution.objects.create(
            name='Banco 1',
            slug='banco-1',
            
            is_active=True
        )
        institution2 = FinancialInstitution.objects.create(
            name='Banco 2',
            slug='banco-2',
            
            is_active=True
        )
        
        # Crear cliente en institución 1
        input_data = CreateClientInput(
            client_type='NATURAL',
            first_name='Juan',
            last_name='Pérez',
            document_type='CI',
            document_number='12345678',
            birth_date=date(1990, 1, 1),
            phone='70123456',
            address='Address',
            city='La Paz',
            department='La Paz',
            employment_status='EMPLOYED',
            monthly_income=Decimal('5000.00'),
        )
        result1 = service.create_client(institution_id=institution1.id, input_data=input_data)
        
        # Listar clientes de institución 1
        clients1 = service.list_clients(institution_id=institution1.id)
        assert clients1.count() == 1
        
        # Listar clientes de institución 2 (debe estar vacío)
        clients2 = service.list_clients(institution_id=institution2.id)
        assert clients2.count() == 0
        
        # Intentar obtener cliente de institución 1 desde institución 2
        client = service.get_client(
            client_id=result1.client.id,
            institution_id=institution2.id
        )
        assert client is None
