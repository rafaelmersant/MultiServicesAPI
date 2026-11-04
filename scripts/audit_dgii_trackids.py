"""Read-only reconciliation of saved e-CF TrackIds against DGII."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

from ecf.certificate import load_pkcs12
from ecf.config import Settings
from ecf.dgii_auth import DGIIAuthenticator
from ecf.dgii_reception import DGIIReceptionClient
from ecf.test_run_registry import ECFTestRegistry


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Consulta TrackIds guardados; no envía ni modifica comprobantes."
    )
    parser.add_argument(
        "--registry-db",
        default="test_data/ecf/test_run_registry_cert.sqlite3",
        help="Registro local de envíos e-CF con TrackIds.",
    )
    args = parser.parse_args()

    registry_path = Path(args.registry_db)
    if not registry_path.is_absolute():
        registry_path = PROJECT_ROOT / registry_path
    if not registry_path.is_file():
        parser.error(f"No existe el registro local: {registry_path}")

    load_dotenv(PROJECT_ROOT / ".env", override=False)
    settings = Settings.from_env()
    if settings.environment != "cert":
        parser.error("La auditoría exige DGII_ENVIRONMENT=cert; no se consultará otro ambiente.")

    certificate = load_pkcs12(settings.certificate_path, settings.certificate_password)
    token = DGIIAuthenticator(settings=settings, certificate=certificate).authenticate().token
    client = DGIIReceptionClient(
        reception_base_url=settings.reception_base_url,
        result_base_url=settings.result_base_url,
        timeout_seconds=settings.request_timeout_seconds,
    )

    records = [record for record in ECFTestRegistry(registry_path).list_records() if record.track_id]
    if not records:
        print("El registro no contiene TrackIds para consultar.")
        return 0

    mismatches = 0
    for record in records:
        try:
            result = client.get_result(record.track_id, token)
        except Exception as exc:  # Keep checking the other independent TrackIds.
            mismatches += 1
            print(f"ERROR | {record.encf} | {type(exc).__name__}: {exc}")
            continue

        identity_matches = (not result.rnc or result.rnc == record.rnc) and (
            not result.encf or result.encf == record.encf
        )
        state_matches = result.code == record.dgii_code and result.status == record.dgii_status
        if not identity_matches or not state_matches:
            mismatches += 1
        verdict = "COINCIDE" if identity_matches and state_matches else "DIFERENCIA"
        print(
            f"{verdict} | {record.case_id or record.encf} | "
            f"local={record.dgii_status}/{record.dgii_code} | "
            f"DGII={result.status}/{result.code} | "
            f"RNC/e-NCF={'OK' if identity_matches else 'NO COINCIDE'}"
        )

    print(f"Consultas: {len(records)}; diferencias/errores: {mismatches}")
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
