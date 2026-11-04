# Validación local — 03/11/2026

- Python del venvms, 3.10; Django 4.0.3.
- 61 pruebas aprobadas: XML/XSD, firma/cadena de prueba, semilla/token, recepción/acuse, orden de certificación, PDF, serialización, rutas y regresión de reverse().
- `manage.py check`: correcto. `makemigrations --check --dry-run`: sin diferencias.
- GET original `/api/v1/invoicesHeaders/` con compañía 14, filtros 03/11/2026, orden/paginación: HTTP 200, sin escrituras.
- Migraciones e-CF 0001–0008 eliminadas/reaplicadas únicamente en una copia SQLite: hashes y filas de las 20 tablas tradicionales iguales antes/después.
- BD nueva de certificación: `migrate products`, luego `migrate`, correcto. Configuración aislada: DEBUG false, HTTPS y únicamente rutas receptoras.
- Dependencias finales de `requirements-certification.txt`: resolución pip satisfactoria sin instalación. `pip check` del venv: correcto. Gunicorn/Linux no se ejecuta en este Windows.
- React: build satisfactorio con REACT_APP_API_URL=https://sistemacenter.org/api/api/v1. Advertencias previas de hooks/variables sin uso y Browserslist antiguo; no se corrigieron flujos ajenos a e-CF.
- `git diff --check`: correcto (aviso local LF/CRLF).

Avisos: USE_L10N obsoleto; filtros de ventas usan fechas sin zona; HSTS subdominios/preload no activados deliberadamente. No alteran estos resultados.

Pendiente obligatorio: DNS/TLS/Nginx/systemd en Ubuntu; migrar BD aislada, registrar empresa, instalar P12 y CA confiables reales; validar semilla firmada->token y posteriormente los documentos reales de DGII. No se ha desplegado ni confirmado URL. No se garantiza todavía la recepción de la cadena real DGII: no se dispone localmente de sus CA.

Git: `.gitignore` protege nuevos artefactos, pero no elimina los ya versionados. Existe un backup histórico seguido por Git en `backups/dgii_day5/test_run_registry_day5.sqlite3`: excluirlo del checkout de despliegue; si se desea retirarlo de futuras versiones, `git rm --cached -- backups/dgii_day5/test_run_registry_day5.sqlite3` conserva la copia local. No se ha modificado el índice ni hecho commit/push.

Repetir: instalar pytest con requirements-day1.txt y ejecutar `python -m pytest -q`. Los archivos oficiales de test_data no están en GitHub; las pruebas que los requieren se omiten explícitamente si faltan. pytest.ini evita importar el script histórico testupload.py, que carga productos al importarse.
