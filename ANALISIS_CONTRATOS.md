# Análisis para Implementación de Funcionalidad de Contratos

**Fecha**: 30 de Mayo, 2026  
**Proyecto**: Sistema de Gestión de Créditos - SI2  
**Módulo**: Contratos de Crédito  
**Estado**: Análisis Preliminar

---

## 1. RESUMEN EJECUTIVO

Este documento analiza el estado actual del sistema SI2 y define los requisitos para implementar la funcionalidad de **Contratos de Crédito**. El sistema actualmente cuenta con un flujo completo de originación de créditos (CU-11) que llega hasta la aprobación y desembolso, pero **no tiene implementada la generación, firma y gestión de contratos formales**.

### 1.1 Contexto del Sistema Actual

El sistema SI2 es una plataforma SaaS multi-tenant para gestión de créditos financieros que incluye:

- ✅ **Gestión de Clientes** (módulo `clients`)
- ✅ **Productos Crediticios** (módulo `products`)
- ✅ **Originación de Créditos** (módulo `loans` - CU-11)
- ✅ **Garantías y Garantes** (módulo `garantias`)
- ✅ **Verificación de Identidad** (módulo `identity_verification` - CU-13)
- ✅ **Gestión Documental** (módulo `storage` con Supabase)
- ✅ **Auditoría Completa** (módulo `audit`)
- ✅ **Multi-tenancy** (módulo `tenants`)
- ✅ **Sistema de Roles y Permisos** (módulo `roles`)
- ✅ **Sucursales** (módulo `branches`)
- ✅ **Reportes** (módulo `reports`)

### 1.2 Brecha Identificada

**FALTA**: Un módulo de **Contratos** que permita:

1. Generar contratos formales a partir de solicitudes aprobadas
2. Gestionar plantillas de contratos personalizables por tenant/producto
3. Permitir firma digital de contratos (prestatario y garantes)
4. Almacenar contratos firmados de forma segura
5. Gestionar el ciclo de vida del contrato (vigente, vencido, liquidado)
6. Vincular contratos con desembolsos y pagos
7. Generar documentos legales en PDF con términos y condiciones

---

## 2. ANÁLISIS DEL FLUJO ACTUAL

### 2.1 Flujo de Originación Existente

```
1. Cliente crea solicitud (DRAFT)
2. Cliente completa datos y envía (SUBMITTED)
3. Staff revisa solicitud (IN_REVIEW)
4. Staff puede observar (OBSERVED) o continuar
5. Staff aprueba con términos finales (APPROVED)
   - approved_amount
   - approved_term_months
   - approved_interest_rate
   - monthly_payment
6. Sistema marca como desembolsada (DISBURSED)
```

### 2.2 Punto de Integración Identificado

**El contrato debe generarse DESPUÉS de la aprobación y ANTES del desembolso:**

```
APPROVED → [GENERAR CONTRATO] → [FIRMAR CONTRATO] → DISBURSED
```

**Nuevo flujo propuesto:**

```
1. Solicitud APROBADA
2. Sistema genera CONTRATO (estado: DRAFT)
3. Staff revisa y publica contrato (estado: PENDING_SIGNATURE)
4. Prestatario firma digitalmente (estado: PARTIALLY_SIGNED)
5. Garantes firman (si aplica) (estado: PARTIALLY_SIGNED)
6. Todos firmaron → Contrato ACTIVE
7. Sistema permite DESEMBOLSO
8. Contrato vinculado a desembolso y plan de pagos
```

---

## 3. ENTIDADES Y MODELOS NECESARIOS

### 3.1 Modelo Principal: `Contract`

```python
class Contract(TenantModel):
    """
    Contrato de crédito generado a partir de una solicitud aprobada.
    """
    
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Borrador'
        PENDING_SIGNATURE = 'PENDING_SIGNATURE', 'Pendiente de Firma'
        PARTIALLY_SIGNED = 'PARTIALLY_SIGNED', 'Parcialmente Firmado'
        ACTIVE = 'ACTIVE', 'Activo'
        CANCELLED = 'CANCELLED', 'Cancelado'
        COMPLETED = 'COMPLETED', 'Completado'
        DEFAULTED = 'DEFAULTED', 'En Mora'
    
    # Relaciones
    loan_application = models.OneToOneField(
        'loans.LoanApplication',
        on_delete=models.PROTECT,
        related_name='contract'
    )
    
    template = models.ForeignKey(
        'contracts.ContractTemplate',
        on_delete=models.PROTECT,
        related_name='contracts'
    )
    
    # Datos del contrato
    contract_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices)
    
    # Términos financieros (snapshot de la aprobación)
    principal_amount = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    term_months = models.PositiveIntegerField()
    monthly_payment = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Fechas importantes
    contract_date = models.DateField()
    start_date = models.DateField()
    end_date = models.DateField()
    first_payment_date = models.DateField()
    
    # Documentos
    pdf_file = models.ForeignKey(
        'storage.FileResource',
        on_delete=models.SET_NULL,
        null=True,
        related_name='contracts_as_pdf'
    )
    
    # Firmas
    borrower_signed_at = models.DateTimeField(null=True, blank=True)
    borrower_signature_ip = models.GenericIPAddressField(null=True)
    
    # Metadata
    terms_and_conditions = models.TextField()
    special_clauses = models.JSONField(default=dict)
```


### 3.2 Modelo: `ContractTemplate`

```python
class ContractTemplate(TenantModel):
    """
    Plantilla de contrato personalizable por tenant y producto.
    """
    
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50)
    
    # Relación con productos (opcional)
    product = models.ForeignKey(
        'products.CreditProduct',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contract_templates'
    )
    
    # Contenido de la plantilla (HTML con variables)
    template_content = models.TextField()
    
    # Variables disponibles: {{borrower_name}}, {{amount}}, etc.
    available_variables = models.JSONField(default=list)
    
    # Configuración
    is_active = models.BooleanField(default=True)
    requires_guarantor_signature = models.BooleanField(default=False)
    
    # Términos legales
    terms_and_conditions = models.TextField()
    legal_clauses = models.JSONField(default=list)
```

### 3.3 Modelo: `ContractSignature`

```python
class ContractSignature(TenantModel):
    """
    Registro de firmas digitales en un contrato.
    """
    
    class SignerType(models.TextChoices):
        BORROWER = 'BORROWER', 'Prestatario'
        GUARANTOR = 'GUARANTOR', 'Garante'
        INSTITUTION = 'INSTITUTION', 'Institución'
    
    contract = models.ForeignKey(
        'contracts.Contract',
        on_delete=models.CASCADE,
        related_name='signatures'
    )
    
    signer_type = models.CharField(max_length=20, choices=SignerType.choices)
    
    # Referencia al firmante
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    
    guarantor = models.ForeignKey(
        'garantias.Guarantor',
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    
    # Datos de la firma
    signed_at = models.DateTimeField()
    signature_method = models.CharField(max_length=50)  # 'digital', 'biometric', 'otp'
    signature_data = models.TextField()  # Hash o datos de la firma
    ip_address = models.GenericIPAddressField()
    device_info = models.JSONField(default=dict)
```

### 3.4 Modelo: `ContractAmortizationSchedule`

```python
class ContractAmortizationSchedule(TenantModel):
    """
    Tabla de amortización del contrato.
    """
    
    contract = models.ForeignKey(
        'contracts.Contract',
        on_delete=models.CASCADE,
        related_name='amortization_schedule'
    )
    
    payment_number = models.PositiveIntegerField()
    due_date = models.DateField()
    
    # Montos
    principal_amount = models.DecimalField(max_digits=12, decimal_places=2)
    interest_amount = models.DecimalField(max_digits=12, decimal_places=2)
    total_payment = models.DecimalField(max_digits=12, decimal_places=2)
    remaining_balance = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Estado
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
```

---

## 4. FUNCIONALIDADES REQUERIDAS

### 4.1 Generación de Contratos

**Requisitos:**
- Generar contrato automáticamente cuando solicitud pasa a APPROVED
- Usar plantilla configurada para el producto
- Reemplazar variables con datos reales (cliente, montos, fechas)
- Generar PDF del contrato
- Almacenar en Supabase Storage
- Crear tabla de amortización

**Endpoint propuesto:**
```
POST /api/contracts/generate-from-application/{loan_application_id}/
```

### 4.2 Gestión de Plantillas

**Requisitos:**
- CRUD de plantillas por tenant
- Editor de plantillas con variables dinámicas
- Preview de plantillas con datos de ejemplo
- Versionado de plantillas
- Plantilla por defecto y plantillas por producto

**Endpoints propuestos:**
```
GET    /api/contracts/templates/
POST   /api/contracts/templates/
GET    /api/contracts/templates/{id}/
PATCH  /api/contracts/templates/{id}/
DELETE /api/contracts/templates/{id}/
POST   /api/contracts/templates/{id}/preview/
```

### 4.3 Firma Digital

**Requisitos:**
- Prestatario puede firmar desde web o móvil
- Garantes pueden firmar (si aplica)
- Validación de identidad antes de firmar
- Registro de IP, dispositivo y timestamp
- Notificación por email cuando se requiere firma
- Contrato solo se activa cuando todas las firmas están completas

**Endpoints propuestos:**
```
POST /api/contracts/{id}/sign/
GET  /api/contracts/{id}/signatures/
POST /api/contracts/{id}/request-signature/{user_id}/
```

### 4.4 Visualización y Descarga

**Requisitos:**
- Ver contrato en PDF
- Descargar contrato firmado
- Ver tabla de amortización
- Ver historial de firmas
- Timeline de eventos del contrato

**Endpoints propuestos:**
```
GET /api/contracts/{id}/
GET /api/contracts/{id}/pdf/
GET /api/contracts/{id}/amortization-schedule/
GET /api/contracts/{id}/timeline/
```


### 4.5 Gestión del Ciclo de Vida

**Requisitos:**
- Contrato ACTIVE después de todas las firmas
- Contrato COMPLETED cuando se paga totalmente
- Contrato DEFAULTED si hay mora significativa
- Cancelación de contratos (con razón)
- Renovación o refinanciamiento

---

## 5. INTEGRACIONES NECESARIAS

### 5.1 Con Módulo de Préstamos (`loans`)

**Cambios requeridos en `LoanApplication`:**

```python
# Agregar campo para vincular contrato
contract_generated = models.BooleanField(default=False)

# Agregar validación antes de desembolso
def can_be_disbursed(self):
    if not self.contract_generated:
        return False
    if not hasattr(self, 'contract'):
        return False
    if self.contract.status != 'ACTIVE':
        return False
    return self.status == self.Status.APPROVED
```

