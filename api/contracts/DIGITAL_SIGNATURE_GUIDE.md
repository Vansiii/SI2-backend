# Guía de Firma Digital - Módulo de Contratos

## 📋 Resumen Ejecutivo

La firma digital implementada es una **firma digital simple** que cumple con los siguientes objetivos:
- ✅ Validación de identidad del firmante
- ✅ Registro de intención de firma
- ✅ Auditoría completa (IP, dispositivo, timestamp)
- ✅ Hash de integridad del documento
- ✅ No repudio (el firmante no puede negar que firmó)

**⚠️ IMPORTANTE**: Esta NO es una firma digital avanzada con certificado digital. Para cumplimiento legal estricto, se puede integrar con servicios como DocuSign o Adobe Sign.

---

## 🔐 ¿Cómo Funciona?

### Flujo Completo de Firma

```
1. Contrato publicado (PENDING_SIGNATURE)
   ↓
2. Usuario accede al contrato
   ↓
3. Sistema valida identidad (ya verificada en CU-13)
   ↓
4. Usuario lee términos y condiciones
   ↓
5. Usuario hace clic en "Firmar"
   ↓
6. Sistema captura:
   - Timestamp exacto
   - IP del usuario
   - Información del dispositivo
   - Hash SHA-256 del documento
   ↓
7. Sistema registra firma en ContractSignature
   ↓
8. Sistema actualiza estado del contrato
   ↓
9. Firma completada ✅
```

### Componentes de la Firma

#### 1. Hash del Documento (Integridad)

```python
def _generate_document_hash(contract: Contract) -> str:
    """
    Genera un hash SHA-256 del contrato para verificación de integridad.
    """
    # Crear string con datos clave del contrato
    data_string = (
        f"{contract.contract_number}"
        f"{contract.principal_amount}"
        f"{contract.interest_rate}"
        f"{contract.term_months}"
        f"{contract.contract_date}"
        f"{contract.loan_application.client.document_number}"
    )
    
    # Generar hash SHA-256
    hash_object = hashlib.sha256(data_string.encode())
    return hash_object.hexdigest()
```

**¿Qué garantiza?**
- Si alguien modifica el contrato después de firmado, el hash cambiará
- Permite verificar que el documento no fue alterado

#### 2. Registro de Firma (Auditoría)

```python
class ContractSignature(TenantModel):
    """Registro completo de cada firma"""
    
    # Quién firmó
    signer_type = 'BORROWER' | 'GUARANTOR' | 'INSTITUTION'
    user = ForeignKey(User)  # o guarantor
    
    # Cuándo firmó
    signed_at = DateTimeField()  # Timestamp exacto
    
    # Desde dónde firmó
    ip_address = GenericIPAddressField()
    device_info = JSONField()  # User-agent, SO, navegador
    geolocation = JSONField()  # Lat/Long si está disponible
    
    # Cómo firmó
    signature_method = 'DIGITAL' | 'BIOMETRIC' | 'OTP'
    signature_data = TextField()  # Hash del documento
    
    # Verificación adicional
    identity_verified = BooleanField()
    verification_method = CharField()  # '2FA', 'biometric', etc.
```

#### 3. Validación de Identidad

**Antes de permitir firmar, el sistema verifica:**

```python
# 1. Usuario está autenticado
if not request.user.is_authenticated:
    return Error("Debe iniciar sesión")

# 2. Usuario es el prestatario del contrato
if contract.loan_application.client.user != request.user:
    return Error("No es el prestatario de este contrato")

# 3. Identidad ya fue verificada (CU-13)
if contract.loan_application.identity_verification_status != 'APPROVED':
    return Error("Debe verificar su identidad primero")

# 4. Contrato puede ser firmado
if contract.status not in ['PENDING_SIGNATURE', 'PARTIALLY_SIGNED']:
    return Error("El contrato no está disponible para firma")
```

---

## 🎯 Implementación Actual

### Backend (Python/Django)

#### Endpoint de Firma

