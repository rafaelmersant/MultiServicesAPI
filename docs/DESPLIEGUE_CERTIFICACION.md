# Despliegue aislado DGII — pasos 7 a 11

## Qué contiene esta entrega

- Modelos/migraciones e-CF 0001–0008, firma, envíos, RFCE, PDF y controles de identidad/orden.
- Recepción e-CF -> ARECF firmado; aprobación comercial -> validación XML/firma y HTTP 200/400.
- Autenticación semilla firmada -> token; rutas insensibles a mayúsculas y compatibles con `reverse()`.
- UI React e-CF separada, token de sesión y permisos Admin/Owner. Los modelos/operaciones NCF tradicionales no se reemplazan.
- Configuración **aislada**: otra base SQLite, otro servicio Gunicorn, otro dominio y solamente cuatro endpoints públicos. No requiere desplegar React para validar URL.

Paso 7: URL de prueba con DGII_ENVIRONMENT=cert. Paso 12: URL de producción, después de completar las pruebas; no cambiar a prod ahora.

## GitHub

Incluir los cambios de código, `ecf/migrations/`, `ecf/assets/132018559.png`, XSD, scripts, tests, requirements, deploy y esta guía. Revisar `git diff` y `git status` en ambos repositorios antes de commit/push. React tiene cambios en App.js, navBarSide.jsx, authService.js, httpService.js y el nuevo electronicInvoices.jsx.

No subir `.env`, certificado/clave, bases de datos, backups, `test_data`, `tmp` ni `output`. Las pruebas que usan el Excel/XML oficial requieren esos archivos locales. No copiar la BD comercial ni la BD local de certificación al despliegue nuevo.

## Ubuntu: instancia nueva

Rutas propuestas (ajustables): `/opt/multiservices-certification/app`, venv hermano, usuario `ecfcert`, puerto interno 8087. Python **3.10**, igual al entorno validado. Conservar el servicio, venv, BD y Nginx comerciales actuales.

1. Crear usuario sin login `ecfcert`; clonar desde GitHub en la ruta anterior y crear un venv propio. Instalar con ese Python:

```bash
python -m pip install -r requirements-certification.txt
python -m pip check
```

2. Crear `/var/lib/multiservices-certification/` y `media/`, propiedad `ecfcert`, permiso 700. Copiar `deploy/certification.env.example` a `/etc/multiservices-certification.env`. Completar los secretos con un editor; generar dos valores independientes de `python -c 'import secrets; print(secrets.token_urlsafe(64))'` para DJANGO_SECRET_KEY y ECF_AUTH_TOKEN_SECRET. El archivo de entorno y los archivos privados deben ser legibles únicamente por root/`ecfcert` (640 root:ecfcert o 600 ecfcert).

3. Tras transferir `certifica.p12` mediante Dropbox, ubicarlo en `/etc/multiservices-certification/`, fuera del repositorio y de cualquier raíz web; no publicar enlace de Dropbox ni guardar la contraseña en GitHub. El P12 sirve para **firmar**. También faltan las CA confiables para verificar los XML/semillas entrantes: obtenerlas del portal/canal oficial DGII y del proveedor correspondiente. Configurar ECF_TRUSTED_CA_PATH y ECF_AUTH_TRUSTED_CA_PATH con sus paquetes PEM/DER reales. No inventar una CA ni desactivar validación para pasar la prueba. No basta con mover el P12.

4. Ejecutar bajo `ecfcert`, dentro del checkout, con el venv nuevo y el archivo de entorno ya configurado:

```bash
export DJANGO_SETTINGS_MODULE=MultiServices.settings_certification
python manage.py check
python manage.py migrate --plan
python manage.py migrate products --noinput
python manage.py migrate --noinput
python manage.py check --deploy
python manage.py shell -c "from administration.models import Company; c, created = Company.objects.get_or_create(rnc='132018559', defaults={'name':'FERRETERIA SUPERAVIT SRL','address':'Calle Corazón de Jesús, esq. 12, El Almirante Caña, Sto. Dgo. Este','phoneNumber':'(849) 504-7281','email':'Eljoel_00@hotmail.com'}); assert c.name == 'FERRETERIA SUPERAVIT SRL'; print('Empresa receptora preparada')"
```

