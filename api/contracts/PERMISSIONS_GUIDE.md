# Guía de Permisos - Módulo de Contratos

## 📋 Permisos Agregados

Se han agregado **13 nuevos permisos** al sistema, organizados en 2 categorías:

### Categoría: Contratos de Crédito (8 permisos)

| Código | Nombre | Descripción | Roles Sugeridos |
|--------|--------|-------------|-----------------|
| `contracts.view` | Ver Contratos | Permite ver contratos de crédito | Admin, Staff, Cliente |
| `contracts.generate` | Generar Contratos | Permite generar contratos desde solicitudes aprobadas | Admin, Staff |
| `contracts.publish` | Publicar Contratos | Permite publicar contratos para firma | Admin, Staff |
| `contracts.sign` | Firmar Contratos | Permite firmar contratos digitalmente | Admin, Staff, Cliente, Garante |
| `contracts.cancel` | Cancelar Contratos | Permite cancelar contratos | Admin |
| `contracts.download` | Descargar Contratos | Permite descargar PDFs de contratos | Admin, Staff, Cliente |
| `contracts.view_signatures` | Ver Firmas | Permite ver estado y detalles de firmas | Admin, Staff |
| `contracts.view_amortization` | Ver Tabla de Amortización | Permite ver tabla de amortización de contratos | Admin, Staff, Cliente |

### Categoría: Plantillas de Contratos (5 permisos)

| Código | Nombre | Descripción | Roles Sugeridos |
|--------|--------|-------------|-----------------|
| `contract_templates.view` | Ver Plantillas | Permite ver plantillas de contratos | Admin |
| `contract_templates.create` | Crear Plantillas | Permite crear nuevas plantillas de contratos | Admin |
| `contract_templates.edit` | Editar Plantillas | Permite editar plantillas de contratos existentes | Admin |
| `contract_templates.delete` | Eliminar Plantillas | Permite eliminar plantillas de contratos | Admin |
| `contract_templates.preview` | Vista Previa de Plantillas | Permite ver vista previa de plantillas | Admin |

## 🔧 Instalación de Permisos

### Paso 1: Ejecutar Seed de Permisos

```bash
python manage.py seed_permissions
```

Este comando creará los 13 nuevos permisos en la base de datos.

**Salida esperada:**
```
=== CREANDO CATÁLOGO DE PERMISOS ===

📁 Contratos de Crédito
  ✓ contracts.view - Ver Contratos
  ✓ contracts.generate - Generar Contratos
  ✓ contracts.publish - Publicar Contratos
  ✓ contracts.sign - Firmar Contratos
  ✓ contracts.cancel - Cancelar Contratos
  ✓ contracts.download - Descargar Contratos
  ✓ contracts.view_signatures - Ver Firmas
  ✓ contracts.view_amortization - Ver Tabla de Amortización

📁 Plantillas de Contratos
  ✓ contract_templates.view - Ver Plantillas
  ✓ contract_templates.create - Crear Plantillas
  ✓ contract_templates.edit - Editar Plantillas
  ✓ contract_templates.delete - Eliminar Plantillas
  ✓ contract_templates.preview - Vista Previa de Plantillas

=== RESUMEN ===
Permisos creados: 13
```

### Paso 2: Asignar Permisos a Roles

Tienes 3 opciones:

#### Opción A: Desde el Admin de Django (Manual)

1. Ir a: http://localhost:8000/admin/roles/role/
2. Seleccionar un rol (ej: "Administrador")
3. En "Permissions", buscar y seleccionar los permisos de contratos
4. Guardar

#### Opción B: Desde la API (Programático)

```python
from api.roles.models import Role, Permission

# Obtener rol
role = Role.objects.get(institution_id=1, name='Administrador')

# Obtener permisos de contratos
contract_perms = Permission.objects.filter(
    code__startswith='contracts.'
)
template_perms = Permission.objects.filter(
    code__startswith='contract_templates.'
)

# Asignar permisos
role.permissions.add(*contract_perms)
role.permissions.add(*template_perms)
```