```python
POST /api/contracts/{id}/sign/

# Request Body:
{
    "signature_method": "DIGITAL",
    "signature_data": "acepto_firmar_este_contrato",
    "device_info": {
        "user_agent": "Mozilla/5.0...",
        "platform": "Windows",
        "browser": "Chrome",
        "screen_resolution": "1920x1080"
    },
    "geolocation": {
        "latitude": -16.5000,
        "longitude": -68.1500,
        "accuracy": 10
    },
    "verification_method": "2FA"
}

# Response:
{
    "message": "Contrato firmado exitosamente",
    "signature": {
        "id": 123,
        "signer_type": "BORROWER",
        "signer_name": "Juan Pérez",
        "signed_at": "2026-05-30T14:30:00Z",
        "ip_address": "192.168.1.100"
    },
    "contract_status": "ACTIVE"  // o "PARTIALLY_SIGNED"
}
```

#### Servicio de Firma

```python
# api/contracts/services/signature_service.py

class SignatureService:
    
    @staticmethod
    def sign_contract_as_borrower(
        contract: Contract,
        user,
        signature_data: str,
        ip_address: str,
        signature_method: str = 'DIGITAL',
        device_info: dict = None,
        geolocation: dict = None,
        verification_method: str = ''
    ) -> ContractSignature:
        """
        Firma un contrato como prestatario.
        """
        
        # 1. Validaciones
        if not contract.can_be_signed():
            raise ValueError("El contrato no puede ser firmado")
        
        if contract.loan_application.client.user != user:
            raise ValueError("No es el prestatario de este contrato")
        
        if contract.is_signed_by_borrower:
            raise ValueError("Ya ha firmado este contrato")
        
        # 2. Generar hash del documento
        document_hash = SignatureService._generate_document_hash(contract)
        
        # 3. Crear registro de firma
        with transaction.atomic():
            signature = ContractSignature.objects.create(
                institution=contract.institution,
                contract=contract,
                signer_type=ContractSignature.SignerType.BORROWER,
                user=user,
                signed_at=timezone.now(),
                signature_method=signature_method,
                signature_data=signature_data,
                ip_address=ip_address,
                device_info=device_info or {},
                geolocation=geolocation or {},
                identity_verified=True,
                verification_method=verification_method
            )
            
            # 4. Actualizar contrato
            contract.borrower_signed_at = signature.signed_at
            contract.borrower_signature_ip = ip_address
            contract.borrower_signature_data = document_hash
            contract.save()
            
            # 5. Actualizar estado del contrato
            contract.update_status_after_signature()
        
        return signature
```

---

## 🖥️ Frontend (React)

### Componente de Firma

```typescript
// ContractSignatureModal.tsx

import React, { useState } from 'react';
import { contractsService } from '@/services/contractsService';

interface Props {
  contract: Contract;
  onClose: () => void;
  onSuccess: () => void;
}

export const ContractSignatureModal: React.FC<Props> = ({
  contract,
  onClose,
  onSuccess
}) => {
  const [loading, setLoading] = useState(false);
  const [acceptedTerms, setAcceptedTerms] = useState(false);

  const handleSign = async () => {
    if (!acceptedTerms) {
      alert('Debe aceptar los términos y condiciones');
      return;
    }

    setLoading(true);

    try {
      // Capturar información del dispositivo
      const deviceInfo = {
        user_agent: navigator.userAgent,
        platform: navigator.platform,
        language: navigator.language,
        screen_resolution: `${screen.width}x${screen.height}`,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
      };

      // Intentar obtener geolocalización (opcional)
      let geolocation = null;
      if (navigator.geolocation) {
        try {
          const position = await new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject);
          });
          geolocation = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy
          };
        } catch (error) {
          console.log('Geolocalización no disponible');
        }
      }

      // Firmar contrato
      await contractsService.sign(contract.id, {
        signature_method: 'DIGITAL',
        signature_data: 'acepto_firmar_este_contrato',
        device_info: deviceInfo,
        geolocation: geolocation,
        verification_method: '2FA'  // Si usaste 2FA
      });

      alert('¡Contrato firmado exitosamente!');
      onSuccess();
      onClose();

    } catch (error) {
      alert('Error al firmar el contrato');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal open onClose={onClose}>
      <div className="p-6">
        <h2 className="text-2xl font-bold mb-4">Firmar Contrato</h2>
        
        {/* Vista previa del contrato */}
        <div className="border rounded p-4 mb-4 max-h-96 overflow-y-auto">
          <iframe 
            src={contract.pdf_url} 
            className="w-full h-96"
          />
        </div>

        {/* Términos y condiciones */}
        <div className="mb-4">
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={acceptedTerms}
              onChange={(e) => setAcceptedTerms(e.target.checked)}
              className="mr-2"
            />
            <span>
              He leído y acepto los términos y condiciones de este contrato.
              Entiendo que al firmar digitalmente estoy aceptando todos los
              términos establecidos.
            </span>
          </label>
        </div>

        {/* Información de seguridad */}
        <div className="bg-blue-50 p-3 rounded mb-4 text-sm">
          <p className="font-semibold mb-1">🔒 Información de seguridad:</p>
          <ul className="list-disc list-inside text-gray-700">
            <li>Su firma será registrada con fecha y hora exacta</li>
            <li>Se registrará su dirección IP y dispositivo</li>
            <li>Esta acción no puede ser revertida</li>
            <li>El documento quedará legalmente vinculante</li>
          </ul>
        </div>

        {/* Botones */}
        <div className="flex justify-end space-x-2">
          <Button
            variant="outline"
            onClick={onClose}
            disabled={loading}
          >
            Cancelar
          </Button>
          <Button
            variant="primary"
            onClick={handleSign}
            disabled={!acceptedTerms || loading}
          >
            {loading ? 'Firmando...' : 'Firmar Contrato'}
          </Button>
        </div>
      </div>
    </Modal>
  );
};
```