**Nuevo estado intermedio (opcional):**
```python
APPROVED → CONTRACT_PENDING → CONTRACT_SIGNED → DISBURSED
```

### 5.2 Con Módulo de Garantías (`garantias`)

- Vincular garantes al contrato
- Requerir firma de garantes si el contrato lo especifica
- Validar que garantías estén aprobadas antes de generar contrato

### 5.3 Con Módulo de Storage (`storage`)

- Almacenar PDFs de contratos en Supabase
- Generar URLs firmadas para descarga segura
- Versionado de documentos


### 5.4 Con Módulo de Auditoría (`audit`)

- Registrar todas las acciones sobre contratos
- Auditar firmas digitales
- Registrar cambios de estado
- Registrar accesos a documentos

### 5.5 Con Sistema de Notificaciones

- Email cuando contrato está listo para firmar
- Email cuando todas las firmas están completas
- Recordatorios de firma pendiente
- Notificación de activación de contrato

---

## 6. DEPENDENCIAS TÉCNICAS

### 6.1 Librerías Python Necesarias

```python
# Para generación de PDFs
reportlab==4.0.7          # Generación de PDFs
weasyprint==60.1          # HTML a PDF (alternativa)
jinja2==3.1.2             # Motor de plantillas

# Para firmas digitales
cryptography==41.0.7      # Criptografía y hashing
pyotp==2.9.0              # OTP para validación adicional

# Para procesamiento de documentos
pypdf==3.17.1             # Manipulación de PDFs
pillow==10.1.0            # Procesamiento de imágenes (firmas)
```

### 6.2 Servicios Externos (Opcionales)

**Para firma digital avanzada:**
- DocuSign API
- Adobe Sign API
- HelloSign API

**Para ahora:** Implementar firma digital simple con:
- Validación de identidad existente (CU-13)
- Captura de IP y dispositivo
- Hash criptográfico del documento
- Timestamp verificable

---

## 7. ESTRUCTURA DE ARCHIVOS PROPUESTA

```
api/contracts/
├── __init__.py
├── apps.py
├── models.py                    # Contract, ContractTemplate, ContractSignature, etc.
├── serializers.py               # Serializers para API
├── views.py                     # ViewSets principales
├── urls.py                      # Rutas del módulo
├── permissions.py               # Permisos específicos
├── admin.py                     # Admin de Django
├── services/
│   ├── __init__.py
│   ├── contract_generator.py   # Generación de contratos
│   ├── pdf_generator.py        # Generación de PDFs
│   ├── signature_service.py    # Gestión de firmas
│   └── amortization_service.py # Cálculo de amortización
├── templates/
│   └── contracts/
│       ├── default_template.html
│       └── email_signature_request.html
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_services.py
│   └── test_api.py
└── migrations/
    └── 0001_initial.py
```

---

## 8. PERMISOS Y ROLES

### 8.1 Permisos Nuevos

```python
# Permisos para contratos
BORROWER_CAN_VIEW_OWN_CONTRACT
BORROWER_CAN_SIGN_OWN_CONTRACT
BORROWER_CAN_DOWNLOAD_OWN_CONTRACT

STAFF_CAN_VIEW_TENANT_CONTRACTS
STAFF_CAN_GENERATE_CONTRACTS
STAFF_CAN_MANAGE_CONTRACT_TEMPLATES

ADMIN_CAN_MANAGE_ALL_CONTRACTS
ADMIN_CAN_CANCEL_CONTRACTS

GUARANTOR_CAN_VIEW_CONTRACT
GUARANTOR_CAN_SIGN_CONTRACT
```

### 8.2 Matriz de Permisos

| Acción | Prestatario | Garante | Staff | Admin |
|--------|:-----------:|:-------:|:-----:|:-----:|
| Ver propio contrato | ✅ | ✅ | ✅ | ✅ |
| Firmar contrato | ✅ | ✅ | - | - |
| Descargar PDF | ✅ | ✅ | ✅ | ✅ |
| Generar contrato | - | - | ✅ | ✅ |
| Editar plantillas | - | - | - | ✅ |
| Cancelar contrato | - | - | - | ✅ |

---

## 9. FLUJO DE TRABAJO DETALLADO

### 9.1 Generación de Contrato

```
1. Solicitud aprobada (APPROVED)
2. Staff hace clic en "Generar Contrato"
3. Sistema valida:
   - Solicitud en estado APPROVED
   - Todos los datos completos
   - Garantías aprobadas (si aplica)
4. Sistema selecciona plantilla:
   - Plantilla específica del producto
   - O plantilla por defecto del tenant
5. Sistema reemplaza variables:
   - {{borrower_name}} → "Juan Pérez"
   - {{amount}} → "Bs. 50,000.00"
   - {{interest_rate}} → "12.5%"
   - etc.
6. Sistema genera PDF
7. Sistema sube PDF a Supabase Storage
8. Sistema crea registro Contract (status: DRAFT)
9. Sistema genera tabla de amortización
10. Staff revisa contrato
11. Staff publica contrato (status: PENDING_SIGNATURE)
12. Sistema envía notificación al prestatario
```

### 9.2 Firma de Contrato

```
1. Prestatario recibe email con link
2. Prestatario accede al contrato
3. Sistema valida identidad (ya verificada en CU-13)
4. Prestatario lee términos y condiciones
5. Prestatario acepta y firma
6. Sistema registra:
   - Timestamp
   - IP address
   - Dispositivo
   - Hash del documento
7. Sistema actualiza estado:
   - Si hay garantes → PARTIALLY_SIGNED
   - Si no hay garantes → ACTIVE
8. Si hay garantes:
   - Sistema envía notificación a garantes
   - Garantes firman (mismo proceso)
   - Última firma → estado ACTIVE
9. Sistema notifica a staff
10. Staff puede proceder con desembolso
```

---

## 10. CONSIDERACIONES DE SEGURIDAD

### 10.1 Firma Digital

- **Hash del documento**: SHA-256 del PDF antes de firmar
- **Timestamp**: Usar timezone-aware datetime
- **IP logging**: Registrar IP real (considerar proxies)
- **Device fingerprinting**: User-agent, resolución, etc.
- **Validación de identidad**: Requerir 2FA o verificación adicional

### 10.2 Almacenamiento

- PDFs en Supabase Storage con permisos restrictivos
- URLs firmadas con expiración corta (1 hora)
- Encriptación en tránsito (HTTPS)
- Backup automático de contratos

### 10.3 Auditoría

- Registrar TODAS las acciones sobre contratos
- Registrar accesos a PDFs
- Registrar intentos de firma
- Registrar cambios de estado

---

## 11. CASOS DE USO PRINCIPALES

### CU-14: Generar Contrato de Crédito

**Actor**: Staff (Analista de Crédito)

**Precondiciones**:
- Solicitud en estado APPROVED
- Plantilla de contrato configurada
- Garantías aprobadas (si aplica)

**Flujo Principal**:
1. Staff accede a solicitud aprobada
2. Staff hace clic en "Generar Contrato"
3. Sistema genera contrato en borrador
4. Staff revisa contrato
5. Staff publica contrato
6. Sistema notifica a prestatario

**Postcondiciones**:
- Contrato creado en estado PENDING_SIGNATURE
- Prestatario notificado

### CU-15: Firmar Contrato (Prestatario)

**Actor**: Prestatario

**Precondiciones**:
- Contrato en estado PENDING_SIGNATURE
- Identidad verificada

**Flujo Principal**:
1. Prestatario recibe notificación
2. Prestatario accede al contrato
3. Prestatario lee términos
4. Prestatario firma digitalmente
5. Sistema registra firma
6. Sistema actualiza estado

**Postcondiciones**:
- Firma registrada
- Contrato ACTIVE o PARTIALLY_SIGNED

### CU-16: Gestionar Plantillas de Contratos

**Actor**: Administrador

**Precondiciones**:
- Usuario con rol ADMIN

**Flujo Principal**:
1. Admin accede a gestión de plantillas
2. Admin crea/edita plantilla
3. Admin define variables
4. Admin configura términos legales
5. Admin activa plantilla

**Postcondiciones**:
- Plantilla disponible para uso

---

## 12. ESTIMACIÓN DE ESFUERZO

### 12.1 Backend (Django)

| Tarea | Estimación |
|-------|------------|
| Modelos y migraciones | 2 días |
| Serializers y ViewSets | 2 días |
| Servicio de generación de contratos | 3 días |
| Servicio de generación de PDFs | 3 días |
| Servicio de firmas digitales | 2 días |
| Servicio de amortización | 2 días |
| Integración con módulos existentes | 2 días |
| Tests unitarios | 3 días |
| Tests de integración | 2 días |
| **Total Backend** | **21 días** |

### 12.2 Frontend Web (React)

| Tarea | Estimación |
|-------|------------|
| Componentes de visualización | 2 días |
| Formulario de plantillas | 2 días |
| Visor de PDF | 1 día |
| Flujo de firma digital | 2 días |
| Tabla de amortización | 1 día |
| Integración con API | 2 días |
| Tests | 2 días |
| **Total Frontend** | **12 días** |

### 12.3 Mobile (Flutter)

| Tarea | Estimación |
|-------|------------|
| Pantallas de contratos | 2 días |
| Visor de PDF | 1 día |
| Flujo de firma | 2 días |
| Integración con API | 1 día |
| Tests | 1 día |
| **Total Mobile** | **7 días** |

### 12.4 Total Estimado

**Total: 40 días de desarrollo** (aproximadamente 8 semanas con 1 desarrollador full-stack)

---

## 13. PRIORIZACIÓN Y FASES

### Fase 1: MVP (Mínimo Viable) - 3 semanas

**Alcance:**
- Modelo Contract básico
- Generación de contrato desde solicitud aprobada
- Plantilla simple (sin editor avanzado)
- Generación de PDF básico
- Firma digital simple (sin garantes)
- Visualización y descarga

**Entregables:**
- Contrato se genera automáticamente al aprobar
- Prestatario puede ver y firmar
- PDF descargable

### Fase 2: Firmas Múltiples - 2 semanas

**Alcance:**
- Firma de garantes
- Gestión de múltiples firmantes
- Notificaciones por email
- Timeline de firmas

### Fase 3: Gestión Avanzada - 2 semanas

**Alcance:**
- Editor de plantillas
- Variables dinámicas
- Preview de plantillas
- Versionado

### Fase 4: Ciclo de Vida - 1 semana

**Alcance:**
- Estados avanzados (COMPLETED, DEFAULTED)
- Cancelación de contratos
- Renovación/refinanciamiento

---

