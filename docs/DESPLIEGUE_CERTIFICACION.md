# Copia normal del proyecto para pruebas DGII

Usar el mismo proyecto y configuración de siempre: `MultiServices.settings`.
La copia en otra carpeta/puerto la administra el usuario. No hay configuración
Django paralela ni restricciones especiales de rutas.

## Ubuntu

1. Actualizar esta rama en la carpeta duplicada y activar su venv Python 3.10.
2. Instalar: `python -m pip install -r requirements.txt`.
3. En el servicio o shell de esa copia, quitar cualquier valor anterior
   `DJANGO_SETTINGS_MODULE=MultiServices.settings_certification` y usar:

```bash
export DJANGO_SETTINGS_MODULE=MultiServices.settings
python manage.py check
python manage.py migrate --plan
python manage.py migrate --noinput
# Ejemplo; elegir el puerto libre que utilizarás.
gunicorn MultiServices.wsgi:application --bind 127.0.0.1:8087
```

Si la BD de la copia está completamente vacía, ejecutar primero
`python manage.py migrate products --noinput` por las dependencias históricas.
Usar la BD propia de la carpeta duplicada, no un enlace a la BD comercial.
No importar datos de prueba encima de la BD comercial.

## Variables de esa copia

El archivo `.env` de la raíz se carga sin sobrescribir variables del proceso.
Usar `.env.example` como referencia y completar:

- DGII_ENVIRONMENT=cert
- ECF_EXPECTED_TAX_ID=132018559
- ECF_CERTIFICATE_PATH: ruta Ubuntu del P12, fuera de la carpeta pública.
- ECF_CERTIFICATE_PASSWORD: clave real.
- ECF_TRUSTED_CA_PATH y ECF_AUTH_TRUSTED_CA_PATH: CA confiables reales.
- ECF_AUTH_TOKEN_SECRET: secreto aleatorio de al menos 32 caracteres.
- ECF_REQUIRE_INBOUND_AUTH=true si se declara autenticación a DGII.

Mantener la configuración habitual de Django/HTTPS del servidor. No subir P12,
contraseñas, `.env` o bases de datos a GitHub. No basta el P12 para validar
firmas de terceros: también hacen falta las CA confiables.

## Rutas conservadas

- `/api/v1/`: ventas, administración, productos y e-CF.
- `/fe/autenticacion/api/semilla`
- `/fe/autenticacion/api/validacioncertificado`
- `/fe/recepcion/api/ecf`
- `/fe/aprobacioncomercial/api/ecf`
- Los alias históricos `/api/v1/fe/...` también siguen disponibles.

El proxy debe apuntar al puerto de la copia y conservar las rutas que se
publicarán. Un 404 de Nginx puede deberse al proxy o al prefijo, aunque Django
resuelva correctamente. Un puerto interno diferente no cambia las rutas Django.
Para DGII publicar HTTPS con puerto estándar; no registrar el puerto interno.

Tras publicar:
`python scripts/check_receiver_deployment.py --base-url https://TU-HOST-Y-PREFIJO --signed-auth`

En el campo central del portal introducir el host/prefijo público comprobado;
DGII agrega `/fe/...`. No confirmar URL hasta validar la copia publicada.
No es necesario cambiar ni publicar el frontend para probar estos servicios.
