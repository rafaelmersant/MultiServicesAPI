# Producción e-CF: instalación sobre el sistema existente

Los NCF tradicionales conservan sus modelos y flujos. No se garantiza ausencia
de incidencias sin verificar la configuración, dependencias y BD del servidor.
Programar una ventana breve para migraciones/reinicio y comprobar una venta NCF
antes de devolver el sistema al personal. No vaciar ni reemplazar la BD real.

## 1. Preparación y respaldo

- Trabajar en la carpeta y rama de producción correctas; `git status --short`
  debe revisarse antes del pull. Resolver cambios locales sin `reset --hard`.
- Respaldar fuera del repositorio: settings.py del servidor, .env, configuración
  Nginx/Gunicorn, media y BD usando el mecanismo consistente de su motor.
  Para SQLite, usar backup de SQLite o detener escrituras antes de copiar.
- Guardar `git rev-parse HEAD` y `python -m pip freeze` del venv actual.
- Mantener SECRET_KEY, DATABASES, ALLOWED_HOSTS, STATIC_ROOT, configuración proxy
  y rutas públicas actuales. No copiar settings.py de desarrollo completo.
- Usar Python 3.10, como el entorno validado; no usar Python 3.6 de Ubuntu 18.04.
  No actualizar el Python del sistema durante este despliegue.

## 2. Código y dependencias

Comandos desde la carpeta real de producción, con su venv activado:

```bash
git pull --ff-only
python --version
python -m pip install -r requirements.txt
python -m pip check
```

El pull utiliza la rama ya configurada: comprobarla antes con `git branch --show-current`.
Para conservar un retorno rápido, instalar primero en un venv Python 3.10 nuevo
y cambiar Gunicorn a ese venv al finalizar; no cambiar el proyecto ni sus rutas.
Si el proyecto usa un driver de BD adicional, instalar también el mismo driver
y versión de producción: requirements.txt no sustituye dependencias particulares
del servidor. Las versiones nuevas de e-CF incluyen signxml, cryptography, lxml,
python-dotenv, requests, xmltodict y herramientas de PDF/QR.

## 3. Agregados al settings.py del servidor

```python
from dotenv import load_dotenv

# Inmediatamente DESPUÉS de definir BASE_DIR:
load_dotenv(os.path.join(BASE_DIR, '.env'), override=False)
```

Agregar `'ecf.apps.EcfConfig'` a INSTALLED_APPS sin duplicarlo.
Agregar `'x-auth-token'` a CORS_ALLOW_HEADERS si el frontend accederá al módulo e-CF.
Si faltan, definir:

```python
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
```

Mantener DEBUG=False, ALLOWED_HOSTS real y SECRET_KEY actual. No añadir prefijos
`/api` a FORCE_SCRIPT_NAME ni modificar rutas/proxy para este cambio. Conservar
`DJANGO_SETTINGS_MODULE=MultiServices.settings`. El nuevo código de URLs viene
en el pull; no reemplazarlo por copias antiguas del servidor.

## 4. .env de producción

Completar valores reales; no ejecutar esto como comandos de shell:

```dotenv
DGII_ENVIRONMENT=prod
ECF_EXPECTED_TAX_ID=132018559
ECF_CERTIFICATE_PATH=/home/privatefiles/certificado.p12
ECF_CERTIFICATE_PASSWORD='CLAVE_REAL_DEL_P12'
ECF_TRUSTED_CA_PATH=/home/privatefiles/ca-receptores-produccion.pem
ECF_AUTH_TRUSTED_CA_PATH=/home/privatefiles/ca-autenticacion-produccion.pem
ECF_REQUIRE_INBOUND_AUTH=true
ECF_AUTH_TOKEN_SECRET=SECRETO_ALEATORIO_GENERADO
ECF_CERT_TRUSTED_SIGNER_SHA256=
DGII_TIMEOUT_SECONDS=30
```

Generar un secreto una sola vez y copiarlo al .env:

