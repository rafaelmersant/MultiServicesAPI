# Confianza explícita del firmante DGII en certificación

Activación manual en el `.env` de la copia de pruebas:

```dotenv
DGII_ENVIRONMENT=cert
ECF_CERT_TRUSTED_SIGNER_SHA256=3d0be20c8bd2917f0e2d5a8d4dac056b50993fa8ef5c9884798c58f940c59cbb
```

Esta huella corresponde al certificado del XML aportado por el usuario el
06/11/2026. No es el identificador de CA de 40 caracteres: es SHA256 del
certificado firmante completo. La confianza directa de ese certificado fue
autorizada expresamente por el usuario para cert.

El pin se comprueba después de RSA/digest. También se comprueban vigencia,
uso de firma digital si está declarado y que no sea un certificado CA.
La semilla debe seguir siendo propia, vigente y no reutilizada para emitir
token. No se acepta otro certificado por el nombre de su emisor.

Se aplica a autenticación, e-CF y ACECF recibidos. Si DGII usa otro firmante,
se rechazará: revisar su origen antes de añadir otra huella separada por coma.
No hay incorporación automática de certificados ni validación de revocación
por OCSP añadida en este cambio. Una renovación requiere autorizar una huella nueva.

En prod/precert se ignora el pin y se exige la CA. Con el pin vacío se conserva
el comportamiento anterior. Con pin activo en cert, CA_PATH no es necesario
para el firmante autorizado; pueden conservarse los valores existentes.

Publicar ecf/certificate_trust.py, ecf/inbound.py y ecf/inbound_auth.py; conservar
ecf/xml_verifier.py ya desplegado. Reiniciar solo el Gunicorn de pruebas.
Retirar ECF_AUTH_DIAGNOSTIC_DIR tras el diagnóstico.

Validación local: 28 pruebas aprobadas; XML DGII real verificado por las rutas
de firma de autenticación/recepción, sin solicitudes de red ni escrituras BD.
Esto no acredita todavía el flujo completo del paso 8 en el servidor.