#### Opción C: Script Automático (Recomendado)

Crear un comando de management:

```bash
python manage.py assign_contract_permissions
```

## 🎭 Configuración por Rol

### Rol: Administrador (Admin)

**Permisos completos:**
```python
ADMIN_PERMISSIONS = [
    # Contratos
    'contracts.view',
    'contracts.generate',
    'contracts.publish',
    'contracts.sign',
    'contracts.cancel',
    'contracts.download',
    'contracts.view_signatures',
    'contracts.view_amortization',
    # Plantillas
    'contract_templates.view',
    'contract_templates.create',
    'contract_templates.edit',
    'contract_templates.delete',
    'contract_templates.preview',
]
```

**Puede:**
- ✅ Gestionar plantillas de contratos
- ✅ Generar contratos
- ✅ Publicar contratos
- ✅ Cancelar contratos
- ✅ Ver todas las firmas
- ✅ Descargar PDFs

### Rol: Staff (Analista de Crédito)

**Permisos operativos:**
```python
STAFF_PERMISSIONS = [
    # Contratos
    'contracts.view',
    'contracts.generate',
    'contracts.publish',
    'contracts.download',
    'contracts.view_signatures',
    'contracts.view_amortization',
]
```

**Puede:**
- ✅ Ver contratos
- ✅ Generar contratos desde solicitudes aprobadas
- ✅ Publicar contratos para firma
- ✅ Descargar PDFs
- ✅ Ver estado de firmas
- ❌ NO puede gestionar plantillas
- ❌ NO puede cancelar contratos

### Rol: Cliente (Prestatario)

**Permisos limitados:**
```python
CLIENT_PERMISSIONS = [
    'contracts.view',           # Solo sus propios contratos
    'contracts.sign',           # Solo sus propios contratos
    'contracts.download',       # Solo sus propios contratos
    'contracts.view_amortization',  # Solo sus propios contratos
]
```

**Puede:**
- ✅ Ver sus propios contratos
- ✅ Firmar sus propios contratos
- ✅ Descargar PDFs de sus contratos
- ✅ Ver su tabla de amortización
- ❌ NO puede ver contratos de otros clientes
- ❌ NO puede generar contratos
- ❌ NO puede gestionar plantillas

### Rol: Garante

**Permisos específicos:**
```python
GUARANTOR_PERMISSIONS = [
    'contracts.view',      # Solo contratos donde es garante
    'contracts.sign',      # Solo contratos donde es garante
    'contracts.download',  # Solo contratos donde es garante
]
```

**Puede:**
- ✅ Ver contratos donde es garante
- ✅ Firmar contratos donde es garante
- ✅ Descargar PDFs de esos contratos
- ❌ NO puede ver otros contratos
- ❌ NO puede generar contratos

## 🔐 Validación de Permisos en el Código

### En las Vistas (ViewSets)

Los permisos ya están implementados en `api/contracts/views.py`:

```python
class ContractViewSet(viewsets.ModelViewSet):
    def get_permissions(self):
        if self.action == 'generate_from_application':
            return [IsAuthenticated(), CanGenerateContract()]
        elif self.action == 'publish':
            return [IsAuthenticated(), CanPublishContract()]
        elif self.action == 'sign':
            return [IsAuthenticated(), CanSignContract()]
        # ...
```

### En los Permisos Personalizados

Los permisos personalizados verifican los permisos de Django:

```python
class CanGenerateContract(permissions.BasePermission):
    def has_permission(self, request, view):
        # Verifica el permiso 'contracts.add_contract'
        return request.user.has_perm('contracts.add_contract')
```

## 📊 Matriz de Permisos Completa

