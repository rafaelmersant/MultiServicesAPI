from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ecf.test_run_registry import ECFTestRegistry


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Consulta y carga resultados históricos en el registro persistente de pruebas e-CF."
    )
    parser.add_argument(
        "--db",
        default="test_data/ecf/test_run_registry.sqlite3",
        help="Ruta de la base SQLite (por defecto dentro de test_data/ecf).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="Lista los casos registrados.")

    seed = sub.add_parser("seed-known", help="Registra los tres resultados ya conocidos de ECF31.")
    seed.add_argument("--rnc", default="132018559")

    args = parser.parse_args()
    registry = ECFTestRegistry(args.db)

    if args.command == "seed-known":
        rnc = args.rnc
        records = [
            dict(
                rnc=rnc, encf="E310000000001",
                case_id="132018559E310000000001", tipo_ecf="31",
                status="accepted", dgii_code=1, dgii_status="Aceptado",
                track_id=None, sequence_used=None,
                notes="Resultado histórico conocido; TrackId/hash del XML no importados.",
            ),
            dict(
                rnc=rnc, encf="E310000000003",
                case_id="132018559E310000000003", tipo_ecf="31",
                status="accepted_conditional", dgii_code=4,
                dgii_status="Aceptado Condicional",
                track_id="f0673b51-3f9f-4f03-8c05-35b25a4af7ff",
                sequence_used=True,
                notes="Histórico: mensajes DGII 11094 para impuestos adicionales 002 y 004.",
            ),
            dict(
                rnc=rnc, encf="E310000000007",
                case_id="132018559E310000000007", tipo_ecf="31",
                status="accepted", dgii_code=1, dgii_status="Aceptado",
                track_id="0868e251-3e96-419f-9899-9814dc003b49",
                sequence_used=True,
                notes="Aceptado por DGII el 2026-10-10.",
            ),
        ]
        for item in records:
            record = registry.record_historical(**item)
            print(f"{record.encf}: {record.status} (registrado)")
        print(f"Base de datos: {Path(args.db).resolve()}")
        return 0

    for record in registry.list_records():
        print(json.dumps(record.__dict__, ensure_ascii=False, default=str))
    print(f"Base de datos: {Path(args.db).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