## 14. RIESGOS Y MITIGACIONES

### 14.1 Riesgos Técnicos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Generación de PDF compleja | Media | Alto | Usar librería probada (ReportLab) |
| Firma digital no válida legalmente | Alta | Alto | Consultar con legal, usar estándares |
| Performance con muchos contratos | Media | Medio | Indexación, paginación, cache |
| Integración con módulos existentes | Baja | Alto | Tests de integración exhaustivos |

### 14.2 Riesgos de Negocio

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Requisitos legales cambiantes | Media | Alto | Plantillas flexibles y editables |
| Rechazo de usuarios | Baja | Medio | UX simple e intuitiva |
| Problemas de cumplimiento | Media | Alto | Auditoría completa, consulta legal |

---

## 15. DEPENDENCIAS Y PREREQUISITOS

### 15.1 Antes de Comenzar

✅ **Ya disponible:**
- Sistema de autenticación y autorización
- Módulo de préstamos funcionando
- Módulo de garantías funcionando
- Sistema de storage (Supabase)
- Sistema de auditoría

❓ **Necesita validación:**
- Requisitos legales específicos del país/región
- Formato de firma digital aceptado
- Términos y condiciones estándar
- Plantilla de contrato base

🔴 **Falta implementar:**
- Sistema de pagos (para vincular con amortización)
- Notificaciones por email (existe pero necesita templates)

### 15.2 Decisiones Pendientes

1. **¿Qué librería usar para PDFs?**
   - Opción A: ReportLab (más control, más complejo)
   - Opción B: WeasyPrint (HTML a PDF, más simple)
   - **Recomendación**: WeasyPrint para MVP, migrar a ReportLab si se necesita más control

2. **¿Firma digital simple o avanzada?**
   - Opción A: Firma simple (checkbox + validación de identidad)
   - Opción B: Firma avanzada (integración con DocuSign/Adobe Sign)
   - **Recomendación**: Firma simple para MVP, integración externa en Fase 4

3. **¿Cuándo generar el contrato?**
   - Opción A: Automático al aprobar
   - Opción B: Manual por staff
   - **Recomendación**: Manual para MVP (más control), automático después

4. **¿Permitir edición de contratos generados?**
   - Opción A: No, solo regenerar
   - Opción B: Sí, con versionado
   - **Recomendación**: No para MVP, versionado en Fase 3

---

## 16. PRÓXIMOS PASOS

### 16.1 Inmediatos (Esta Semana)

1. ✅ **Análisis completado** (este documento)
2. ⏳ **Validar con stakeholders**:
   - Revisar requisitos legales
   - Confirmar flujo de firma
   - Aprobar estimaciones
3. ⏳ **Definir plantilla base de contrato**
4. ⏳ **Crear spec técnico detallado**

### 16.2 Siguientes (Próxima Semana)

1. Crear módulo `api/contracts/`
2. Definir modelos y migraciones
3. Implementar servicio de generación
4. Crear endpoints básicos
5. Tests unitarios

### 16.3 Mediano Plazo (2-3 Semanas)

1. Integración con frontend
2. Implementar firma digital
3. Generación de PDFs
4. Tests de integración
5. Deploy a staging

---

## 17. CONCLUSIONES

### 17.1 Viabilidad

✅ **El proyecto es VIABLE** con las siguientes consideraciones:

1. **Infraestructura existente es sólida**: El sistema tiene todos los módulos base necesarios
2. **Integración clara**: El punto de integración (después de APPROVED) está bien definido
3. **Tecnología probada**: Las librerías necesarias son maduras y estables
4. **Alcance manejable**: Se puede implementar en fases incrementales

### 17.2 Recomendaciones

1. **Comenzar con MVP**: Implementar funcionalidad básica primero
2. **Validar legal**: Consultar requisitos legales antes de implementar firma
3. **Plantilla simple**: Usar plantilla HTML simple para MVP
4. **Tests exhaustivos**: Especialmente en generación de PDFs y firmas
5. **Documentación**: Mantener documentación actualizada del flujo

### 17.3 Valor de Negocio

La implementación de contratos:
- ✅ Completa el flujo de originación de créditos
- ✅ Permite desembolsos formales y legales
- ✅ Facilita auditoría y cumplimiento
- ✅ Mejora experiencia del usuario (firma digital)
- ✅ Reduce trabajo manual (generación automática)
- ✅ Habilita futuros módulos (pagos, cobranza)

---

## 18. APÉNDICES

### A. Variables de Plantilla Sugeridas

```
{{institution_name}}
{{institution_address}}
{{institution_nit}}

{{borrower_name}}
{{borrower_document}}
{{borrower_address}}
{{borrower_email}}

{{contract_number}}
{{contract_date}}
{{start_date}}
{{end_date}}

{{principal_amount}}
{{interest_rate}}
{{term_months}}
{{monthly_payment}}
{{total_amount}}

{{first_payment_date}}
{{last_payment_date}}

{{guarantor_name}}  (si aplica)
{{guarantor_document}}  (si aplica)

{{special_clauses}}
{{terms_and_conditions}}
```

### B. Ejemplo de Plantilla HTML

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Contrato de Crédito</title>
    <style>
        body { font-family: Arial, sans-serif; }
        .header { text-align: center; }
        .section { margin: 20px 0; }
        .signature { margin-top: 50px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>CONTRATO DE CRÉDITO</h1>
        <p>No. {{contract_number}}</p>
    </div>
    
    <div class="section">
        <p>Entre <strong>{{institution_name}}</strong>, en adelante "LA INSTITUCIÓN", 
        y <strong>{{borrower_name}}</strong>, en adelante "EL PRESTATARIO"...</p>
    </div>
    
    <!-- Más contenido -->
    
    <div class="signature">
        <p>_________________________</p>
        <p>Firma del Prestatario</p>
    </div>
</body>
</html>
```

### C. Estructura de Respuesta API

```json
{
  "id": 1,
  "contract_number": "CONT-2026-0001",
  "status": "ACTIVE",
  "loan_application": {
    "id": 123,
    "application_number": "LOAN-1-2026-0001-1234"
  },
  "borrower": {
    "id": 45,
    "name": "Juan Pérez",
    "document": "1234567 LP"
  },
  "financial_terms": {
    "principal_amount": "50000.00",
    "interest_rate": "12.50",
    "term_months": 24,
    "monthly_payment": "2356.78"
  },
  "dates": {
    "contract_date": "2026-05-15",
    "start_date": "2026-05-20",
    "end_date": "2028-05-20",
    "first_payment_date": "2026-06-20"
  },
  "signatures": [
    {
      "signer_type": "BORROWER",
      "signer_name": "Juan Pérez",
      "signed_at": "2026-05-16T10:30:00Z",
      "ip_address": "192.168.1.100"
    }
  ],
  "documents": {
    "pdf_url": "https://storage.supabase.co/...",
    "pdf_expires_at": "2026-05-30T23:59:59Z"
  },
  "created_at": "2026-05-15T14:00:00Z",
  "updated_at": "2026-05-16T10:30:00Z"
}
```

---

**Fin del Análisis**

**Preparado por**: Sistema de Análisis Kiro  
**Fecha**: 30 de Mayo, 2026  
**Versión**: 1.0  
**Estado**: Listo para Revisión


---

## 19. FRONTEND WEB (REACT + TYPESCRIPT) - DETALLADO

### 19.1 Arquitectura del Frontend

El frontend SI2 está organizado con **arquitectura modular basada en features**, similar al backend:

```
src/
├── features/           # Módulos por funcionalidad
│   ├── auth/
│   ├── roles/
│   └── contracts/     # ← NUEVO MÓDULO
├── layouts/           # Layouts compartidos
├── shared/            # Componentes compartidos
└── App.tsx
```

### 19.2 Estructura del Módulo Contracts (Frontend)

```
src/features/contracts/
├── components/
│   ├── ContractViewer.tsx
│   ├── ContractCard.tsx
│   ├── ContractStatusBadge.tsx
│   ├── ContractSignatureModal.tsx
│   ├── AmortizationTable.tsx
│   ├── ContractTimeline.tsx
│   └── PDFViewer.tsx
├── pages/
│   ├── ContractListPage.tsx
│   ├── ContractDetailPage.tsx
│   ├── ContractSignaturePage.tsx
│   └── ContractTemplateManagementPage.tsx
├── services/
│   ├── contractsApi.ts
│   └── pdfService.ts
├── hooks/
│   ├── useContract.ts
│   ├── useContractSignature.ts
│   └── useAmortizationSchedule.ts
└── types.ts
```

### 19.3 Tipos TypeScript

```typescript
// src/features/contracts/types.ts

export interface Contract {
  id: number;
  contract_number: string;
  status: ContractStatus;
  loan_application: {
    id: number;
    application_number: string;
    client_name: string;
  };
  template: {
    id: number;
    name: string;
  };
  
  // Términos financieros
  principal_amount: string;
  interest_rate: string;
  term_months: number;
  monthly_payment: string;
  
  // Fechas
  contract_date: string;
  start_date: string;
  end_date: string;
  first_payment_date: string;
  
  // Documentos
  pdf_url?: string;
  pdf_expires_at?: string;
  
  // Firmas
  borrower_signed_at?: string;
  signatures: ContractSignature[];
  
  // Metadata
  created_at: string;
  updated_at: string;
}

export type ContractStatus = 
  | 'DRAFT'
  | 'PENDING_SIGNATURE'
  | 'PARTIALLY_SIGNED'
  | 'ACTIVE'
  | 'CANCELLED'
  | 'COMPLETED'
  | 'DEFAULTED';

export interface ContractSignature {
  id: number;
  signer_type: 'BORROWER' | 'GUARANTOR' | 'INSTITUTION';
  signer_name: string;
  signed_at: string;
  ip_address: string;
}

export interface AmortizationScheduleItem {
  payment_number: number;
  due_date: string;
  principal_amount: string;
  interest_amount: string;
  total_payment: string;
  remaining_balance: string;
  is_paid: boolean;
  paid_at?: string;
}

export interface ContractTemplate {
  id: number;
  name: string;
  code: string;
  template_content: string;
  is_active: boolean;
  requires_guarantor_signature: boolean;
}
```

### 19.4 Servicio API

```typescript
// src/features/contracts/services/contractsApi.ts

import axios from 'axios';
import { Contract, ContractTemplate, AmortizationScheduleItem } from '../types';

const API_BASE = '/api/contracts';

export const contractsApi = {
  // Listar contratos
  list: async (params?: {
    status?: string;
    loan_application_id?: number;
  }) => {
    const response = await axios.get<{ results: Contract[] }>(API_BASE, { params });
    return response.data;
  },

  // Obtener detalle
  get: async (id: number) => {
    const response = await axios.get<Contract>(`${API_BASE}/${id}/`);
    return response.data;
  },

  // Generar contrato desde solicitud
  generateFromApplication: async (loanApplicationId: number) => {
    const response = await axios.post<Contract>(
      `${API_BASE}/generate-from-application/`,
      { loan_application_id: loanApplicationId }
    );
    return response.data;
  },

  // Publicar contrato
  publish: async (id: number) => {
    const response = await axios.post<Contract>(`${API_BASE}/${id}/publish/`);
    return response.data;
  },

  // Firmar contrato
  sign: async (id: number, pin: string) => {
    const response = await axios.post<Contract>(`${API_BASE}/${id}/sign/`, { pin });
    return response.data;
  },

  // Obtener PDF
  getPDF: async (id: number) => {
    const response = await axios.get<{ pdf_url: string }>(`${API_BASE}/${id}/pdf/`);
    return response.data;
  },

  // Obtener tabla de amortización
  getAmortizationSchedule: async (id: number) => {
    const response = await axios.get<AmortizationScheduleItem[]>(
      `${API_BASE}/${id}/amortization-schedule/`
    );
    return response.data;
  },

  // Plantillas
  templates: {
    list: async () => {
      const response = await axios.get<{ results: ContractTemplate[] }>(
        `${API_BASE}/templates/`
      );
      return response.data;
    },
    
    create: async (data: Partial<ContractTemplate>) => {
      const response = await axios.post<ContractTemplate>(
        `${API_BASE}/templates/`,
        data
      );
      return response.data;
    },
    
    update: async (id: number, data: Partial<ContractTemplate>) => {
      const response = await axios.patch<ContractTemplate>(
        `${API_BASE}/templates/${id}/`,
        data
      );
      return response.data;
    },
  },
};
```



### 19.5 Custom Hooks

```typescript
// src/features/contracts/hooks/useContract.ts

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { contractsApi } from '../services/contractsApi';
import { toast } from 'sonner';

export const useContract = (id: number) => {
  return useQuery({
    queryKey: ['contract', id],
    queryFn: () => contractsApi.get(id),
    enabled: !!id,
  });
};

export const useContractList = (filters?: { status?: string }) => {
  return useQuery({
    queryKey: ['contracts', filters],
    queryFn: () => contractsApi.list(filters),
  });
};

export const useGenerateContract = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: contractsApi.generateFromApplication,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contracts'] });
      toast.success('Contrato generado exitosamente');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Error al generar contrato');
    },
  });
};