| Acción | Admin | Staff | Cliente | Garante |
|--------|:-----:|:-----:|:-------:|:-------:|
| **Contratos** |
| Ver contratos | ✅ Todos | ✅ Todos | ✅ Propios | ✅ Donde es garante |
| Generar contratos | ✅ | ✅ | ❌ | ❌ |
| Publicar contratos | ✅ | ✅ | ❌ | ❌ |
| Firmar contratos | ✅ | ✅ | ✅ Propios | ✅ Donde es garante |
| Cancelar contratos | ✅ | ❌ | ❌ | ❌ |
| Descargar PDF | ✅ | ✅ | ✅ Propios | ✅ Donde es garante |
| Ver firmas | ✅ | ✅ | ✅ Propias | ✅ Propias |
| Ver amortización | ✅ | ✅ | ✅ Propia | ❌ |
| **Plantillas** |
| Ver plantillas | ✅ | ❌ | ❌ | ❌ |
| Crear plantillas | ✅ | ❌ | ❌ | ❌ |
| Editar plantillas | ✅ | ❌ | ❌ | ❌ |
| Eliminar plantillas | ✅ | ❌ | ❌ | ❌ |
| Vista previa | ✅ | ❌ | ❌ | ❌ |

## 🚀 Script de Asignación Automática

Puedes crear este comando para asignar permisos automáticamente:

```python
# api/contracts/management/commands/assign_contract_permissions.py

from django.core.management.base import BaseCommand
from api.roles.models import Role, Permission
from api.tenants.models import FinancialInstitution

class Command(BaseCommand):
    help = 'Asigna permisos de contratos a roles existentes'

    def handle(self, *args, **options):
        # Permisos por rol
        role_permissions = {
            'Administrador': [
                'contracts.view', 'contracts.generate', 'contracts.publish',
                'contracts.sign', 'contracts.cancel', 'contracts.download',
                'contracts.view_signatures', 'contracts.view_amortization',
                'contract_templates.view', 'contract_templates.create',
                'contract_templates.edit', 'contract_templates.delete',
                'contract_templates.preview',
            ],
            'Staff': [
                'contracts.view', 'contracts.generate', 'contracts.publish',
                'contracts.download', 'contracts.view_signatures',
                'contracts.view_amortization',
            ],
            'Cliente': [
                'contracts.view', 'contracts.sign', 'contracts.download',
                'contracts.view_amortization',
            ],
        }

        for institution in FinancialInstitution.objects.filter(is_active=True):
            for role_name, perm_codes in role_permissions.items():
                try:
                    role = Role.objects.get(
                        institution=institution,
                        name=role_name
                    )
                    
                    perms = Permission.objects.filter(code__in=perm_codes)
                    role.permissions.add(*perms)
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✅ {institution.name} - {role_name}: '
                            f'{perms.count()} permisos asignados'
                        )
                    )
                except Role.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f'⚠️  {institution.name} - Rol "{role_name}" no existe'
                        )
                    )
```

## ✅ Checklist de Verificación

- [ ] Ejecutar `python manage.py seed_permissions`
- [ ] Verificar que los 13 permisos se crearon
- [ ] Asignar permisos al rol "Administrador"
- [ ] Asignar permisos al rol "Staff"
- [ ] Asignar permisos al rol "Cliente"
- [ ] Probar acceso desde cada rol
- [ ] Verificar que los permisos se respetan en la API
- [ ] Documentar permisos en el frontend

## 🔍 Verificación

### Verificar permisos creados:

```bash
python manage.py shell
```

```python
from api.roles.models import Permission

# Ver permisos de contratos
contract_perms = Permission.objects.filter(code__startswith='contracts.')
print(f"Permisos de contratos: {contract_perms.count()}")
for p in contract_perms:
    print(f"  - {p.code}: {p.name}")

# Ver permisos de plantillas
template_perms = Permission.objects.filter(code__startswith='contract_templates.')
print(f"\nPermisos de plantillas: {template_perms.count()}")
for p in template_perms:
    print(f"  - {p.code}: {p.name}")
```

### Verificar permisos de un rol:

```python
from api.roles.models import Role

role = Role.objects.get(institution_id=1, name='Administrador')
contract_perms = role.permissions.filter(code__startswith='contracts.')
print(f"Permisos de contratos del Admin: {contract_perms.count()}")
```

---

**Última actualización**: 30 de Mayo, 2026  
**Versión**: 1.0
