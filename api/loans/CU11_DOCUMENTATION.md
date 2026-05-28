# CU-11: Gestionar Originación de Créditos - Documentación Técnica

## Resumen Ejecutivo

CU-11 implementa el flujo completo de originación de créditos para un sistema SaaS multi-tenant de gestión de créditos financieros. El caso de uso permite que prestatarios creen solicitudes de crédito desde web y móvil, y que el personal autorizado las revise, apruebe o rechace.

**Estado**: ✅ **IMPLEMENTADO**
**Componentes**: Backend (Django), Frontend (React/TypeScript), Móvil (Flutter)

---

## 1. ARQUITECTURA Y DISEÑO

### 1.1 Entidades Principales

#### LoanApplication (Modelo Principal)
Representa una solicitud de crédito con:
- **Estados**: DRAFT, SUBMITTED, IN_REVIEW, OBSERVED, APPROVED, REJECTED, DISBURSED, CANCELLED
- **Datos Económicos**: Monto, plazo, ingreso mensual, tipo de empleo
- **Auditoría**: Creado por, actualizado por, fechas de cambios de estado
- **Relaciones**: Cliente, Producto Crediticio, Sucursal, Usuario Asignado

#### LoanApplicationStatusHistory (Timeline)
Registra cada cambio de estado con:
- Estado anterior y nuevo
- Actor que hizo el cambio
- Descripción visible/invisible para prestatario
- Metadata adicional

#### LoanApplicationComment (Notas)
Comentarios internos o públicos:
- Solo staff puede crear comentarios internos
- Prestatario solo ve comentarios públicos
- Auditoría completa de quién y cuándo

### 1.2 Flujos de Estado

```
DRAFT
  ├─> SUBMITTED  (Prestatario envía)
  └─> CANCELLED  (Usuario cancela)

SUBMITTED
  ├─> IN_REVIEW  (Staff inicia revisión)
  ├─> OBSERVED   (Staff observa)
  ├─> REJECTED   (Staff rechaza)
  └─> CANCELLED  (Cancelación)

IN_REVIEW
  ├─> OBSERVED   (Se encuentran observaciones)
  ├─> APPROVED   (Se aprueba)
  ├─> REJECTED   (Se rechaza)
  └─> SUBMITTED  (Regresa a envío)

OBSERVED
  ├─> SUBMITTED  (Se corrigen observaciones)
  ├─> IN_REVIEW  (Se vuelve a revisar)
  ├─> REJECTED   (Se rechaza)
  └─> CANCELLED  (Cancelación)

APPROVED
  ├─> DISBURSED  (Desembolso)
  └─> CANCELLED  (Cancelación si no se desembolsó)

REJECTED → (Terminal, no hay transiciones)
DISBURSED → (Terminal, no hay transiciones)
CANCELLED → (Terminal, no hay transiciones)
```

### 1.3 Integración con CU-13 (Verificación de Identidad)

- Antes de SUBMITTED, valida que la identidad esté APPROVED
- Si no está verificada, retorna error 400 con mensaje específico
- Guarda estado de identidad en la solicitud para auditoría
- Permite que prestatario complete verificación antes de enviar

---

## 2. ENDPOINTS REST API

### Base: `/api/loans/credit-applications/`

#### 2.1 Listar Solicitudes
```
GET /api/loans/credit-applications/
```
**Permisos**: Prestatario ve solo sus solicitudes, Staff ve del tenant/sucursal

**Parámetros**:
- `status`: Filtrar por estado (DRAFT, SUBMITTED, etc.)
- `branch_id`: Filtrar por sucursal
- `product_id`: Filtrar por producto
- `identity_verification_status`: Filtrar por estado de identidad
- `ordering`: -created_at (default)
- `search`: Buscar por número de solicitud o email

**Respuesta**:
```json
{
  "count": 10,
  "next": "...",
  "results": [
    {
      "id": 1,
      "application_number": "LOAN-1-2026-0001-1234",
      "client_name": "Juan Pérez",
      "product_name": "Crédito Personal",
      "requested_amount": "5000.00",
      "term_months": 24,
      "status": "SUBMITTED",
      "status_display": "Enviada",
      "submitted_at": "2026-05-03T14:30:00Z",
      "identity_verification_status": "APPROVED",
      "created_at": "2026-05-03T10:00:00Z"
    }
  ]
}
```