export const useSignContract = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, pin }: { id: number; pin: string }) =>
      contractsApi.sign(id, pin),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['contract', data.id] });
      toast.success('Contrato firmado exitosamente');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Error al firmar contrato');
    },
  });
};
```

### 19.6 Componentes Principales

#### ContractCard.tsx
```typescript
// src/features/contracts/components/ContractCard.tsx

import { Contract } from '../types';
import { ContractStatusBadge } from './ContractStatusBadge';
import { FileText, Calendar, DollarSign } from 'lucide-react';

interface ContractCardProps {
  contract: Contract;
  onClick?: () => void;
}

export const ContractCard: React.FC<ContractCardProps> = ({ contract, onClick }) => {
  return (
    <div
      className="border rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
      onClick={onClick}
    >
      <div className="flex justify-between items-start mb-3">
        <div>
          <h3 className="font-semibold text-lg">{contract.contract_number}</h3>
          <p className="text-sm text-gray-600">
            {contract.loan_application.client_name}
          </p>
        </div>
        <ContractStatusBadge status={contract.status} />
      </div>

      <div className="space-y-2 text-sm">
        <div className="flex items-center gap-2">
          <DollarSign className="w-4 h-4 text-gray-400" />
          <span>Monto: Bs. {contract.principal_amount}</span>
        </div>
        
        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-gray-400" />
          <span>Plazo: {contract.term_months} meses</span>
        </div>
        
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-gray-400" />
          <span>Cuota: Bs. {contract.monthly_payment}</span>
        </div>
      </div>

      <div className="mt-3 pt-3 border-t text-xs text-gray-500">
        Creado: {new Date(contract.created_at).toLocaleDateString()}
      </div>
    </div>
  );
};
```

#### ContractViewer.tsx
```typescript
// src/features/contracts/components/ContractViewer.tsx

import { useState } from 'react';
import { Contract } from '../types';
import { Button } from '@/shared/components/Button';
import { PDFViewer } from './PDFViewer';
import { ContractSignatureModal } from './ContractSignatureModal';
import { Download, FileSignature } from 'lucide-react';

interface ContractViewerProps {
  contract: Contract;
  canSign?: boolean;
}

export const ContractViewer: React.FC<ContractViewerProps> = ({
  contract,
  canSign = false,
}) => {
  const [showSignModal, setShowSignModal] = useState(false);

  const handleDownload = async () => {
    const { pdf_url } = await contractsApi.getPDF(contract.id);
    window.open(pdf_url, '_blank');
  };

  return (
    <div className="space-y-4">
      {/* PDF Viewer */}
      {contract.pdf_url && (
        <PDFViewer url={contract.pdf_url} />
      )}

      {/* Acciones */}
      <div className="flex gap-3">
        <Button
          variant="outline"
          onClick={handleDownload}
          icon={<Download />}
        >
          Descargar PDF
        </Button>

        {canSign && contract.status === 'PENDING_SIGNATURE' && (
          <Button
            variant="primary"
            onClick={() => setShowSignModal(true)}
            icon={<FileSignature />}
          >
            Firmar Contrato
          </Button>
        )}
      </div>

      {/* Modal de firma */}
      {showSignModal && (
        <ContractSignatureModal
          contract={contract}
          onClose={() => setShowSignModal(false)}
        />
      )}
    </div>
  );
};
```

#### AmortizationTable.tsx
```typescript
// src/features/contracts/components/AmortizationTable.tsx

import { useQuery } from '@tanstack/react-query';
import { contractsApi } from '../services/contractsApi';
import { CheckCircle, Circle } from 'lucide-react';

interface AmortizationTableProps {
  contractId: number;
}

export const AmortizationTable: React.FC<AmortizationTableProps> = ({
  contractId,
}) => {
  const { data: schedule, isLoading } = useQuery({
    queryKey: ['amortization', contractId],
    queryFn: () => contractsApi.getAmortizationSchedule(contractId),
  });

  if (isLoading) return <div>Cargando tabla de amortización...</div>;
  if (!schedule) return null;

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              #
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Fecha
            </th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
              Capital
            </th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
              Interés
            </th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
              Cuota
            </th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
              Saldo
            </th>
            <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
              Estado
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {schedule.map((item) => (
            <tr key={item.payment_number} className={item.is_paid ? 'bg-green-50' : ''}>
              <td className="px-4 py-3 text-sm">{item.payment_number}</td>
              <td className="px-4 py-3 text-sm">
                {new Date(item.due_date).toLocaleDateString()}
              </td>
              <td className="px-4 py-3 text-sm text-right">
                Bs. {item.principal_amount}
              </td>
              <td className="px-4 py-3 text-sm text-right">
                Bs. {item.interest_amount}
              </td>
              <td className="px-4 py-3 text-sm text-right font-semibold">
                Bs. {item.total_payment}
              </td>
              <td className="px-4 py-3 text-sm text-right">
                Bs. {item.remaining_balance}
              </td>
              <td className="px-4 py-3 text-center">
                {item.is_paid ? (
                  <CheckCircle className="w-5 h-5 text-green-600 mx-auto" />
                ) : (
                  <Circle className="w-5 h-5 text-gray-300 mx-auto" />
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
```



### 19.7 Páginas

#### ContractListPage.tsx
```typescript
// src/features/contracts/pages/ContractListPage.tsx

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useContractList } from '../hooks/useContract';
import { ContractCard } from '../components/ContractCard';
import { ContractStatus } from '../types';

export const ContractListPage = () => {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState<ContractStatus | ''>('');
  
  const { data, isLoading } = useContractList({
    status: statusFilter || undefined,
  });

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Contratos</h1>
        
        {/* Filtros */}
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as ContractStatus)}
          className="border rounded px-3 py-2"
        >
          <option value="">Todos los estados</option>
          <option value="DRAFT">Borrador</option>
          <option value="PENDING_SIGNATURE">Pendiente de Firma</option>
          <option value="ACTIVE">Activo</option>
          <option value="COMPLETED">Completado</option>
        </select>
      </div>

      {isLoading ? (
        <div>Cargando contratos...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {data?.results.map((contract) => (
            <ContractCard
              key={contract.id}
              contract={contract}
              onClick={() => navigate(`/contracts/${contract.id}`)}
            />
          ))}
        </div>
      )}
    </div>
  );
};
```

#### ContractDetailPage.tsx
```typescript
// src/features/contracts/pages/ContractDetailPage.tsx

import { useParams } from 'react-router-dom';
import { useContract } from '../hooks/useContract';
import { ContractViewer } from '../components/ContractViewer';
import { AmortizationTable } from '../components/AmortizationTable';
import { ContractTimeline } from '../components/ContractTimeline';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/shared/components/Tabs';

export const ContractDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const { data: contract, isLoading } = useContract(Number(id));

  if (isLoading) return <div>Cargando contrato...</div>;
  if (!contract) return <div>Contrato no encontrado</div>;

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold">{contract.contract_number}</h1>
        <p className="text-gray-600">{contract.loan_application.client_name}</p>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="contract">
        <TabsList>
          <TabsTrigger value="contract">Contrato</TabsTrigger>
          <TabsTrigger value="amortization">Tabla de Amortización</TabsTrigger>
          <TabsTrigger value="timeline">Historial</TabsTrigger>
        </TabsList>

        <TabsContent value="contract">
          <ContractViewer
            contract={contract}
            canSign={contract.status === 'PENDING_SIGNATURE'}
          />
        </TabsContent>

        <TabsContent value="amortization">
          <AmortizationTable contractId={contract.id} />
        </TabsContent>

        <TabsContent value="timeline">
          <ContractTimeline contractId={contract.id} />
        </TabsContent>
      </Tabs>
    </div>
  );
};
```

### 19.8 Rutas

```typescript
// src/App.tsx (agregar rutas)

import { ContractListPage } from './features/contracts/pages/ContractListPage';
import { ContractDetailPage } from './features/contracts/pages/ContractDetailPage';

// En el router:
<Route path="/contracts" element={<ContractListPage />} />
<Route path="/contracts/:id" element={<ContractDetailPage />} />
```

### 19.9 Integración con Módulo de Loans

```typescript
// src/features/loans/pages/LoanDetailPage.tsx

