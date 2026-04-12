"""
Tests para modelos de clientes.
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.contrib.auth import get_user_model
from api.clients.models import Client, ClientDocument
from api.tenants.models import FinancialInstitution

User = get_user_model()


@pytest.mark.django_db
class TestClientModel:
    """Tests para el modelo Client."""
    
    @pytest.fixture
    def institution(self):
        """Crea una institución de prueba."""
        return FinancialInstitution.objects.create(
            name='Banco Test',
            slug='banco-test',
            
            is_active=True
        )
    
    @pytest.fixture
    def client_data(self, institution):
        """Datos de prueba para crear un cliente."""
        return {
            'institution': institution,
            'client_type': 'NATURAL',
            'first_name': 'Juan',
            'last_name': 'Pérez',
            'document_type': 'CI',
            'document_number': '12345678',
            'document_extension': 'LP',
            'birth_date': date(1990, 1, 15),
            'gender': 'M',
            'email': 'juan.perez@example.com',
            'phone': '+591 70123456',
            'mobile_phone': '+591 71234567',
            'address': 'Av. Principal 123',
            'city': 'La Paz',
            'department': 'La Paz',
            'country': 'Bolivia',
            'postal_code': '0000',
            'employment_status': 'EMPLOYED',
            'employer_name': 'Empresa ABC',
            'employer_nit': '1234567890',
            'job_title': 'Ingeniero',
            'monthly_income': Decimal('5000.00'),
            'additional_income': Decimal('500.00'),
        }
    
    # ============================================================
    # TESTS DE CREACIÓN Y CAMPOS BÁSICOS
    # ============================================================
    
    def test_create_client_minimal(self, institution):
        """Test crear un cliente con campos mínimos requeridos."""
        client = Client.objects.create(
            institution=institution,
            client_type='NATURAL',
            first_name='Juan',
            last_name='Pérez',
            document_type='CI',
            document_number='12345678',
            birth_date=date(1990, 1, 15),
            phone='+591 70123456',
            address='Av. Principal 123',
            city='La Paz',
            department='La Paz',
            employment_status='EMPLOYED',
            monthly_income=Decimal('5000.00'),
        )
        
        assert client.id is not None
        assert client.first_name == 'Juan'
        assert client.last_name == 'Pérez'
        assert client.is_active is True
        assert client.kyc_status == 'PENDING'
    
    def test_create_client_complete(self, client_data):
        """Test crear un cliente con todos los campos."""
        client = Client.objects.create(**client_data)
        
        assert client.id is not None
        assert client.client_type == 'NATURAL'
        assert client.first_name == 'Juan'
        assert client.last_name == 'Pérez'
        assert client.document_number == '12345678'
        assert client.document_extension == 'LP'
        assert client.email == 'juan.perez@example.com'
        assert client.phone == '+591 70123456'
        assert client.mobile_phone == '+591 71234567'
        assert client.employer_name == 'Empresa ABC'
        assert client.monthly_income == Decimal('5000.00')
        assert client.additional_income == Decimal('500.00')
        assert client.is_active is True
        assert client.verified_at is None
    
    def test_client_str_representation(self, client_data):
        """Test representación en string del cliente."""
        client = Client.objects.create(**client_data)
        expected = 'Juan Pérez - 12345678'
        assert str(client) == expected
    
    def test_client_get_full_name(self, client_data):
        """Test método get_full_name."""
        client = Client.objects.create(**client_data)
        assert client.get_full_name() == 'Juan Pérez'
    
    def test_client_get_total_monthly_income(self, client_data):
        """Test método get_total_monthly_income."""
        client = Client.objects.create(**client_data)
        assert client.get_total_monthly_income() == Decimal('5500.00')
    
    def test_client_get_age(self, client_data):
        """Test método get_age."""
        client = Client.objects.create(**client_data)
        age = client.get_age()
        # Cliente nacido en 1990, debería tener 36 años en 2026
        assert age >= 35 and age <= 37  # Rango para evitar problemas con fechas
    
    # ============================================================
    # TESTS DE VALIDACIONES
    # ============================================================
    
    def test_unique_document_per_institution(self, client_data):
        """Test que el documento debe ser único por institución."""
        # Crear primer cliente
        Client.objects.create(**client_data)
        
        # Intentar crear segundo cliente con mismo documento en misma institución
        with pytest.raises(IntegrityError):
            Client.objects.create(**client_data)
    
    def test_same_document_different_institutions(self, client_data):
        """Test que el mismo documento puede existir en diferentes instituciones."""
        # Crear primer cliente
        client1 = Client.objects.create(**client_data)
        
        # Crear segunda institución
        institution2 = FinancialInstitution.objects.create(
            name='Banco Test 2',
            slug='banco-test-2',
            
            is_active=True
        )
        
        # Crear segundo cliente con mismo documento pero diferente institución
        client_data['institution'] = institution2
        client2 = Client.objects.create(**client_data)
        
        assert client1.document_number == client2.document_number
        assert client1.institution != client2.institution
    
    def test_email_validation(self, client_data):
        """Test validación de email."""
        client_data['email'] = 'invalid-email'
        client = Client(**client_data)
        
        with pytest.raises(ValidationError):
            client.full_clean()
    
    def test_monthly_income_positive(self, client_data):
        """Test que el ingreso mensual debe ser positivo."""
        client_data['monthly_income'] = Decimal('-1000.00')
        client = Client(**client_data)
        
        with pytest.raises(ValidationError):
            client.full_clean()
    
    def test_additional_income_positive(self, client_data):
        """Test que el ingreso adicional debe ser positivo."""
        client_data['additional_income'] = Decimal('-500.00')
        client = Client(**client_data)
        
        with pytest.raises(ValidationError):
            client.full_clean()
    
    def test_document_number_format(self, client_data):
        """Test validación de formato de número de documento."""
        # Formato válido
        client_data['document_number'] = 'ABC-123'
        client = Client(**client_data)
        client.full_clean()  # No debe lanzar error
        
        # Formato inválido (caracteres especiales no permitidos)
        client_data['document_number'] = 'ABC@123'
        client = Client(**client_data)
        with pytest.raises(ValidationError):
            client.full_clean()
    
    def test_phone_format(self, client_data):
        """Test validación de formato de teléfono."""
        # Formatos válidos
        valid_phones = ['+591 70123456', '70123456', '+591-70-123456', '(591) 70123456']
        
        for phone in valid_phones:
            client_data['phone'] = phone
            client_data['document_number'] = f'DOC{valid_phones.index(phone)}'
            client = Client(**client_data)
            client.full_clean()  # No debe lanzar error
            client.save()
            client.delete()
    
    # ============================================================
    # TESTS DE TIPOS Y ESTADOS
    # ============================================================
    
    def test_client_types(self, client_data):
        """Test tipos de cliente válidos."""
        valid_types = ['NATURAL', 'JURIDICA']
        
        for client_type in valid_types:
            client_data['client_type'] = client_type
            client_data['document_number'] = f'DOC{client_type}'
            client = Client.objects.create(**client_data)
            assert client.client_type == client_type
            client.delete()
    
    def test_document_types(self, client_data):
        """Test tipos de documento válidos."""
        valid_types = ['CI', 'NIT', 'PASSPORT', 'RUC']
        
        for doc_type in valid_types:
            client_data['document_type'] = doc_type
            client_data['document_number'] = f'DOC{doc_type}'
            client = Client.objects.create(**client_data)
            assert client.document_type == doc_type
            client.delete()
    
    def test_employment_statuses(self, client_data):
        """Test estados de empleo válidos."""
        valid_statuses = ['EMPLOYED', 'SELF_EMPLOYED', 'BUSINESS_OWNER', 'RETIRED', 'UNEMPLOYED', 'OTHER']
        
        for status in valid_statuses:
            client_data['employment_status'] = status
            client_data['document_number'] = f'DOC{status}'
            client = Client.objects.create(**client_data)
            assert client.employment_status == status
            client.delete()
    
    def test_kyc_statuses(self, client_data):
        """Test estados KYC válidos."""
        valid_statuses = ['PENDING', 'VERIFIED', 'REJECTED', 'EXPIRED']
        
        for kyc_status in valid_statuses:
            client_data['kyc_status'] = kyc_status
            client_data['document_number'] = f'DOC{kyc_status}'
            client = Client.objects.create(**client_data)
            assert client.kyc_status == kyc_status
            client.delete()
    
    def test_risk_levels(self, client_data):
        """Test niveles de riesgo válidos."""
        valid_levels = ['LOW', 'MEDIUM', 'HIGH']
        
        for risk_level in valid_levels:
            client_data['risk_level'] = risk_level
            client_data['document_number'] = f'DOC{risk_level}'
            client = Client.objects.create(**client_data)
            assert client.risk_level == risk_level
            client.delete()
    
    def test_gender_choices(self, client_data):
        """Test opciones de género válidas."""
        valid_genders = ['M', 'F', 'O']
        
        for gender in valid_genders:
            client_data['gender'] = gender
            client_data['document_number'] = f'DOC{gender}'
            client = Client.objects.create(**client_data)
            assert client.gender == gender
            client.delete()
    
    # ============================================================
    # TESTS DE OPERACIONES
    # ============================================================
    
    def test_deactivate_client(self, client_data):
        """Test desactivar un cliente."""
        client = Client.objects.create(**client_data)
        assert client.is_active is True
        
        client.is_active = False
        client.save()
        
        assert client.is_active is False
    
    def test_update_client_fields(self, client_data):
        """Test actualizar campos del cliente."""
        client = Client.objects.create(**client_data)
        
        # Actualizar varios campos
        client.phone = '+591 70999999'
        client.address = 'Nueva Dirección 456'
        client.monthly_income = Decimal('6000.00')
        client.save()
        
        # Verificar cambios
        client.refresh_from_db()
        assert client.phone == '+591 70999999'
        assert client.address == 'Nueva Dirección 456'
        assert client.monthly_income == Decimal('6000.00')
    
    def test_client_ordering(self, client_data):
        """Test ordenamiento de clientes por fecha de creación."""
        # Crear varios clientes
        client1 = Client.objects.create(
            **{**client_data, 'first_name': 'Ana', 'document_number': '11111111'}
        )
        client2 = Client.objects.create(
            **{**client_data, 'first_name': 'Carlos', 'document_number': '22222222'}
        )
        client3 = Client.objects.create(
            **{**client_data, 'first_name': 'Beatriz', 'document_number': '33333333'}
        )
        
        clients = Client.objects.all()
        
        # Verificar que están ordenados por fecha de creación (más reciente primero)
        assert clients[0].id == client3.id
        assert clients[1].id == client2.id
        assert clients[2].id == client1.id
    
    def test_client_indexes(self, client_data):
        """Test que los índices están funcionando."""
        # Crear varios clientes
        for i in range(10):
            client_data['document_number'] = f'1234567{i}'
            client_data['email'] = f'client{i}@example.com'
            Client.objects.create(**client_data)
        
        # Búsquedas que deberían usar índices
        client = Client.objects.filter(document_number='12345670').first()
        assert client is not None
        
        client = Client.objects.filter(email='client5@example.com').first()
        assert client is not None
        
        client = Client.objects.filter(kyc_status='PENDING').first()
        assert client is not None


@pytest.mark.django_db
class TestClientDocumentModel:
    """Tests para el modelo ClientDocument."""
    
    @pytest.fixture
    def institution(self):
        """Crea una institución de prueba."""
        return FinancialInstitution.objects.create(
            name='Banco Test',
            slug='banco-test',
            
            is_active=True
        )
    
    @pytest.fixture
    def client(self, institution):
        """Crea un cliente de prueba."""
        return Client.objects.create(
            institution=institution,
            client_type='NATURAL',
            first_name='Juan',
            last_name='Pérez',
            document_type='CI',
            document_number='12345678',
            birth_date=date(1990, 1, 15),
            phone='+591 70123456',
            address='Av. Principal 123',
            city='La Paz',
            department='La Paz',
            employment_status='EMPLOYED',
            monthly_income=Decimal('5000.00'),
        )
    
    @pytest.fixture
    def user(self, institution):
        """Crea un usuario de prueba."""
        return User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
    
    def test_create_client_document(self, client, institution):
        """Test crear un documento de cliente."""
        document = ClientDocument.objects.create(
            institution=institution,
            client=client,
            category='IDENTITY',
            document_name='Cédula de Identidad',
            file='test.pdf',
        )
        
        assert document.id is not None
        assert document.client == client
        assert document.category == 'IDENTITY'
        assert document.verified is False
    
    def test_document_categories(self, client, institution):
        """Test categorías de documentos válidas."""
        valid_categories = ['IDENTITY', 'INCOME', 'ADDRESS', 'EMPLOYMENT', 'BANK', 'TAX', 'OTHER']
        
        for category in valid_categories:
            document = ClientDocument.objects.create(
                institution=institution,
                client=client,
                category=category,
                document_name=f'Documento {category}',
                file=f'test_{category}.pdf',
            )
            assert document.category == category
            document.delete()
    
    def test_document_str_representation(self, client, institution):
        """Test representación en string del documento."""
        document = ClientDocument.objects.create(
            institution=institution,
            client=client,
            category='IDENTITY',
            document_name='Cédula de Identidad',
            file='test.pdf',
        )
        
        expected = 'Cédula de Identidad - Juan Pérez'
        assert str(document) == expected
    
    def test_document_verification(self, client, institution, user):
        """Test verificación de documento."""
        from django.utils import timezone
        
        document = ClientDocument.objects.create(
            institution=institution,
            client=client,
            category='IDENTITY',
            document_name='Cédula de Identidad',
            file='test.pdf',
        )
        
        assert document.verified is False
        assert document.verified_at is None
        assert document.verified_by is None
        
        # Verificar documento
        document.verified = True
        document.verified_at = timezone.now()
        document.verified_by = user
        document.save()
        
        assert document.verified is True
        assert document.verified_at is not None
        assert document.verified_by == user
    
    def test_document_cascade_delete(self, client, institution):
        """Test que los documentos se eliminan cuando se elimina el cliente."""
        # Crear documentos
        ClientDocument.objects.create(
            institution=institution,
            client=client,
            category='IDENTITY',
            document_name='Documento 1',
            file='test1.pdf',
        )
        ClientDocument.objects.create(
            institution=institution,
            client=client,
            category='INCOME',
            document_name='Documento 2',
            file='test2.pdf',
        )
        
        assert ClientDocument.objects.filter(client=client).count() == 2
        
        # Eliminar cliente
        client.delete()
        
        # Verificar que los documentos también se eliminaron
        assert ClientDocument.objects.filter(client_id=client.id).count() == 0