#### 2.2 Crear Solicitud (Borrador)
```
POST /api/loans/credit-applications/
```
**Body**:
```json
{
  "product_id": 1,
  "requested_amount": "5000.00",
  "term_months": 24,
  "purpose": "Compra de electrodomésticos",
  "monthly_income": "2000.00",
  "employment_type": "EMPLOYED",
  "employment_description": "Contador en empresa XYZ",
  "branch_id": 1,
  "additional_data": {}
}
```

**Respuesta** (201 Created):
```json
{
  "id": 1,
  "application_number": "LOAN-1-2026-0001-1234",
  "status": "DRAFT",
  "requested_amount": "5000.00",
  "term_months": 24,
  "created_at": "2026-05-03T10:00:00Z"
}
```

#### 2.3 Ver Detalle
```
GET /api/loans/credit-applications/{id}/
```

**Respuesta incluye**:
- Datos completos de la solicitud
- Timeline (eventos visibles según rol)
- Comentarios (filtrados según rol)
- Documentos
- Estado de identidad

#### 2.4 Actualizar Borrador
```
PATCH /api/loans/credit-applications/{id}/
```

**Solo permitido** si status == DRAFT y es el propietario

#### 2.5 Enviar Solicitud
```
POST /api/loans/credit-applications/{id}/submit/
```

**Validaciones**:
- Todos los campos requeridos completos
- Producto activo
- Monto dentro del rango del producto
- Plazo dentro del rango del producto
- Identidad verificada (si aplica)

**Respuesta exitosa**:
```json
{
  "id": 1,
  "status": "SUBMITTED",
  "message": "Solicitud enviada correctamente"
}
```

**Error si identidad no verificada**:
```json
{
  "error": "Debe completar la verificación de identidad antes de enviar la solicitud",
  "requires_identity_verification": true,
  "identity_verification_url": "/api/identity-verification/start/"
}
```

#### 2.6 Cambiar Estado (Staff)
```
POST /api/loans/credit-applications/{id}/change-status/
```

**Body**:
```json
{
  "new_status": "IN_REVIEW",
  "reason": "Motivo opcional",
  "approved_amount": "4500.00",
  "approved_term_months": 24,
  "approved_interest_rate": "12.50"
}
```

**Transiciones válidas**: Según matriz de estados

#### 2.7 Ver Timeline
```
GET /api/loans/credit-applications/{id}/timeline/
```

**Respuesta**:
```json
[
  {
    "id": 1,
    "previous_status": "DRAFT",
    "new_status": "SUBMITTED",
    "title": "Solicitud enviada",
    "description": "El prestatario envió la solicitud para evaluación",
    "actor_name": "Juan Pérez",
    "actor_role": "BORROWER",
    "is_visible_to_borrower": true,
    "created_at": "2026-05-03T10:00:00Z"
  }
]
```

#### 2.8 Comentarios
```
GET /api/loans/credit-applications/{id}/comments/
POST /api/loans/credit-applications/{id}/comments/
```

**POST Body**:
```json
{
  "comment": "Texto del comentario",
  "is_internal": true
}
```

---

## 3. REGLAS DE NEGOCIO

### 3.1 Validaciones de Cantidad
- Monto > 0
- Monto >= Min del producto
- Monto <= Max del producto

### 3.2 Validaciones de Plazo
- Plazo > 0
- Plazo >= Min del producto
- Plazo <= Max del producto
- Plazo <= 360 meses

### 3.3 Validaciones de Identidad (CU-13)
- Si identity_verification_status != APPROVED → no permitir submit
- Guardar referencia a IdentityVerification en solicitud
- Permitir reintentar si fue DECLINED

### 3.4 Multi-Tenancy
- No confiar en tenant_id del cliente
- Extraer institution del usuario autenticado
- Validar que cliente pertenece a la institución
- Filtrar solicitudes por institution automáticamente

### 3.5 Restricción de Sucursal
- Si empleado está asignado a sucursal → solo ver solicitudes de esa sucursal
- Managers/Admins pueden ver todas las sucursales del tenant
- Prestatario no tiene restricción de sucursal