import { useGenerateContract } from '@/features/contracts/hooks/useContract';

export const LoanDetailPage = () => {
  const { mutate: generateContract, isPending } = useGenerateContract();
  
  const handleGenerateContract = () => {
    generateContract(loanApplication.id);
  };

  return (
    <div>
      {/* ... contenido existente ... */}
      
      {loanApplication.status === 'APPROVED' && !loanApplication.has_contract && (
        <Button
          onClick={handleGenerateContract}
          disabled={isPending}
        >
          Generar Contrato
        </Button>
      )}
      
      {loanApplication.has_contract && (
        <Button
          onClick={() => navigate(`/contracts/${loanApplication.contract_id}`)}
        >
          Ver Contrato
        </Button>
      )}
    </div>
  );
};
```

---

## 20. MOBILE (FLUTTER) - DETALLADO

### 20.1 Arquitectura del Mobile

El proyecto Flutter SI2 está organizado con **arquitectura por features** similar al backend y frontend:

```
lib/
├── core/              # Configuración, networking, auth
├── features/          # Módulos por funcionalidad
│   ├── auth/
│   ├── loans/
│   ├── products/
│   └── contracts/    # ← NUEVO MÓDULO
└── shared/           # Widgets compartidos
```

### 20.2 Estructura del Módulo Contracts (Flutter)

```
lib/features/contracts/
├── models/
│   ├── contract.dart
│   ├── contract_signature.dart
│   └── amortization_schedule_item.dart
├── providers/
│   └── contracts_provider.dart
├── screens/
│   ├── contract_list_screen.dart
│   ├── contract_detail_screen.dart
│   └── contract_signature_screen.dart
├── services/
│   └── contracts_service.dart
└── widgets/
    ├── contract_card.dart
    ├── contract_status_badge.dart
    ├── pdf_viewer_widget.dart
    ├── amortization_table.dart
    └── signature_pad.dart
```

### 20.3 Modelos

```dart
// lib/features/contracts/models/contract.dart

class Contract {
  final int id;
  final String contractNumber;
  final ContractStatus status;
  final LoanApplicationSummary loanApplication;
  
  // Términos financieros
  final double principalAmount;
  final double interestRate;
  final int termMonths;
  final double monthlyPayment;
  
  // Fechas
  final DateTime contractDate;
  final DateTime startDate;
  final DateTime endDate;
  final DateTime firstPaymentDate;
  
  // Documentos
  final String? pdfUrl;
  final DateTime? pdfExpiresAt;
  
  // Firmas
  final DateTime? borrowerSignedAt;
  final List<ContractSignature> signatures;
  
  // Metadata
  final DateTime createdAt;
  final DateTime updatedAt;

  Contract({
    required this.id,
    required this.contractNumber,
    required this.status,
    required this.loanApplication,
    required this.principalAmount,
    required this.interestRate,
    required this.termMonths,
    required this.monthlyPayment,
    required this.contractDate,
    required this.startDate,
    required this.endDate,
    required this.firstPaymentDate,
    this.pdfUrl,
    this.pdfExpiresAt,
    this.borrowerSignedAt,
    required this.signatures,
    required this.createdAt,
    required this.updatedAt,
  });

  factory Contract.fromJson(Map<String, dynamic> json) {
    return Contract(
      id: json['id'],
      contractNumber: json['contract_number'],
      status: ContractStatus.fromString(json['status']),
      loanApplication: LoanApplicationSummary.fromJson(json['loan_application']),
      principalAmount: double.parse(json['principal_amount']),
      interestRate: double.parse(json['interest_rate']),
      termMonths: json['term_months'],
      monthlyPayment: double.parse(json['monthly_payment']),
      contractDate: DateTime.parse(json['contract_date']),
      startDate: DateTime.parse(json['start_date']),
      endDate: DateTime.parse(json['end_date']),
      firstPaymentDate: DateTime.parse(json['first_payment_date']),
      pdfUrl: json['pdf_url'],
      pdfExpiresAt: json['pdf_expires_at'] != null 
          ? DateTime.parse(json['pdf_expires_at']) 
          : null,
      borrowerSignedAt: json['borrower_signed_at'] != null
          ? DateTime.parse(json['borrower_signed_at'])
          : null,
      signatures: (json['signatures'] as List)
          .map((s) => ContractSignature.fromJson(s))
          .toList(),
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
    );
  }
}

enum ContractStatus {
  draft,
  pendingSignature,
  partiallySigned,
  active,
  cancelled,
  completed,
  defaulted;

  static ContractStatus fromString(String status) {
    switch (status) {
      case 'DRAFT':
        return ContractStatus.draft;
      case 'PENDING_SIGNATURE':
        return ContractStatus.pendingSignature;
      case 'PARTIALLY_SIGNED':
        return ContractStatus.partiallySigned;
      case 'ACTIVE':
        return ContractStatus.active;
      case 'CANCELLED':
        return ContractStatus.cancelled;
      case 'COMPLETED':
        return ContractStatus.completed;
      case 'DEFAULTED':
        return ContractStatus.defaulted;
      default:
        return ContractStatus.draft;
    }
  }

  String get displayName {
    switch (this) {
      case ContractStatus.draft:
        return 'Borrador';
      case ContractStatus.pendingSignature:
        return 'Pendiente de Firma';
      case ContractStatus.partiallySigned:
        return 'Parcialmente Firmado';
      case ContractStatus.active:
        return 'Activo';
      case ContractStatus.cancelled:
        return 'Cancelado';
      case ContractStatus.completed:
        return 'Completado';
      case ContractStatus.defaulted:
        return 'En Mora';
    }
  }
}
```



### 20.4 Servicio API

```dart
// lib/features/contracts/services/contracts_service.dart

import 'package:dio/dio.dart';
import '../../../core/network/api_client.dart';
import '../models/contract.dart';
import '../models/amortization_schedule_item.dart';

class ContractsService {
  final ApiClient _apiClient;

  ContractsService(this._apiClient);

  // Listar contratos
  Future<List<Contract>> getContracts({String? status}) async {
    try {
      final response = await _apiClient.get(
        '/contracts/',
        queryParameters: status != null ? {'status': status} : null,
      );
      
      final results = response.data['results'] as List;
      return results.map((json) => Contract.fromJson(json)).toList();
    } catch (e) {
      throw Exception('Error al obtener contratos: $e');
    }
  }

  // Obtener detalle
  Future<Contract> getContract(int id) async {
    try {
      final response = await _apiClient.get('/contracts/$id/');
      return Contract.fromJson(response.data);
    } catch (e) {
      throw Exception('Error al obtener contrato: $e');
    }
  }

  // Generar contrato desde solicitud
  Future<Contract> generateFromApplication(int loanApplicationId) async {
    try {
      final response = await _apiClient.post(
        '/contracts/generate-from-application/',
        data: {'loan_application_id': loanApplicationId},
      );
      return Contract.fromJson(response.data);
    } catch (e) {
      throw Exception('Error al generar contrato: $e');
    }
  }

  // Firmar contrato
  Future<Contract> signContract(int id, String pin) async {
    try {
      final response = await _apiClient.post(
        '/contracts/$id/sign/',
        data: {'pin': pin},
      );
      return Contract.fromJson(response.data);
    } catch (e) {
      throw Exception('Error al firmar contrato: $e');
    }
  }

  // Obtener PDF
  Future<String> getContractPDF(int id) async {
    try {
      final response = await _apiClient.get('/contracts/$id/pdf/');
      return response.data['pdf_url'];
    } catch (e) {
      throw Exception('Error al obtener PDF: $e');
    }
  }

  // Obtener tabla de amortización
  Future<List<AmortizationScheduleItem>> getAmortizationSchedule(int id) async {
    try {
      final response = await _apiClient.get('/contracts/$id/amortization-schedule/');
      final items = response.data as List;
      return items.map((json) => AmortizationScheduleItem.fromJson(json)).toList();
    } catch (e) {
      throw Exception('Error al obtener tabla de amortización: $e');
    }
  }
}
```

### 20.5 Provider (State Management)

```dart
// lib/features/contracts/providers/contracts_provider.dart

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/contracts_service.dart';
import '../models/contract.dart';

// Provider del servicio
final contractsServiceProvider = Provider<ContractsService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return ContractsService(apiClient);
});

// Provider de lista de contratos
final contractsListProvider = FutureProvider.family<List<Contract>, String?>((ref, status) async {
  final service = ref.watch(contractsServiceProvider);
  return service.getContracts(status: status);
});

// Provider de detalle de contrato
final contractDetailProvider = FutureProvider.family<Contract, int>((ref, id) async {
  final service = ref.watch(contractsServiceProvider);
  return service.getContract(id);
});

// Provider de tabla de amortización
final amortizationScheduleProvider = FutureProvider.family<List<AmortizationScheduleItem>, int>((ref, contractId) async {
  final service = ref.watch(contractsServiceProvider);
  return service.getAmortizationSchedule(contractId);
});

// State notifier para acciones
class ContractsNotifier extends StateNotifier<AsyncValue<void>> {
  final ContractsService _service;

  ContractsNotifier(this._service) : super(const AsyncValue.data(null));

  Future<void> signContract(int id, String pin) async {
    state = const AsyncValue.loading();
    try {
      await _service.signContract(id, pin);
      state = const AsyncValue.data(null);
    } catch (e, stack) {
      state = AsyncValue.error(e, stack);
    }
  }
}

final contractsNotifierProvider = StateNotifierProvider<ContractsNotifier, AsyncValue<void>>((ref) {
  final service = ref.watch(contractsServiceProvider);
  return ContractsNotifier(service);
});
```

### 20.6 Widgets

#### ContractCard
```dart
// lib/features/contracts/widgets/contract_card.dart

import 'package:flutter/material.dart';
import '../models/contract.dart';
import 'contract_status_badge.dart';

class ContractCard extends StatelessWidget {
  final Contract contract;
  final VoidCallback? onTap;

