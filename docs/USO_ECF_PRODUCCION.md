# Preparación y operación e-CF en producción

## Estado de esta entrega

Se habilitan borradores productivos, reserva controlada, construcción/validación
XSD, firma, envío y consulta DGII, RFCE y representación PDF. No se cargaron rangos
ni se asignaron e-NCF en la BD de trabajo; no se enviaron documentos fiscales.
La prueba definitiva en producción queda pendiente hasta obtener los rangos.

## Desplegar antes de usar

Actualizar backend y frontend desde sus respectivos repositorios. Con el venv
de producción activado y respaldo consistente previo de la BD:

```bash
python -m pip install -r requirements.txt
python -m pip check
python manage.py check
python manage.py migrate --plan
python manage.py migrate --noinput
python manage.py showmigrations ecf
```

Debe aparecer aplicada `0009_production_issuance`. Esta migración modifica solo
tablas e-CF: referencia de autorización, almacenamiento de diez dígitos, rangos
sucesivos e identificación única por empresa/ambiente/e-NCF. No sustituye las
tablas de NCF tradicionales ni importa datos. Reiniciar únicamente el Gunicorn
de producción y publicar la compilación React con su URL productiva existente.
No hace falta una dependencia nueva ni un settings Django paralelo para esta entrega.
El venv y settings deben conservar los agregados indicados en DESPLIEGUE_PRODUCCION.md.

Mantener `.env` con DGII_ENVIRONMENT=prod, ECF_EXPECTED_TAX_ID=132018559,
P12/clave y CA productivas válidas. No copiar el pin del certificado TEST.
Verificar en la empresa RNC, razón social **FERRETERIA SUPERAVIT SRL** y dirección
reales; el XML y PDF usan esa identidad registrada, no el nombre comercial del logo.

## Qué puedes hacer sin rangos

En **Facturación e-CF**, seleccionar Producción y crear borradores. Estos no
constituyen comprobantes fiscales y no deben entregarse como facturas fiscales.
Si no existe rango vigente, aparece **Pendiente de rango autorizado** y Reservar
queda deshabilitado. El backend aplica el mismo bloqueo aunque se llame al API.
La firma y envío productivos requieren un número dentro de un rango registrado.

Cerrar sesión y entrar nuevamente después del despliegue si falta el token.
Admin/Owner administran rangos, preparan y envían comprobantes. Otros usuarios
autenticados pueden leer e imprimir la RI de ventas de su propia empresa.
Los endpoints tradicionales mantienen sus permisos anteriores.

## Al recibir autorización de secuencias

Registrar tipo, ambiente Producción, inicio, fin, vencimiento si aplica y
referencia real de autorización DGII. No usar el rango genérico del set de pruebas.
Los rangos no pueden solaparse. Un rango agotado o vencido no asigna números;
se puede registrar el siguiente rango autorizado conservando el anterior.
Nunca modificar el contador ni borrar registros para recuperar numeración.

## Primera venta E31/E32

1. En la factura habitual, seleccionar NCF **No usar**, guardar sus líneas y
   comprobar los totales reales. Esto evita consumir B01/B02 y luego duplicar
   el comprobante. Mientras se esperan los rangos, continuar usando el flujo
   tradicional habitual para las ventas que requieran comprobante fiscal.
2. En Facturación e-CF seleccionar esa venta sin NCF, Producción y E31 o E32.
   Una venta que ya tiene NCF tradicional no se puede convertir.
3. Especificar tratamiento de líneas sin ITBIS cuando existan: tasa 0% o exentas.
   Para una mezcla, indicar cada `IndicadorFacturacion[n]` en los ajustes JSON.
   Los indicadores por línea prevalecen sobre la selección general.
4. Crear borrador. Si se requieren ajustes, completar el objeto JSON y pulsar
   **Aplicar ajustes fiscales** en ese borrador antes de reservar. El objeto
   reemplaza sus ajustes anteriores. El tipo de ingreso admite `TipoIngresos`
   (por defecto 01); completar datos fiscales aplicables a la operación real.
5. **Reservar → XML → Firmar**. La reserva para ventas E31/E32 comprueba la
   conversión de importes antes de consumir número. Descuentos se toman como
   importe total de línea, igual que el sistema existente. No se recalculan
   ni sobrescriben importes de la venta. Diferencias de impuesto/total detienen
   el flujo. Cantidades requieren máximo dos decimales según el XSD utilizado.
6. E31 y E32 de RD$250,000 o más: **Enviar e-CF → Consultar** hasta resultado
   definitivo. E32 menor de RD$250,000: **Crear RFCE → Firmar RFCE → Enviar RFCE**.
   En producción, su respuesta real determina el estado; no se acepta una
   confirmación manual ni una carga al portal de certificación.
7. Tras aceptación o aceptación condicional, generar/descargar el PDF RI y
   descargar el XML firmado para entregarlos al receptor según corresponda.
   La entrega automatizada al servicio de cada comprador no forma parte de
   esta pantalla; el XML y PDF se pueden entregar por el canal acordado.

Solo tras aceptación se vincula el e-NCF al campo NCF de la venta existente,
para que aparezca en listados/exportaciones que usan ese campo. No se sobrescribe
un NCF distinto. Comprobar los reportes fiscales y su clasificación antes del
primer cierre productivo; no se ha rediseñado el exportador 607 en esta entrega.
La impresión de esa venta ofrece **PDF e-CF**, usando los datos firmados y QR;
no utiliza el ticket tradicional como representación fiscal electrónica.
Esta integración entrega la RI en PDF, no un nuevo diseño de ticket térmico.

## Otros tipos, correcciones e incidencias

E33/E34 y E41–E47 conservan la preparación mediante datos fiscales JSON completos
y su XSD; no son conversiones automáticas de una venta E31/E32. Las notas requieren
referencia real de la empresa: e-CF productivo aceptado o NCF tradicional registrado.
El flujo habitual de ventas queda separado de esas operaciones especiales.

Desde la reserva se protegen encabezado/detalle contra edición, borrado o
anulación tradicional. Cobro (`paid`) e impresión (`printed`) siguen permitidos.
Las correcciones fiscales requieren el procedimiento e-CF aplicable; no borrar
la venta ni editar el XML firmado. No se implementa reenvío automático de rechazos.
Un resultado incierto requiere conciliación; no se deben emitir números nuevos
ni marcar aceptación manual para resolverlo. Respaldar la BD, MEDIA_ROOT y
`private_ecf_state` de la raíz del backend: allí se guardan los registros de
transporte productivo separados de certificación y fuera del directorio público.
Opcionalmente configurar ECF_PRODUCTION_REGISTRY_DIR como una ruta absoluta privada
y persistente, escribible por Gunicorn; no exponer esa carpeta mediante Nginx.

## Verificación realizada

- 104 pruebas automatizadas aprobadas; Django check sin errores y sin migraciones
  de modelos pendientes de generar.
- Migración y reservas comprobadas sobre una copia SQLite desechable: 20 tablas
  tradicionales conservaron sus datos; se verificaron agotamiento, diez dígitos,
  rechazo de duplicados y separación entre producción/certificación.
- React compilado; advertencias preexistentes de hooks/variables sin usar y
  Browserslist. No se realizó una emisión fiscal productiva ni prueba de impresora.

Antes de abrir al personal: aplicar migración, validar sesión, consultar una venta
tradicional y su impresión, preparar un borrador sin rango y comprobar el bloqueo.
La primera emisión real y sus reportes se validan cuando DGII entregue los rangos.