---

## 4. PERMISOS Y ROLES

### Permisos Requeridos

```
BORROWER_CAN_CREATE_OWN_APPLICATION
- Crear solicitud
- Editar borrador
- Enviar solicitud
- Ver propia solicitud

STAFF_CAN_VIEW_TENANT_APPLICATIONS
- Listar solicitudes del tenant
- Ver detalles

STAFF_CAN_CHANGE_APPLICATION_STATUS
- Cambiar estado
- Agregar observaciones
- Asignar aplicación

ADMIN_CAN_VIEW_ALL_TENANT_APPLICATIONS
- Listar todas sin restricción
- Ver detalles
- Exportar

BRANCH_RESTRICTION_PERMISSION
- Automática si está asignado a sucursal
```

### Matriz de Permisos

| Acción | Prestatario | Staff | Admin | Manager |
|--------|:-----------:|:-----:|:----:|:-------:|
| Crear | ✅ | ✅ | ✅ | ✅ |
| Ver Propias | ✅ | - | - | - |
| Listar Tenant | - | ✅ | ✅ | ✅ |
| Ver Detalles | ✅* | ✅* | ✅ | ✅ |
| Cambiar Estado | - | ✅** | ✅ | ✅ |
| Agregar Comentarios | ✅*** | ✅ | ✅ | ✅ |

\*Solo de propia sucursal si aplica
\*\*Según rol y transición
\*\*\*Solo comentarios públicos

---

## 5. AUDITORÍA Y TIMELINE

### Eventos Registrados

**Visibles para Prestatario**:
- Solicitud creada
- Solicitud enviada
- Solicitud en revisión
- Solicitud observada
- Solicitud aprobada
- Solicitud rechazada
- Solicitud cancelada

**Eventos Internos**:
- Asignación a analista
- Cambio manual de estado
- Actualización de evaluación
- Validación de identidad
- Validación de reglas de producto

### Log de Auditoría

Todos los cambios se registran en `AuditLog`:
- Usuario que hizo la acción
- Acción específica (create, update, submit, approve, etc.)
- Timestamp exacto
- Metadata: antes/después, razón, etc.
- IP address (si disponible)

---

## 6. INTEGRACIÓN CON OTROS CU

### CU-10 (Personalización de Apariencia)
- Respeta branding del tenant en frontend
- Usa colores y logo configurados

### CU-13 (Verificación de Identidad)
- Valida identidad antes de submit
- Vincula IdentityVerification a solicitud
- Bloquea si DECLINED

### CU-38 (Gestión de Sucursales)
- Solicitud puede asociarse a sucursal
- Staff ve solo solicitudes de su sucursal
- Permite filtrar por sucursal

### CU-07 (Seguimiento del Crédito - Futuro)
- Timeline disponible para consulta
- Eventos registrados para posteridad

### CU-12 (Gestión Documental - Preparación)
- Campo documents_status en aplicación
- Timeline preparado para eventos de documentos
- Estructura lista para expansión

---

## 7. TESTING

### Pruebas Backend

```bash
# Ejecutar todas las pruebas
python manage.py test api.loans

# Pruebas específicas
python manage.py test api.loans.tests.CreditApplicationServiceTests
python manage.py test api.loans.tests.CreditApplicationViewTests
```

### Casos de Prueba

1. **Crear Solicitud**
   - Prestatario crea en DRAFT
   - Solo completar campos necesarios
   - Validar aplicación_number generado

2. **Enviar Solicitud**
   - Validar campos requeridos
   - Bloquear si producto inactivo
   - Bloquear si monto fuera de rango
   - Bloquear si identidad no verificada

3. **Cambiar Estados**
   - Validar transiciones permitidas
   - Rechazar transiciones inválidas
   - Crear eventos en timeline
   - Registrar auditoría

4. **Multi-tenancy**
   - Prestatario solo ve sus solicitudes
   - Staff solo ve del tenant
   - Bloquear acceso cross-tenant

5. **Identidad**
   - APPROVED → permite submit
   - PENDING → bloquea con mensaje
   - DECLINED → bloquea con mensaje
   - No existe → bloquea con mensaje

