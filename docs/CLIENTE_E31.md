# Identificación del cliente al facturar E31

Actualizar backend y frontend. Se añade la dependencia `python-stdnum`:

```bash
python3.10 -m pip install -r requirements.txt
python3.10 manage.py check
```

Reiniciar el Gunicorn correspondiente y publicar la nueva compilación React.
Esta entrega no requiere migraciones.

Al seleccionar E31 y un cliente, se leen los campos existentes
`identificationType` (C/R) e `identification`. Se muestra un bloque para completar
o corregirlos sin salir de la factura. El botón Guardar identificación actualiza
solo esos dos campos del cliente de la misma empresa. Al guardar la factura,
también se valida y guarda lo digitado, aunque no se haya pulsado ese botón.
Los cambios no se guardan mientras se escribe ni cuando el número es inválido.

Se aceptan espacios y guiones, se normaliza a dígitos sin perder ceros iniciales
y se comprueban longitud y dígito verificador. C exige cédula de 11 dígitos;
R admite RNC de 9 dígitos o identificación de persona física de 11. Se utilizan
los validadores y excepciones históricas de
[python-stdnum](https://github.com/arthurdejong/python-stdnum/tree/master/stdnum/do).

Esta validación es **local de formato y dígito verificador**, no una consulta al
padrón DGII ni confirmación de inscripción/estatus activo o de correspondencia
del nombre con el número. La interfaz no la presenta como verificación oficial.

Los clientes genéricos compartidos no admiten asignar una identificación
particular en este flujo: seleccionar o crear el cliente real con la búsqueda
y el formulario de clientes existentes. No se inventan números ni se reasigna
el RNC de la empresa emisora al comprador.

El backend repite la validación para E31 productivos al convertir la venta,
antes de reservar el número, tanto desde Caja como desde el flujo manual.
Los modelos ilustrativos y casos de certificación no se someten a este nuevo
filtro productivo. Los campos históricos y flujos B01/B02/E32 se conservan.