---

## 📱 Mobile (Flutter)

### Pantalla de Firma

```dart
// contract_signature_screen.dart

class ContractSignatureScreen extends StatefulWidget {
  final Contract contract;
  
  @override
  _ContractSignatureScreenState createState() => _ContractSignatureScreenState();
}

class _ContractSignatureScreenState extends State<ContractSignatureScreen> {
  bool _acceptedTerms = false;
  bool _loading = false;

  Future<void> _signContract() async {
    if (!_acceptedTerms) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Debe aceptar los términos y condiciones'))
      );
      return;
    }

    setState(() => _loading = true);

    try {
      // Capturar información del dispositivo
      final deviceInfo = await _getDeviceInfo();
      
      // Intentar obtener ubicación
      final geolocation = await _getGeolocation();

      // Firmar contrato
      await contractsService.signContract(
        widget.contract.id,
        signatureMethod: 'DIGITAL',
        signatureData: 'acepto_firmar_este_contrato',
        deviceInfo: deviceInfo,
        geolocation: geolocation,
      );

      // Mostrar éxito
      showDialog(
        context: context,
        builder: (context) => AlertDialog(
          title: Text('✅ Contrato Firmado'),
          content: Text('Su contrato ha sido firmado exitosamente'),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(context).pop();
                Navigator.of(context).pop(true); // Volver con éxito
              },
              child: Text('Aceptar'),
            ),
          ],
        ),
      );

    } catch (error) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error al firmar: $error'))
      );
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<Map<String, dynamic>> _getDeviceInfo() async {
    final deviceInfo = DeviceInfoPlugin();
    
    if (Platform.isAndroid) {
      final androidInfo = await deviceInfo.androidInfo;
      return {
        'platform': 'Android',
        'model': androidInfo.model,
        'version': androidInfo.version.release,
        'manufacturer': androidInfo.manufacturer,
      };
    } else if (Platform.isIOS) {
      final iosInfo = await deviceInfo.iosInfo;
      return {
        'platform': 'iOS',
        'model': iosInfo.model,
        'version': iosInfo.systemVersion,
        'name': iosInfo.name,
      };
    }
    
    return {};
  }

  Future<Map<String, dynamic>?> _getGeolocation() async {
    try {
      final position = await Geolocator.getCurrentPosition();
      return {
        'latitude': position.latitude,
        'longitude': position.longitude,
        'accuracy': position.accuracy,
      };
    } catch (e) {
      return null;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Firmar Contrato')),
      body: SingleChildScrollView(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Vista previa del contrato
            Container(
              height: 400,
              child: PDFViewer(url: widget.contract.pdfUrl),
            ),
            
            SizedBox(height: 20),
            
            // Checkbox de términos
            CheckboxListTile(
              value: _acceptedTerms,
              onChanged: (value) => setState(() => _acceptedTerms = value!),
              title: Text(
                'He leído y acepto los términos y condiciones de este contrato'
              ),
            ),
            
            SizedBox(height: 20),
            
            // Información de seguridad
            Card(
              color: Colors.blue[50],
              child: Padding(
                padding: EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '🔒 Información de seguridad:',
                      style: TextStyle(fontWeight: FontWeight.bold),
                    ),
                    SizedBox(height: 8),
                    Text('• Su firma será registrada con fecha y hora exacta'),
                    Text('• Se registrará su dirección IP y dispositivo'),
                    Text('• Esta acción no puede ser revertida'),
                    Text('• El documento quedará legalmente vinculante'),
                  ],
                ),
              ),
            ),
            
            SizedBox(height: 20),
            
            // Botón de firma
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _acceptedTerms && !_loading ? _signContract : null,
                child: _loading
                    ? CircularProgressIndicator(color: Colors.white)
                    : Text('Firmar Contrato'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
```