---

## 8. FRONTEND WEB (React + TypeScript)

### Rutas

```
/credit-applications/
/credit-applications/new
/credit-applications/{id}
/backoffice/credit-applications
/backoffice/credit-applications/{id}
```

### Componentes Principales

- `CreditApplicationForm` - Formulario crear/editar
- `CreditApplicationList` - Listar solicitudes
- `CreditApplicationDetail` - Ver detalles
- `CreditApplicationStatusBadge` - Badge de estado
- `CreditApplicationTimeline` - Mostrar timeline
- `CreditApplicationStatusActions` - Botones de cambio de estado
- `CreditApplicationObservationModal` - Modal para observaciones

### Estado y Gestión

```typescript
// Redux actions
- fetchApplications
- createApplication
- updateApplicationDraft
- submitApplication
- changeApplicationStatus
- addComment
- fetchTimeline
```

---

## 9. FLUTTER MÓVIL

### Pantallas

```
MyCreditApplicationsScreen
├─ Lista de solicitudes del usuario
├─ Filtros por estado
└─ Crear nueva solicitud

CreateCreditApplicationScreen
├─ Formulario de nueva solicitud
├─ Selección de producto
├─ Validación de campos
└─ Guardar como borrador o enviar

CreditApplicationDetailScreen
├─ Detalles completos
├─ Estado y timeline
├─ Observaciones
└─ Acciones posibles

CreditApplicationTimelineScreen
├─ Timeline de eventos
└─ Comentarios visibles
```

### Modelos

```dart
class LoanApplication {
  int id;
  String applicationNumber;
  String status;
  Decimal requestedAmount;
  int termMonths;
  String purpose;
  IdentityVerificationStatus identityVerificationStatus;
  // ... más campos
}
```

---

## 10. VARIABLES DE ENTORNO

```bash
# Backend
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:pass@localhost/db_name

# Frontend
REACT_APP_API_URL=http://localhost:8000/api
REACT_APP_TENANT_SUBDOMAIN=institution-slug

# Mobile
API_BASE_URL=http://10.0.2.2:8000/api  # Para emulador Android
```

---

## 11. NOTAS DE IMPLEMENTACIÓN

### Consideraciones Importantes

1. **Transacciones Atómicas**: Todos los cambios de estado usan `@transaction.atomic`
2. **Queryset Optimization**: Se usan `select_related()` y `prefetch_related()` para evitar N+1
3. **Indexación**: Índices en institution, status, created_at para query performance
4. **Paginación**: Standard es 25 items, configurable en settings
5. **Versionado de API**: Ready para v2 con cambios backward compatible
6. **Rate Limiting**: Aplicado a endpoints de creación/modificación

### Pendientes / Consideraciones Futuras

- [ ] Envío de notificaciones por email en cambios de estado
- [ ] Dashboard de analítica para staff
- [ ] Scoring automático basado en reglas configurables
- [ ] Integración con sistema de documentación (CU-12)
- [ ] Webhooks para integraciones externas
- [ ] Exportación a formatos (PDF, Excel)
- [ ] Búsqueda avanzada y reportes

---

## 12. COMANDOS ÚTILES

```bash
# Backend
python manage.py migrate                    # Aplicar migraciones
python manage.py createsuperuser            # Crear admin
python manage.py runserver                  # Servidor dev
python manage.py test                       # Ejecutar tests
python manage.py makemigrations             # Crear nuevas migraciones

# Frontend
npm install                                 # Instalar dependencias
npm run dev                                 # Servidor de desarrollo
npm run build                               # Build producción
npm run lint                                # Verificar código

# Mobile (Flutter)
flutter pub get                             # Instalar dependencias
flutter run                                 # Ejecutar en emulador
flutter build apk                           # Build APK
flutter build ios                           # Build iOS
```

---

## 13. CONTACTO Y SOPORTE

Para preguntas sobre implementación:
- Revisar tests en `api/loans/tests/`
- Revisar documentación del API schema en `/api/schema/`
- Contactar al equipo de desarrollo

**Versión del Documento**: 1.0
**Última Actualización**: 2026-05-03
**Estado**: ✅ Implementado y testeado