  const ContractCard({
    Key? key,
    required this.contract,
    this.onTap,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          contract.contractNumber,
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                fontWeight: FontWeight.bold,
                              ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          contract.loanApplication.clientName,
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                color: Colors.grey[600],
                              ),
                        ),
                      ],
                    ),
                  ),
                  ContractStatusBadge(status: contract.status),
                ],
              ),
              
              const SizedBox(height: 16),
              
              // Detalles
              _buildDetailRow(
                context,
                icon: Icons.attach_money,
                label: 'Monto',
                value: 'Bs. ${contract.principalAmount.toStringAsFixed(2)}',
              ),
              const SizedBox(height: 8),
              _buildDetailRow(
                context,
                icon: Icons.calendar_today,
                label: 'Plazo',
                value: '${contract.termMonths} meses',
              ),
              const SizedBox(height: 8),
              _buildDetailRow(
                context,
                icon: Icons.payment,
                label: 'Cuota',
                value: 'Bs. ${contract.monthlyPayment.toStringAsFixed(2)}',
              ),
              
              const SizedBox(height: 12),
              const Divider(),
              const SizedBox(height: 8),
              
              // Footer
              Text(
                'Creado: ${_formatDate(contract.createdAt)}',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Colors.grey[500],
                    ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDetailRow(
    BuildContext context, {
    required IconData icon,
    required String label,
    required String value,
  }) {
    return Row(
      children: [
        Icon(icon, size: 16, color: Colors.grey[400]),
        const SizedBox(width: 8),
        Text(
          '$label: ',
          style: Theme.of(context).textTheme.bodySmall,
        ),
        Text(
          value,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                fontWeight: FontWeight.w600,
              ),
        ),
      ],
    );
  }

  String _formatDate(DateTime date) {
    return '${date.day}/${date.month}/${date.year}';
  }
}
```

#### PDFViewerWidget
```dart
// lib/features/contracts/widgets/pdf_viewer_widget.dart

import 'package:flutter/material.dart';
import 'package:flutter_pdfview/flutter_pdfview.dart';
import 'package:http/http.dart' as http;
import 'dart:io';
import 'package:path_provider/path_provider.dart';

class PDFViewerWidget extends StatefulWidget {
  final String pdfUrl;

  const PDFViewerWidget({
    Key? key,
    required this.pdfUrl,
  }) : super(key: key);

  @override
  State<PDFViewerWidget> createState() => _PDFViewerWidgetState();
}

class _PDFViewerWidgetState extends State<PDFViewerWidget> {
  String? localPath;
  bool isLoading = true;
  String? error;

  @override
  void initState() {
    super.initState();
    _downloadAndSavePDF();
  }