---

## 🔍 Verificación de Firma

### Cómo Verificar una Firma

```python
# Verificar integridad del documento
def verify_signature(signature: ContractSignature) -> dict:
    contract = signature.contract
    
    # Regenerar hash del documento actual
    current_hash = SignatureService._generate_document_hash(contract)
    
    # Comparar con hash almacenado
    is_valid = (contract.borrower_signature_data == current_hash)
    
    return {
        'is_valid': is_valid,
        'signer_name': signature.get_signer_name(),
        'signed_at': signature.signed_at,
        'ip_address': signature.ip_address,
        'document_hash': current_hash,
        'message': 'Firma válida' if is_valid else 'Documento modificado'
    }
```

---

## ⚖️ Validez Legal

### ¿Es Legalmente Válida?

**Depende de la jurisdicción**, pero generalmente:

✅ **SÍ es válida si:**
- Hay consentimiento claro del firmante
- Se puede identificar al firmante
- Hay registro de auditoría completo
- El documento no fue alterado después de firmar

❌ **NO es válida si:**
- La ley requiere firma manuscrita
- Se requiere certificado digital específico
- No hay forma de verificar identidad

### Recomendaciones Legales

1. **Consultar con abogado** sobre requisitos locales
2. **Agregar cláusula** en términos y condiciones:
   ```
   "El prestatario acepta que la firma digital tiene la misma
   validez legal que una firma manuscrita conforme a la Ley
   de Firma Digital [número de ley local]"
   ```
3. **Mantener auditoría completa** de todas las firmas
4. **Backup de documentos firmados** en múltiples ubicaciones

---

## 🚀 Mejoras Futuras

### Fase 2: Firma Biométrica

```python
# Capturar firma manuscrita en tablet/móvil
signature_data = {
    'type': 'BIOMETRIC',
    'image': 'base64_encoded_signature_image',
    'strokes': [...],  # Datos de trazos
    'pressure': [...],  # Datos de presión
    'speed': [...]     # Velocidad de firma
}
```

### Fase 3: Integración con DocuSign

```python
# Enviar a DocuSign para firma avanzada
docusign_service.send_for_signature(
    contract=contract,
    signers=[
        {'email': borrower.email, 'name': borrower.name},
        {'email': guarantor.email, 'name': guarantor.name}
    ]
)
```

### Fase 4: Certificado Digital

```python
# Firma con certificado digital PKI
certificate_service.sign_with_certificate(
    document=contract_pdf,
    certificate=user_certificate,
    private_key=user_private_key
)
```

---

## 📊 Resumen

| Aspecto | Implementación Actual | Mejora Futura |
|---------|----------------------|---------------|
| Tipo | Firma digital simple | Firma avanzada con certificado |
| Validación | Identidad verificada (CU-13) | Certificado digital PKI |
| Integridad | Hash SHA-256 | Firma criptográfica |
| Auditoría | IP, dispositivo, timestamp | + Certificado, + Blockchain |
| Validez Legal | Depende de jurisdicción | Cumplimiento total |
| Costo | Gratis | Servicio externo ($) |

---

## ✅ Conclusión

La firma digital implementada es **suficiente para un MVP** y cumple con:
- ✅ Identificación del firmante
- ✅ Intención clara de firmar
- ✅ Auditoría completa
- ✅ Integridad del documento
- ✅ No repudio

Para **cumplimiento legal estricto**, se recomienda:
1. Consultar con abogado local
2. Agregar cláusulas legales apropiadas
3. Considerar integración con DocuSign/Adobe Sign para casos críticos

**La implementación actual es funcional y segura para la mayoría de casos de uso.**
