# Checklist de Despliegue - Módulo de Contratos

Este checklist asegura que el módulo de contratos esté correctamente configurado antes de usar en producción.

## ✅ Pre-requisitos del Sistema

### Python y Dependencias
- [ ] Python 3.10+ instalado
- [ ] Django 5.0+ instalado
- [ ] Django REST Framework instalado
- [ ] `weasyprint` instalado (`pip install weasyprint`)
- [ ] `python-dateutil` instalado (`pip install python-dateutil`)
- [ ] `django-filter` instalado (`pip install django-filter`)

### Dependencias del Sistema (para WeasyPrint)

#### Windows
- [ ] GTK3 Runtime instalado
  - Descargar de: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer
  - Ejecutar instalador y seguir instrucciones

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get install python3-cffi python3-brotli libpango-1.0-0 libpangoft2-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info
```

#### macOS
```bash
brew install python3 cairo pango gdk-pixbuf libffi
```

## ✅ Configuración de Django

### Settings
- [ ] `'api.contracts'` agregado a `INSTALLED_APPS`
- [ ] Migraciones creadas: `python manage.py makemigrations contracts`
- [ ] Migraciones aplicadas: `python manage.py migrate contracts`

### URLs
- [ ] URLs de contratos incluidas en `api/urls.py`
- [ ] Verificar que las rutas funcionan: `/api/contracts/`, `/api/contract-templates/`

### Modelos Exportados
- [ ] Modelos de contratos agregados a `api/models.py` para compatibilidad

## ✅ Configuración de Base de Datos

### Verificar Tablas Creadas
```sql
-- Verificar que existen las tablas:
SELECT table_name FROM information_schema.tables 
WHERE table_name LIKE 'contracts_%';

-- Deberían existir:
-- contracts_contract
-- contracts_contracttemplate
-- contracts_contractsignature
-- contracts_contractamortizationschedule
-- contracts_contractdocument
```

### Verificar Índices
- [ ] Índices creados correctamente en campos clave
- [ ] Foreign keys configuradas

## ✅ Integración con Otros Módulos

### Módulo de Loans
- [ ] Campo `contract_generated` agregado a `LoanApplication`
- [ ] Migración aplicada para el nuevo campo
- [ ] Verificar que solicitudes aprobadas pueden generar contratos

### Módulo de Storage
- [ ] Supabase Storage configurado
- [ ] Bucket para contratos creado
- [ ] Permisos de storage configurados

### Módulo de Garantías
- [ ] Garantes pueden ser vinculados a contratos
- [ ] Firmas de garantes funcionan correctamente

## ✅ Plantillas de Contratos

### Plantilla por Defecto
- [ ] Ejecutar comando: `python manage.py create_default_contract_template --institution-id=1`
- [ ] Verificar que la plantilla se creó correctamente
- [ ] Probar vista previa de plantilla

### Plantillas Personalizadas (Opcional)
- [ ] Crear plantillas específicas por producto si es necesario
- [ ] Configurar términos y condiciones legales
- [ ] Validar variables disponibles

## ✅ Permisos y Roles

### Permisos de Django
```python
# Verificar que existen estos permisos:
from django.contrib.auth.models import Permission

permissions = [
    'contracts.add_contract',
    'contracts.change_contract',
    'contracts.delete_contract',
    'contracts.view_contract',
    'contracts.add_contracttemplate',
    'contracts.change_contracttemplate',
    'contracts.delete_contracttemplate',
    'contracts.view_contracttemplate',
]

for perm in permissions:
    app, codename = perm.split('.')
    exists = Permission.objects.filter(
        content_type__app_label=app,
        codename=codename
    ).exists()
    print(f"{perm}: {'✓' if exists else '✗'}")
```

### Roles de Usuario
- [ ] Rol de Staff puede generar contratos
- [ ] Rol de Admin puede gestionar plantillas
- [ ] Prestatarios pueden ver y firmar sus contratos
- [ ] Garantes pueden firmar contratos donde son garantes

## ✅ Tests

### Tests Unitarios
```bash
# Ejecutar tests del módulo
python manage.py test api.contracts

