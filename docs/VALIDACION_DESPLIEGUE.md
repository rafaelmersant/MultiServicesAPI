# Estado de validación

La validación del 03/11/2026 se conserva como referencia: 61 pruebas aprobadas,
Django sin errores, lista de facturas HTTP 200 y React compilado. En una copia
SQLite se reaplicaron las migraciones e-CF y las 20 tablas tradicionales
conservaron exactamente sus datos.

El 05/11/2026 se retiraron, por petición del usuario, settings/URLs aislados,
plantillas systemd/Nginx y requirements separados. Se usa únicamente
MultiServices.settings, con /api/v1/ y /fe/. La guía actual es
DESPLIEGUE_CERTIFICACION.md.

Pendiente: validar la copia Ubuntu real, su proxy HTTPS, certificado y CA
confiables; no se ha desplegado ni confirmado ninguna URL desde aquí.
Los avisos previos son USE_L10N, fechas sin zona en filtros de ventas y lint
React. No se modificaron flujos tradicionales para corregir esos avisos.

Los archivos oficiales de test_data no se publican: pruebas dependientes se
omiten cuando no están disponibles. pytest.ini evita ejecutar testupload.py,
que importa productos al cargarse. No subir secretos, bases o archivos de
certificación. El backup histórico ya seguido por Git en backups/dgii_day5/
no se excluye retroactivamente por .gitignore.