```bash
python -c 'import secrets; print(secrets.token_urlsafe(48))'
chmod 600 .env
```

Los archivos CA deben existir, contener autoridades confiables reales para
validar certificados de los remitentes y ser legibles por el usuario de Gunicorn.
No basta convertir el certificado personal P12 a PEM: ese certificado no es una
CA. No reutilizar la Sub-CA TEST incompatible que investigamos ni el pin TEST.
En producción el pin de certificación se ignora y la cadena CA es obligatoria.
Pueden compartir un paquete de CA verificado si cubre ambos usos.
El P12 debe estar vigente y corresponder al firmante autorizado; protegerlo
fuera del directorio público. Quitar ECF_AUTH_DIAGNOSTIC_DIR del entorno productivo.
Las variables exportadas por el servicio prevalecen sobre .env: comprobar que
Gunicorn no conserve DGII_ENVIRONMENT=cert ni rutas antiguas.
DGII_BASE_URL no es necesario: ecf/config.py selecciona la URL según el ambiente.

## 5. Migraciones y verificaciones

```bash
python manage.py check
python manage.py check --deploy
python manage.py makemigrations --check --dry-run
python manage.py showmigrations ecf
python manage.py migrate --plan
```

Revisar el plan. En BD existente aplicar las pendientes del branch; e-CF tiene
migraciones 0001–0009. No generar migraciones nuevas ni usar --fake.
Con respaldo verificado y escrituras detenidas durante la ventana:

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

Si se trata de una BD completamente vacía, existe una dependencia histórica:
ejecutar primero `python manage.py migrate products --noinput` y después migrate.
Esto no es necesario sobre la BD comercial ya operativa.

Reiniciar solamente el servicio Gunicorn de producción con su método habitual
y su puerto existente; no iniciar una segunda instancia sobre el mismo puerto
ni detener los procesos del ambiente test. Mantener Nginx y sus rutas actuales.

## 6. Prueba antes de confirmar el paso 12

- Iniciar sesión, abrir usuarios/productos y consultar facturas tradicionales.
- Validar una venta NCF y su impresión mediante el procedimiento habitual,
  verificando correlativo, impuestos y existencia; no emitir ventas ficticias.
- Comprobar admin y archivos estáticos; revisar logs por errores 500.
- No importar fixtures, casos de certificación ni rangos fiscales de prueba.
- No activar secuencias electrónicas ni enviar facturas a DGII hasta tener
  autorización y rangos reales. Configurar prod no asigna por sí solo un e-NCF.
- Verificar HTTPS y que /fe/... llegue a Django sin redirecciones del proxy.

Ejemplo de validación de autenticación con el certificado local autorizado
(no envía comprobantes fiscales):

```bash
python scripts/check_receiver_deployment.py --base-url https://sistemacenter.org/api/api/v1 --signed-auth
```

Usar esa base únicamente si es la ruta definitiva real comprobada. El script
comprueba autenticación y rechazos de solicitudes vacías; no demuestra por sí
solo la recepción completa de un e-CF/ACECF válido de cada emisor externo.
No confirmar URLs si falla la cadena CA o alguna comprobación pública.

En los tres campos centrales del portal, sin https:// ni el sufijo /fe/...:
`sistemacenter.org/api/api/v1` (si esa es efectivamente la base verificada).

## 7. Operación y retorno

El frontend actual puede mantenerse para operación tradicional. Si se despliega
el frontend con el módulo e-CF, usar su URL productiva actual para REACT_APP_API_URL
y comprobar login/X-Auth-Token. No hace falta desplegar React para publicar /fe/.

Si la validación operativa falla, mantener la ventana y volver al commit, venv
y configuración respaldados. No revertir migraciones o restaurar una BD sobre
ventas nuevas sin analizar los datos: una restauración puede perder operaciones.
La instalación en Ubuntu y la validación productiva siguen pendientes de ejecutar
en el servidor; las comprobaciones locales no sustituyen esas pruebas.