  Future<void> _downloadAndSavePDF() async {
    try {
      final response = await http.get(Uri.parse(widget.pdfUrl));
      final dir = await getApplicationDocumentsDirectory();
      final file = File('${dir.path}/contract_${DateTime.now().millisecondsSinceEpoch}.pdf');
      await file.writeAsBytes(response.bodyBytes);
      
      setState(() {
        localPath = file.path;
        isLoading = false;
      });
    } catch (e) {
      setState(() {
        error = 'Error al cargar PDF: $e';
        isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (error != null) {
      return Center(
        child: Text(error!, style: const TextStyle(color: Colors.red)),
      );
    }

    return PDFView(
      filePath: localPath!,
      enableSwipe: true,
      swipeHorizontal: false,
      autoSpacing: true,
      pageFling: true,
    );
  }
}
```et> {
  String? localPath;
  bool isLoading = true;
  String? error;

  @override
  void initState() {
    super.initState();
    _downloadPDF();
  }

  Future<void> _downloadPDF() async {
    try {
      final response = await http.get(Uri.parse(widget.pdfUrl));
      final dir = await getTemporaryDirectory();
      final file = File('${dir.path}/contract.pdf');
      await file.writeAsBytes(response.bodyBytes);
      
      setState(() {
        localPath = file.path;
        isLoading = false;
      });
    } catch (e) {
      setState(() {
        error = 'Error al cargar PDF: $e';
        isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (error != null) {
      return Center(child: Text(error!));
    }

    return PDFView(
      filePath: localPath!,
      enableSwipe: true,
      swipeHorizontal: false,
      autoSpacing: true,
      pageFling: true,
    );
  }
}
```



#### AmortizationTable
```dart
// lib/features/contracts/widgets/amortization_table.dart

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/amortization_schedule_item.dart';
import '../providers/contracts_provider.dart';

class AmortizationTable extends ConsumerWidget {
  final int contractId;

  const AmortizationTable({
    Key? key,
    required this.contractId,
  }) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final scheduleAsync = ref.watch(amortizationScheduleProvider(contractId));

    return scheduleAsync.when(
      data: (schedule) => SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: DataTable(
          columns: const [
            DataColumn(label: Text('#')),
            DataColumn(label: Text('Fecha')),
            DataColumn(label: Text('Capital')),
            DataColumn(label: Text('Interés')),
            DataColumn(label: Text('Cuota')),
            DataColumn(label: Text('Saldo')),
            DataColumn(label: Text('Estado')),
          ],
          rows: schedule.map((item) {
            return DataRow(
              color: MaterialStateProperty.resolveWith<Color?>(
                (states) => item.isPaid ? Colors.green.shade50 : null,
              ),
              cells: [
                DataCell(Text('${item.paymentNumber}')),
                DataCell(Text(_formatDate(item.dueDate))),
                DataCell(Text('Bs. ${item.principalAmount.toStringAsFixed(2)}')),
                DataCell(Text('Bs. ${item.interestAmount.toStringAsFixed(2)}')),
                DataCell(Text(
                  'Bs. ${item.totalPayment.toStringAsFixed(2)}',
                  style: const TextStyle(fontWeight: FontWeight.bold),
                )),
                DataCell(Text('Bs. ${item.remainingBalance.toStringAsFixed(2)}')),
                DataCell(
                  Icon(
                    item.isPaid ? Icons.check_circle : Icons.circle_outlined,
                    color: item.isPaid ? Colors.green : Colors.grey,
                  ),
                ),
              ],
            );
          }).toList(),
        ),
      ),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, stack) => Center(
        child: Text('Error: $error', style: const TextStyle(color: Colors.red)),
      ),
    );
  }

  String _formatDate(DateTime date) {
    return '${date.day}/${date.month}/${date.year}';
  }
}
```

#### ContractStatusBadge
```dart
// lib/features/contracts/widgets/contract_status_badge.dart

import 'package:flutter/material.dart';
import '../models/contract.dart';

class ContractStatusBadge extends StatelessWidget {
  final ContractStatus status;

  const ContractStatusBadge({
    Key? key,
    required this.status,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: _getColor(),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        status.displayName,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 12,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  Color _getColor() {
    switch (status) {
      case ContractStatus.draft:
        return Colors.grey;
      case ContractStatus.pendingSignature:
        return Colors.orange;
      case ContractStatus.partiallySigned:
        return Colors.blue;
      case ContractStatus.active:
        return Colors.green;
      case ContractStatus.cancelled:
        return Colors.red;
      case ContractStatus.completed:
        return Colors.teal;
      case ContractStatus.defaulted:
        return Colors.deepOrange;
    }
  }
}
```

#### SignaturePad
```dart
// lib/features/contracts/widgets/signature_pad.dart

import 'package:flutter/material.dart';
import 'package:signature/signature.dart';

class SignaturePad extends StatefulWidget {
  final Function(String) onSigned;

  const SignaturePad({
    Key? key,
    required this.onSigned,
  }) : super(key: key);

  @override
  State<SignaturePad> createState() => _SignaturePadState();
}

class _SignaturePadState extends State<SignaturePad> {
  late SignatureController _controller;

  @override
  void initState() {
    super.initState();
    _controller = SignatureController(
      penStrokeWidth: 3,
      penColor: Colors.black,
      exportBackgroundColor: Colors.white,
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          height: 200,
          decoration: BoxDecoration(
            border: Border.all(color: Colors.grey),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Signature(
            controller: _controller,
            backgroundColor: Colors.white,
          ),
        ),
        const SizedBox(height: 16),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: [
            ElevatedButton.icon(
              onPressed: () => _controller.clear(),
              icon: const Icon(Icons.clear),
              label: const Text('Limpiar'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.grey,
              ),
            ),
            ElevatedButton.icon(
              onPressed: _handleSign,
              icon: const Icon(Icons.check),
              label: const Text('Confirmar Firma'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.green,
              ),
            ),
          ],
        ),
      ],
    );
  }

  Future<void> _handleSign() async {
    if (_controller.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor, firme antes de continuar')),
      );
      return;
    }

    final signature = await _controller.toPngBytes();
    if (signature != null) {
      // Convertir a base64 o guardar según necesidad
      widget.onSigned(signature.toString());
    }
  }
}
```

### 20.7 Screens

#### ContractListScreen
```dart
// lib/features/contracts/screens/contract_list_screen.dart

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/contracts_provider.dart';
import '../widgets/contract_card.dart';
import '../models/contract.dart';
import 'contract_detail_screen.dart';

class ContractListScreen extends ConsumerStatefulWidget {
  const ContractListScreen({Key? key}) : super(key: key);

  @override
  ConsumerState<ContractListScreen> createState() => _ContractListScreenState();
}

class _ContractListScreenState extends ConsumerState<ContractListScreen> {
  String? _selectedStatus;

  @override
  Widget build(BuildContext context) {
    final contractsAsync = ref.watch(contractsListProvider(_selectedStatus));

    return Scaffold(
      appBar: AppBar(
        title: const Text('Contratos'),
        actions: [
          PopupMenuButton<String>(
            icon: const Icon(Icons.filter_list),
            onSelected: (value) {
              setState(() {
                _selectedStatus = value == 'all' ? null : value;
              });
            },
            itemBuilder: (context) => [
              const PopupMenuItem(value: 'all', child: Text('Todos')),
              const PopupMenuItem(value: 'DRAFT', child: Text('Borrador')),
              const PopupMenuItem(value: 'PENDING_SIGNATURE', child: Text('Pendiente de Firma')),
              const PopupMenuItem(value: 'ACTIVE', child: Text('Activo')),
              const PopupMenuItem(value: 'COMPLETED', child: Text('Completado')),
            ],
          ),
        ],
      ),
      body: contractsAsync.when(
        data: (contracts) {
          if (contracts.isEmpty) {
            return const Center(
              child: Text('No hay contratos disponibles'),
            );
          }

          return RefreshIndicator(
            onRefresh: () async {
              ref.invalidate(contractsListProvider(_selectedStatus));
            },
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: contracts.length,
              itemBuilder: (context, index) {
                final contract = contracts[index];
                return Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: ContractCard(
                    contract: contract,
                    onTap: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (context) => ContractDetailScreen(
                            contractId: contract.id,
                          ),
                        ),
                      );
                    },
                  ),
                );
              },
            ),
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline, size: 48, color: Colors.red),
              const SizedBox(height: 16),
              Text('Error: $error'),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () {
                  ref.invalidate(contractsListProvider(_selectedStatus));
                },
                child: const Text('Reintentar'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```


#### ContractDetailScreen
```dart
// lib/features/contracts/screens/contract_detail_screen.dart

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/contracts_provider.dart';
import '../widgets/pdf_viewer_widget.dart';
import '../widgets/amortization_table.dart';
import '../widgets/contract_status_badge.dart';
import '../models/contract.dart';
import 'contract_signature_screen.dart';

class ContractDetailScreen extends ConsumerWidget {
  final int contractId;

  const ContractDetailScreen({
    Key? key,
    required this.contractId,
  }) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final contractAsync = ref.watch(contractDetailProvider(contractId));

    return Scaffold(
      appBar: AppBar(
        title: const Text('Detalle del Contrato'),
      ),
      body: contractAsync.when(
        data: (contract) => _buildContent(context, ref, contract),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => Center(
          child: Text('Error: $error', style: const TextStyle(color: Colors.red)),
        ),
      ),
    );
  }

  Widget _buildContent(BuildContext context, WidgetRef ref, Contract contract) {
    return DefaultTabController(
      length: 3,
      child: Column(
        children: [
          // Header
          Container(
            padding: const EdgeInsets.all(16),
            color: Colors.grey[100],
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            contract.contractNumber,
                            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                  fontWeight: FontWeight.bold,
                                ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            contract.loanApplication.clientName,
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                        ],
                      ),
                    ),
                    ContractStatusBadge(status: contract.status),
                  ],
                ),
                const SizedBox(height: 16),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: [
                    _buildInfoChip(
                      context,
                      icon: Icons.attach_money,
                      label: 'Monto',
                      value: 'Bs. ${contract.principalAmount.toStringAsFixed(2)}',
                    ),
                    _buildInfoChip(
                      context,
                      icon: Icons.calendar_today,
                      label: 'Plazo',
                      value: '${contract.termMonths} meses',
                    ),
                    _buildInfoChip(
                      context,
                      icon: Icons.payment,
                      label: 'Cuota',
                      value: 'Bs. ${contract.monthlyPayment.toStringAsFixed(2)}',
                    ),
                  ],
                ),
              ],
            ),
          ),

          // Tabs
          const TabBar(
            tabs: [
              Tab(text: 'Contrato', icon: Icon(Icons.description)),
              Tab(text: 'Amortización', icon: Icon(Icons.table_chart)),
              Tab(text: 'Firmas', icon: Icon(Icons.edit)),
            ],
          ),

          // Tab Views
          Expanded(
            child: TabBarView(
              children: [
                // Tab 1: Contrato PDF
                _buildContractTab(context, contract),
                
                // Tab 2: Tabla de Amortización
                Padding(
                  padding: const EdgeInsets.all(16),
                  child: AmortizationTable(contractId: contract.id),
                ),
                
                // Tab 3: Firmas
                _buildSignaturesTab(context, contract),
              ],
            ),
          ),

          // Botones de acción
          if (contract.status == ContractStatus.pendingSignature)
            _buildActionButtons(context, contract),
        ],
      ),
    );
  }

  Widget _buildInfoChip(
    BuildContext context, {
    required IconData icon,
    required String label,
    required String value,
  }) {
    return Column(
      children: [
        Icon(icon, size: 20, color: Theme.of(context).primaryColor),
        const SizedBox(height: 4),
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Colors.grey[600],
              ),
        ),
        Text(
          value,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
      ],
    );
  }

  Widget _buildContractTab(BuildContext context, Contract contract) {
    if (contract.pdfUrl == null) {
      return const Center(
        child: Text('PDF no disponible'),
      );
    }

    return Column(
      children: [
        Expanded(
          child: PDFViewerWidget(pdfUrl: contract.pdfUrl!),
        ),
        Padding(
          padding: const EdgeInsets.all(16),
          child: ElevatedButton.icon(
            onPressed: () {
              // Implementar descarga
            },
            icon: const Icon(Icons.download),
            label: const Text('Descargar PDF'),
            style: ElevatedButton.styleFrom(
              minimumSize: const Size(double.infinity, 48),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildSignaturesTab(BuildContext context, Contract contract) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (contract.signatures.isEmpty)
          const Center(
            child: Padding(
              padding: EdgeInsets.all(32),
              child: Text('No hay firmas registradas'),
            ),
          )
        else
          ...contract.signatures.map((signature) {
            return Card(
              child: ListTile(
                leading: const Icon(Icons.check_circle, color: Colors.green),
                title: Text(signature.signerName),
                subtitle: Text(
                  'Firmado: ${_formatDateTime(signature.signedAt)}',
                ),
                trailing: Chip(
                  label: Text(signature.signerType),
                  backgroundColor: Colors.blue.shade100,
                ),
              ),
            );
          }).toList(),
      ],
    );
  }

  Widget _buildActionButtons(BuildContext context, Contract contract) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.grey.withOpacity(0.2),
            spreadRadius: 1,
            blurRadius: 5,
            offset: const Offset(0, -3),
          ),
        ],
      ),
      child: ElevatedButton.icon(
        onPressed: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => ContractSignatureScreen(
                contractId: contract.id,
              ),
            ),
          );
        },
        icon: const Icon(Icons.edit),
        label: const Text('Firmar Contrato'),
        style: ElevatedButton.styleFrom(
          backgroundColor: Colors.green,
          minimumSize: const Size(double.infinity, 48),
        ),
      ),
    );
  }

  String _formatDateTime(DateTime dateTime) {
    return '${dateTime.day}/${dateTime.month}/${dateTime.year} ${dateTime.hour}:${dateTime.minute}';
  }
}
```

#### ContractSignatureScreen
```dart
// lib/features/contracts/screens/contract_signature_screen.dart

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/contracts_provider.dart';
import '../widgets/signature_pad.dart';

class ContractSignatureScreen extends ConsumerStatefulWidget {
  final int contractId;

  const ContractSignatureScreen({
    Key? key,
    required this.contractId,
  }) : super(key: key);

  @override
  ConsumerState<ContractSignatureScreen> createState() => _ContractSignatureScreenState();
}

class _ContractSignatureScreenState extends ConsumerState<ContractSignatureScreen> {
  final _pinController = TextEditingController();
  bool _termsAccepted = false;
  bool _isProcessing = false;

  @override
  void dispose() {
    _pinController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Firmar Contrato'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Instrucciones
            Card(
              color: Colors.blue.shade50,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.info_outline, color: Colors.blue.shade700),
                        const SizedBox(width: 8),
                        Text(
                          'Instrucciones',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: Colors.blue.shade700,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      '1. Lea cuidadosamente los términos y condiciones\n'
                      '2. Firme en el recuadro de abajo\n'
                      '3. Ingrese su PIN de seguridad\n'
                      '4. Confirme la firma',
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 24),

            // Términos y condiciones
            Text(
              'Términos y Condiciones',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 8),
            Container(
              height: 150,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                border: Border.all(color: Colors.grey),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const SingleChildScrollView(
                child: Text(
                  'Al firmar este contrato, usted acepta los términos y condiciones '
                  'establecidos en el documento. Este contrato es legalmente vinculante '
                  'y establece sus obligaciones de pago según el plan de amortización '
                  'acordado...\n\n'
                  '[Aquí irían los términos completos]',
                ),
              ),
            ),

            const SizedBox(height: 16),

            // Checkbox de aceptación
            CheckboxListTile(
              value: _termsAccepted,
              onChanged: (value) {
                setState(() {
                  _termsAccepted = value ?? false,
                });
              },
              title: const Text('He leído y acepto los términos y condiciones'),
              controlAffinity: ListTileControlAffinity.leading,
            ),

            const SizedBox(height: 24),

            // Firma
            Text(
              'Firma Digital',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 8),
            SignaturePad(
              onSigned: (signature) {
                // Guardar firma
              },
            ),

            const SizedBox(height: 24),

            // PIN
            Text(
              'PIN de Seguridad',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _pinController,
              obscureText: true,
              keyboardType: TextInputType.number,
              maxLength: 4,
              decoration: const InputDecoration(
                hintText: 'Ingrese su PIN de 4 dígitos',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.lock),
              ),
            ),

            const SizedBox(height: 24),

            // Botón de confirmar
            ElevatedButton(
              onPressed: _termsAccepted && !_isProcessing ? _handleSign : null,
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.green,
                minimumSize: const Size(double.infinity, 48),
              ),
              child: _isProcessing
                  ? const CircularProgressIndicator(color: Colors.white)
                  : const Text('Confirmar Firma'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _handleSign() async {
    if (_pinController.text.length != 4) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('El PIN debe tener 4 dígitos')),
      );
      return;
    }

    setState(() {
      _isProcessing = true;
    });

    try {
      final notifier = ref.read(contractsNotifierProvider.notifier);
      await notifier.signContract(widget.contractId, _pinController.text);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Contrato firmado exitosamente'),
            backgroundColor: Colors.green,
          ),
        );
        Navigator.pop(context);
        ref.invalidate(contractDetailProvider(widget.contractId));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error al firmar: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isProcessing = false;
        });
      }
    }
  }
}
```

### 20.8 Rutas y Navegación

```dart
// lib/core/routes/app_routes.dart

import 'package:flutter/material.dart';
import '../../features/contracts/screens/contract_list_screen.dart';
import '../../features/contracts/screens/contract_detail_screen.dart';
import '../../features/contracts/screens/contract_signature_screen.dart';

class AppRoutes {
  static const String contractList = '/contracts';
  static const String contractDetail = '/contracts/:id';
  static const String contractSignature = '/contracts/:id/sign';

  static Route<dynamic> generateRoute(RouteSettings settings) {
    switch (settings.name) {
      case contractList:
        return MaterialPageRoute(
          builder: (_) => const ContractListScreen(),
        );
      
      case contractDetail:
        final contractId = settings.arguments as int;
        return MaterialPageRoute(
          builder: (_) => ContractDetailScreen(contractId: contractId),
        );
      
      case contractSignature:
        final contractId = settings.arguments as int;
        return MaterialPageRoute(
          builder: (_) => ContractSignatureScreen(contractId: contractId),
        );
      
      default:
        return MaterialPageRoute(
          builder: (_) => Scaffold(
            body: Center(
              child: Text('Ruta no encontrada: ${settings.name}'),
            ),
          ),
        );
    }
  }
}
```

### 20.9 Integración con Módulo de Loans

```dart
// lib/features/loans/screens/loan_detail_screen.dart

import 'package:flutter/material.dart';
import '../../contracts/services/contracts_service.dart';

class LoanDetailScreen extends StatelessWidget {
  final LoanApplication loanApplication;

  const LoanDetailScreen({
    Key? key,
    required this.loanApplication,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Detalle de Solicitud')),
      body: Column(
        children: [
          // ... contenido existente ...

          // Botón para generar contrato
          if (loanApplication.status == 'APPROVED' && !loanApplication.hasContract)
            Padding(
              padding: const EdgeInsets.all(16),
              child: ElevatedButton.icon(
                onPressed: () => _generateContract(context),
                icon: const Icon(Icons.description),
                label: const Text('Generar Contrato'),
                style: ElevatedButton.styleFrom(
                  minimumSize: const Size(double.infinity, 48),
                ),
              ),
            ),

          // Botón para ver contrato
          if (loanApplication.hasContract)
            Padding(
              padding: const EdgeInsets.all(16),
              child: ElevatedButton.icon(
                onPressed: () {
                  Navigator.pushNamed(
                    context,
                    AppRoutes.contractDetail,
                    arguments: loanApplication.contractId,
                  );
                },
                icon: const Icon(Icons.visibility),
                label: const Text('Ver Contrato'),
                style: ElevatedButton.styleFrom(
                  minimumSize: const Size(double.infinity, 48),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Future<void> _generateContract(BuildContext context) async {
    try {
      final service = ContractsService(ApiClient());
      await service.generateFromApplication(loanApplication.id);
      
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Contrato generado exitosamente'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }
}
```

### 20.10 Dependencias Necesarias (pubspec.yaml)

```yaml
dependencies:
  flutter:
    sdk: flutter
  
  # State Management
  flutter_riverpod: ^2.4.0
  
  # Networking
  dio: ^5.3.3
  
  # PDF Viewer
  flutter_pdfview: ^1.3.2
  
  # File handling
  path_provider: ^2.1.1
  http: ^1.1.0
  
  # Signature
  signature: ^5.4.0
  
  # UI Components
  intl: ^0.18.1
```

---

## 21. DEPENDENCIAS ESPECÍFICAS POR PLATAFORMA

### 21.1 Frontend (React)

```json
{
  "dependencies": {
    "@tanstack/react-query": "^5.0.0",
    "axios": "^1.6.0",
    "react-pdf": "^7.5.0",
    "@react-pdf/renderer": "^3.1.0",
    "lucide-react": "^0.292.0",
    "sonner": "^1.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-pdf": "^7.0.0"
  }
}
```

### 21.2 Mobile (Flutter)

Ya incluidas en la sección 20.10

### 21.3 Backend (Python)

Ya incluidas en la sección 6.1

---

## 22. ACTUALIZACIÓN DE ESTIMACIONES DETALLADAS

### 22.1 Backend (Django) - DETALLADO

| Tarea | Subtareas | Estimación |
|-------|-----------|------------|
| **Modelos y migraciones** | | **2 días** |
| - Contract model | Definir campos, relaciones, métodos | 0.5 días |
| - ContractTemplate model | Plantillas con variables | 0.5 días |
| - ContractSignature model | Registro de firmas | 0.5 días |
| - ContractAmortizationSchedule | Tabla de amortización | 0.5 días |
| **Serializers y ViewSets** | | **2 días** |
| - ContractSerializer | Serialización completa | 0.5 días |
| - ContractTemplateSerializer | Con preview | 0.5 días |
| - ViewSets y permisos | CRUD + acciones custom | 1 día |
| **Servicio de generación** | | **3 días** |
| - Lógica de generación | Desde LoanApplication | 1 día |
| - Reemplazo de variables | Motor de plantillas | 1 día |
| - Validaciones | Reglas de negocio | 1 día |
| **Servicio de PDFs** | | **3 días** |
| - Configuración WeasyPrint | Setup y templates | 1 día |
| - Generación de PDFs | HTML a PDF | 1 día |
| - Integración con Storage | Supabase upload | 1 día |
| **Servicio de firmas** | | **2 días** |
| - Lógica de firma | Validación, registro | 1 día |
| - Verificación de identidad | Integración con CU-13 | 1 día |
| **Servicio de amortización** | | **2 días** |
| - Cálculo de cuotas | Algoritmo francés | 1 día |
| - Generación de tabla | Persistencia | 1 día |
| **Integración con módulos** | | **2 días** |
| - Loans integration | Hooks y validaciones | 1 día |
| - Garantías, storage, audit | Integraciones | 1 día |
| **Tests unitarios** | | **3 días** |
| - Tests de modelos | Validaciones | 1 día |
| - Tests de servicios | Lógica de negocio | 1 día |
| - Tests de serializers | Transformaciones | 1 día |
| **Tests de integración** | | **2 días** |
| - Tests de API | Endpoints completos | 1 día |
| - Tests de flujo completo | End-to-end | 1 día |
| **TOTAL BACKEND** | | **21 días** |

### 22.2 Frontend Web (React) - DETALLADO

| Tarea | Subtareas | Estimación |
|-------|-----------|------------|
| **Tipos TypeScript** | | **0.5 días** |
| - Definir interfaces | Contract, Template, etc. | 0.5 días |
| **Servicio API** | | **1 día** |
| - contractsApi.ts | Todos los endpoints | 1 día |
| **Custom Hooks** | | **1 día** |
| - useContract, useContractList | React Query hooks | 0.5 días |
| - useGenerateContract, useSignContract | Mutation hooks | 0.5 días |
| **Componentes base** | | **2 días** |
| - ContractCard | Card component | 0.5 días |
| - ContractStatusBadge | Badge component | 0.25 días |
| - PDFViewer | Visor de PDF | 0.75 días |
| - AmortizationTable | Tabla completa | 0.5 días |
| **Componentes avanzados** | | **2 días** |
| - ContractViewer | Visor completo | 1 día |
| - ContractSignatureModal | Modal de firma | 0.5 días |
| - ContractTimeline | Timeline de eventos | 0.5 días |
| **Páginas** | | **2 días** |
| - ContractListPage | Lista con filtros | 1 día |
| - ContractDetailPage | Detalle con tabs | 1 día |
| **Integración con Loans** | | **1 día** |
| - Botones en LoanDetailPage | Generar/Ver contrato | 0.5 días |
| - Rutas y navegación | Router setup | 0.5 días |
| **Tests** | | **2 días** |
| - Tests de componentes | Unit tests | 1 día |
| - Tests de integración | E2E tests | 1 día |
| **Styling y UX** | | **0.5 días** |
| - Responsive design | Mobile/tablet | 0.5 días |
| **TOTAL FRONTEND** | | **12 días** |

### 22.3 Mobile (Flutter) - DETALLADO

| Tarea | Subtareas | Estimación |
|-------|-----------|------------|
| **Modelos Dart** | | **1 día** |
| - Contract model | Con fromJson/toJson | 0.5 días |
| - Otros modelos | Signature, Schedule | 0.5 días |
| **Servicio API** | | **1 día** |
| - ContractsService | Todos los endpoints | 1 día |
| **Providers (Riverpod)** | | **1 día** |
| - contractsProvider | State management | 0.5 días |
| - contractsNotifier | Actions | 0.5 días |
| **Widgets** | | **2 días** |
| - ContractCard | Card widget | 0.5 días |
| - PDFViewerWidget | PDF viewer | 0.75 días |
| - AmortizationTable | Tabla | 0.5 días |
| - SignaturePad | Firma digital | 0.25 días |
| **Screens** | | **2 días** |
| - ContractListScreen | Lista con filtros | 0.75 días |
| - ContractDetailScreen | Detalle con tabs | 0.75 días |
| - ContractSignatureScreen | Pantalla de firma | 0.5 días |
| **Integración con Loans** | | **0.5 días** |
| - Botones en LoanDetailScreen | Generar/Ver | 0.5 días |
| **Rutas y navegación** | | **0.5 días** |
| - AppRoutes | Router setup | 0.5 días |
| **Tests** | | **1 día** |
| - Widget tests | Unit tests | 0.5 días |
| - Integration tests | E2E tests | 0.5 días |
| **TOTAL MOBILE** | | **9 días** |

### 22.4 Total General Actualizado

| Plataforma | Estimación Original | Estimación Detallada | Diferencia |
|------------|---------------------|----------------------|------------|
| Backend | 21 días | 21 días | 0 días |
| Frontend | 12 días | 12 días | 0 días |
| Mobile | 7 días | 9 días | +2 días |
| **TOTAL** | **40 días** | **42 días** | **+2 días** |

**Nota**: La estimación de mobile aumentó ligeramente al detallar todas las pantallas y widgets necesarios.

---

## 23. CONCLUSIÓN FINAL

### 23.1 Resumen del Análisis Completo

Este documento ahora incluye:

✅ **Backend (Django)**: Análisis completo con modelos, servicios, endpoints, integraciones
✅ **Frontend (React + TypeScript)**: Estructura modular completa con tipos, servicios, hooks, componentes y páginas
✅ **Mobile (Flutter)**: Arquitectura completa con modelos, servicios, providers, widgets y screens
✅ **Dependencias**: Listado completo de librerías necesarias para cada plataforma
✅ **Estimaciones detalladas**: Desglose por subtareas para cada plataforma
✅ **Integraciones**: Puntos de integración con módulos existentes (loans, garantías, storage, audit)

### 23.2 Arquitectura Consistente

Las tres plataformas siguen la **misma arquitectura modular**:

```
Backend:  api/contracts/
Frontend: src/features/contracts/
Mobile:   lib/features/contracts/
```

Esto facilita:
- Desarrollo paralelo por equipos especializados
- Mantenimiento independiente
- Escalabilidad futura
- Reutilización de patrones

### 23.3 Listo para Implementación

Con este análisis detallado, un equipo de desarrollo puede:

1. **Backend Developer**: Implementar el módulo completo siguiendo la estructura propuesta
2. **Frontend Developer**: Crear todos los componentes y páginas con los tipos definidos
3. **Mobile Developer**: Desarrollar todas las pantallas y widgets con los modelos especificados
4. **QA Engineer**: Crear plan de pruebas basado en los casos de uso y flujos descritos

### 23.4 Próximos Pasos Recomendados

1. **Validación con stakeholders** (1 día)
2. **Setup de entornos de desarrollo** (1 día)
3. **Implementación Fase 1 (MVP)** (3 semanas)
4. **Testing y QA** (1 semana)
5. **Deploy a staging** (2 días)
6. **Validación con usuarios** (1 semana)
7. **Deploy a producción** (1 día)

**Total estimado: 6-7 semanas** para tener el MVP en producción.

---

**Fin del Análisis Completo**

**Versión**: 2.0 (Completo con Frontend y Mobile)  
**Fecha**: 30 de Mayo, 2026  
**Estado**: ✅ Listo para Implementación