En una BD vacía se migra `products` primero: el historial antiguo de ventas tiene referencias a productos sin dependencia explícita. Se comprobó este orden sin modificar migraciones históricas. Esto crea solamente la empresa receptora en la BD **nueva**. No crear secuencias ni copiar registros de pruebas para recibir los documentos de DGII. Las migraciones necesitan poder escribir en el directorio SQLite. Los e-CF recibidos quedarán en esta instancia, no en la BD comercial.

5. Instalar el ejemplo systemd como servicio nuevo. Configurar DNS de `certificacion.sistemacenter.org` hacia el servidor, habilitar HTTPS con certificado público válido y usar `deploy/nginx-certification.conf.example` dentro del nuevo bloque TLS. El proxy conserva `/fe/...`, usa Host real y sobrescribe X-Forwarded-Proto. No publicar el puerto 8087; escuchar solamente en loopback.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now multiservices-certification
sudo nginx -t
# Recargar Nginx solo después de nginx -t satisfactorio.
sudo systemctl reload nginx
```

6. Validación desde el servidor (archivo de entorno accesible por ecfcert):

```bash
python scripts/check_receiver_deployment.py --base-url https://certificacion.sistemacenter.org --signed-auth
sudo journalctl -u multiservices-certification --since '10 minutes ago'
```

También repetir la comprobación desde otra conexión. La prueba pública crea/consume semillas, no envía facturas. Deben pasar firma->token, ambos casos de mayúsculas, ausencia de redirecciones y rechazo de XML ausente. Los acuses reales de DGII se verifican en pasos 8–11. Si falta la cadena CA, detenerse y conseguirla antes de iniciar recepción.

## Campos del paso 7

Si se utiliza el dominio propuesto, escribir **certificacion.sistemacenter.org** en los tres campos centrales; el portal agrega `https://` y los sufijos `/fe/...`. No conservar `/api/api/v1` en este despliegue aislado.

- GET `/fe/autenticacion/api/semilla`: XML `semillamodel` con valor/fecha.
- POST `/fe/autenticacion/api/validacioncertificado`: multipart `xml`, token/expira/expedido.
- POST `/fe/recepcion/api/ecf`: multipart `xml` y Bearer, ARECF firmado.
- POST `/fe/aprobacioncomercial/api/ecf`: multipart `xml` y Bearer, 200/400.

Confirmar URL solo tras comprobar el servidor real. No pulsar «Enviar prueba de comprobantes» hasta disponer de CA confiables y logs activos. No se ha confirmado ninguna URL con esta entrega.

## Operación y reversión

Antes de actualizar la instancia de pruebas, guardar copia consistente de su BD (SQLite backup API) y revisar `migrate --plan`. Para revertir, detener solamente `multiservices-certification` y restaurar su código/venv/BD compatibles; no deshacer migraciones sobre la BD comercial ni restaurar una copia antigua encima de ventas nuevas. No publicar `media`, certificados o `.env` mediante Nginx.

## Límites conocidos

El proyecto conserva Django 4.0.3 para evitar una migración mayor en esta entrega; requiere un trabajo separado de actualización. Las pruebas locales no acreditan DNS, TLS, firewall, reputación del dominio ni las cadenas de firma que enviará DGII. El despliegue aislado debe permanecer en cert incluso estando en el servidor Ubuntu público.

`check --deploy` avisa sobre HSTS de subdominios/preload; no se activan para no imponer políticas sobre otros subdominios existentes.

## React (opcional; no necesario para el paso 7)

`src/settings.js` acepta REACT_APP_API_URL y mantiene config.json como valor local. Para el despliegue comercial posterior: `REACT_APP_API_URL=https://sistemacenter.org/api/api/v1 npm run build`. No publicar un build que apunte a localhost ni conectar la UI de ventas al receptor aislado. Compilar no despliega nada; el personal conserva su frontend actual hasta que se publique deliberadamente.
