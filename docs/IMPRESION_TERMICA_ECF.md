# Impresión térmica E31/E32

Actualizar backend y frontend; esta entrega no requiere migraciones ni paquetes
nuevos. Compilar/publicar React y reiniciar el Gunicorn del backend actualizado.

En una venta E31/E32 aceptada o aceptada condicional, pulsar el mismo icono de
impresora que las facturas tradicionales. Se prepara el contenido fiscal y se
abre el diálogo de impresión. El botón **PDF e-CF** sigue disponible.

Seleccionar la impresora y el mismo papel usado en la muestra de calibración,
escala **100%**, y desactivar encabezados/pies del navegador. El perfil aplica
internamente la ampliación 1.38 (un punto menos que el 139% comprobado) y agrega
2 mm de margen izquierdo sin volver a escalar manualmente. El contenido base
de 76 mm pasa a 104.88 mm; el contenedor reserva 108 mm para contenido y margen.
Este perfil debe utilizarse con un papel/controlador que admita ese ancho efectivo;
no es un perfil universal para rollos de 80 o 58 mm. El largo lo determina el
controlador. Validar la impresión física con el mismo papel de la calibración.

Los datos se obtienen de un endpoint autenticado y limitado a la empresa del
usuario. La plantilla usa razón social, dirección, e-NCF, fechas, comprador E31,
detalle y totales del XML firmado guardado. Comprueba el hash y la identidad del
registro; no sustituye datos firmados por cambios posteriores en el cliente o
la empresa. E32 omite el bloque de comprador del modelo ilustrativo utilizado.

El QR usa los mismos parámetros de la RI PDF y el ambiente del documento. Para
consumo menor de RD$250,000 se utiliza fc.dgii.gov.do; los demás, ecf.dgii.gov.do.
Se imprime centrado a 32 mm, con su margen blanco, y debajo **Código de Seguridad**
y **Fecha Firma**. No se añade «Valor a pagar», dirección del cliente ni columna
de descuento; los descuentos por línea se indican dentro del detalle.

El diseño sigue las secciones de representación impresa del
[Informe técnico DGII](https://dgii.gov.do/cicloContribuyente/facturacion/comprobantesFiscalesElectronicosE-CF/Documentacin%20sobre%20eCF/Informe%20y%20Descripci%C3%B3n%20T%C3%A9cnica/Informe%20T%C3%A9cnico%20e-CF%20v1.0.pdf).
No implica una nueva aprobación de diseño por parte de DGII.

Si falta aceptación, falla el contenido fiscal o no carga el QR, se bloquea la
impresión electrónica; no se sustituye por un ticket tradicional. No se vuelve
a firmar, enviar ni reservar numeración al imprimir. B01/B02 mantienen su plantilla.

Validar físicamente la primera impresión: texto completo, márgenes, tamaño y
lectura del QR con el teléfono, comparando resultado con la RI PDF. No se ha
probado un dispositivo físico desde este entorno.