# Ejecutar tests específicos
python manage.py test api.contracts.tests.test_models
```

- [ ] Todos los tests pasan
- [ ] No hay warnings críticos

### Tests de Integración
- [ ] Crear solicitud aprobada
- [ ] Generar contrato desde solicitud
- [ ] Publicar contrato
- [ ] Firmar contrato
- [ ] Descargar PDF
- [ ] Verificar tabla de amortización

## ✅ Funcionalidades Clave

### Generación de Contratos
- [ ] Generar contrato desde solicitud aprobada funciona
- [ ] PDF se genera correctamente
- [ ] PDF se guarda en storage
- [ ] Tabla de amortización se crea automáticamente
- [ ] Variables se reemplazan correctamente en plantilla

### Firmas Digitales
- [ ] Prestatario puede firmar
- [ ] Garantes pueden firmar (si aplica)
- [ ] Staff puede firmar como institución
- [ ] Estado del contrato se actualiza automáticamente
- [ ] IP y dispositivo se registran

### Tabla de Amortización
- [ ] Cuotas se calculan correctamente
- [ ] Capital e interés son correctos
- [ ] Saldo pendiente es correcto
- [ ] Última cuota cierra en cero

### Descargas
- [ ] PDF se puede descargar
- [ ] Vista previa HTML funciona
- [ ] URLs firmadas expiran correctamente

## ✅ Seguridad

### Autenticación y Autorización
- [ ] Solo usuarios autenticados pueden acceder
- [ ] Permisos se verifican correctamente
- [ ] Prestatarios solo ven sus propios contratos
- [ ] Staff solo ve contratos de su tenant

### Datos Sensibles
- [ ] PDFs se almacenan de forma segura
- [ ] URLs de descarga son temporales
- [ ] Firmas incluyen hash de integridad
- [ ] IP y dispositivo se registran para auditoría

### Multi-tenancy
- [ ] Contratos están aislados por institución
- [ ] No hay fugas de datos entre tenants
- [ ] Queries filtran por institución automáticamente

## ✅ Performance

### Optimizaciones
- [ ] Queries usan `select_related` y `prefetch_related`
- [ ] Índices en campos de búsqueda frecuente
- [ ] Paginación configurada en listados

### Carga de Archivos
- [ ] PDFs se generan de forma eficiente
- [ ] Storage tiene suficiente espacio
- [ ] Límites de tamaño configurados

## ✅ Monitoreo y Logs

### Logging
- [ ] Logs configurados para el módulo
- [ ] Eventos importantes se registran:
  - Generación de contratos
  - Firmas
  - Cancelaciones
  - Errores en generación de PDF

### Auditoría
- [ ] Todas las acciones se auditan automáticamente
- [ ] Cambios de estado se registran
- [ ] Accesos a documentos se registran

## ✅ Documentación

### Para Desarrolladores
- [ ] README.md está actualizado
- [ ] IMPLEMENTATION_SUMMARY.md revisado
- [ ] EXAMPLE_USAGE.py probado
- [ ] Comentarios en código son claros

### Para Usuarios
- [ ] Documentación de API disponible
- [ ] Guía de uso para staff
- [ ] Guía de firma para prestatarios

## ✅ Backup y Recuperación

### Backups
- [ ] PDFs incluidos en backup automático
- [ ] Base de datos se respalda regularmente
- [ ] Procedimiento de restauración documentado

### Disaster Recovery
- [ ] Plan de recuperación ante desastres
- [ ] Contratos críticos identificados
- [ ] Procedimiento de regeneración de PDFs

## ✅ Compliance y Legal

### Requisitos Legales
- [ ] Términos y condiciones revisados por legal
- [ ] Firma digital cumple con regulaciones locales
- [ ] Retención de documentos según normativa
- [ ] Privacidad de datos cumple con GDPR/local

### Auditoría Legal
- [ ] Registro completo de firmas
- [ ] Timestamps verificables
- [ ] Integridad de documentos garantizada

## ✅ Capacitación

### Staff
- [ ] Capacitación en generación de contratos
- [ ] Capacitación en gestión de plantillas
- [ ] Capacitación en resolución de problemas

### Usuarios Finales
- [ ] Guía de firma digital
- [ ] FAQ disponible
- [ ] Soporte técnico preparado

## ✅ Go-Live

### Pre-producción
- [ ] Todos los tests pasan en staging
- [ ] Pruebas de carga realizadas
- [ ] Rollback plan preparado

### Producción
- [ ] Deploy realizado exitosamente
- [ ] Verificación post-deploy completada
- [ ] Monitoreo activo
- [ ] Equipo de soporte alertado

### Post-producción
- [ ] Primeros contratos generados exitosamente
- [ ] No hay errores críticos en logs
- [ ] Performance es aceptable
- [ ] Usuarios reportan satisfacción

---

## 🚨 Problemas Comunes y Soluciones

### Error: "No module named 'weasyprint'"
**Solución**: `pip install weasyprint`

### Error: "OSError: cannot load library 'gobject-2.0-0'"
**Solución**: Instalar GTK3 Runtime (Windows) o dependencias del sistema (Linux/Mac)

### Error: "No hay plantilla de contrato disponible"
**Solución**: Ejecutar `python manage.py create_default_contract_template --institution-id=X`

### Error: "La solicitud debe estar en estado APPROVED"
**Solución**: Verificar que la solicitud esté aprobada antes de generar contrato

### PDFs se ven mal o sin estilos
**Solución**: Verificar que el CSS esté correctamente incluido en la plantilla HTML

### Firmas no actualizan el estado del contrato
**Solución**: Verificar que los signals estén configurados correctamente

---

## 📞 Contacto y Soporte

Para problemas o preguntas:
- Revisar documentación en `README.md`
- Consultar ejemplos en `EXAMPLE_USAGE.py`
- Contactar al equipo de desarrollo

---

**Última actualización**: 30 de Mayo, 2026  
**Versión del checklist**: 1.0
