# E31/E32 desde la factura habitual

## Despliegue

Actualizar backend y frontend; aplicar la nueva migración antes de reiniciar:

```bash
python3.10 manage.py migrate --noinput
python3.10 manage.py check
```

Debe quedar aplicada `ecf.0010_checkout_claim`. No cambian requirements ni la
configuración fiscal productiva existente. Publicar la nueva compilación React.
Si Gunicorn usa el timeout predeterminado de 30 segundos, dar margen al proceso
de autenticación/envío/consulta, por ejemplo `--timeout 120` en su configuración
actual. Reiniciar solo el servicio correspondiente, conservando puerto y rutas.
El timeout del proxy debe permitir la misma duración. Un timeout no autoriza
repetir la venta ni enviar otro número.

## Uso normal

1. En NCF elegir **E31** o **E32**, junto a No usar/B01/B02.
2. Registrar cliente, vendedor y productos como siempre. E31 requiere RNC/cédula
   real del comprador. Si hay líneas sin ITBIS, indicar tratamiento real; en
   ventas a crédito indicar fecha límite de pago.
3. Pulsar **Guardar**. Se guarda la venta y sus líneas/inventario, se crea su
   registro e-CF, se reserva un número del rango productivo y se genera/firma XML.
4. El sistema envía E31 y E32 de RD$250,000 o más por recepción e-CF y consulta
   una vez su estado. Consumo menor de RD$250,000 utiliza RFCE.
5. Se abre la venta guardada con el resultado. Si está aceptado o aceptado
   condicional, queda el número vinculado y el botón **PDF e-CF** disponible.
   No se imprime el ticket tradicional como representación fiscal electrónica.

No hay intervención sobre contadores B01/B02 para una selección electrónica.
No usar cambia únicamente en que evita consultar una secuencia innecesaria.
Tarjeta y transferencia se reconocen como operaciones al contado; crédito sigue
siendo a crédito. Operaciones con puntos o situaciones fiscales no clasificables
se detienen para revisión, sin inventar tratamiento fiscal.

## Si queda pendiente

La factura ya existe. El aviso enlaza **Facturación e-CF** y no regresa a un
formulario nuevo que pudiera inducir a volver a guardarla. El estado se vuelve
a leer al abrir esa venta. Continuar con su mismo registro y número:

- Sin rango o con datos por revisar: corregir los datos/ajustes reales y utilizar
  el flujo de reserva, XML, firma y envío cuando corresponda.
- Con TrackId en proceso: **Consultar**, sin volver a emitir.
- RFCE incierto, envío incierto o rechazado: revisar respuesta y conciliar antes
  de actuar. No se reenvían automáticamente documentos con resultado incierto.
- Si se aceptó pero falló el PDF, generar la RI desde ese mismo registro.
- Si falló la comunicación antes de crear el registro e-CF, la venta guardada
  puede seleccionarse como factura fuente; no crear otra venta.

Admin/Owner conservan administración de rangos. Caja puede ejecutar el proceso
automático y continuar acciones manuales únicamente sobre E31/E32 productivos
vinculados a ventas de su empresa. No puede crear rangos ni modificar otros tipos.
Cerrar sesión y entrar de nuevo si la sesión no dispone de token e-CF.

El procesamiento tiene una exclusión por registro para impedir ejecuciones
automáticas simultáneas. Si un worker muere, el intento automático permanece
bloqueado para ese registro; revisar su estado mediante el flujo manual, no
resetear el indicador a ciegas. Los registros de transporte mantienen además
su protección contra envíos repetidos.

Se valida con datos sintéticos y dobles de los servicios DGII; esta entrega no
envía facturas reales como prueba ni modifica rangos productivos.
