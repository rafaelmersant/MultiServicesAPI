from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ecf.test_run_registry import ECFTestRegistry
from ecf.test_set_loader import certification_order, load_test_set


DEFAULT_EXCEL = "test_data/132018559-07102026102146.xlsx"
DEFAULT_REGISTRY_DB = "test_data/ecf/test_run_registry_cert.sqlite3"


def resolve_project_path(value: str) -> Path:
    """Resolve relative paths from the project root."""
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def print_case(case, registry: ECFTestRegistry, tipo_ecf: str) -> bool:
    """Print the local status for a test case; return whether it is registered."""
    # In this test set, CasoPrueba starts with the 9-digit issuer RNC.
    rnc = case.case_id[:9]
    record = registry.get(rnc, case.encf)

    if record:
        status = record.status
        dgii_status = record.dgii_status or "-"
        code = record.dgii_code if record.dgii_code is not None else "-"
        sequence = (
            "Sí" if record.sequence_used is True
            else "No" if record.sequence_used is False
            else "-"
        )
        print(
            f"{case.case_id} | {tipo_ecf} | {case.encf} | "
            f"{status} | DGII={dgii_status} | "
            f"código={code} | secuencia={sequence}"
        )
        return True

    print(f"{case.case_id} | {tipo_ecf} | {case.encf} | PENDIENTE DE REGISTRO")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audita los casos del Excel contra un registro SQLite local. "
            "No envía documentos ni consulta DGII."
        )
    )
    parser.add_argument(
        "--excel",
        default=DEFAULT_EXCEL,
        help="Ruta al Excel oficial del conjunto de pruebas.",
    )
    parser.add_argument(
        "--registry-db",
        default=DEFAULT_REGISTRY_DB,
        help=(
            "Ruta de la base SQLite. Por defecto usa el registro independiente "
            "de certificación, sin modificar el registro histórico."
        ),
    )
    args = parser.parse_args()

    excel_path = resolve_project_path(args.excel)
    registry_path = resolve_project_path(args.registry_db)

    if not excel_path.is_file():
        print(f"ERROR: no existe el Excel: {excel_path}")
        return 1
    if not registry_path.is_file():
        print(
            "ERROR: no existe el registro SQLite indicado: "
            f"{registry_path}\n"
            "No se creó ningún registro. Inicialízalo explícitamente antes de auditar."
        )
        return 1

    summary = load_test_set(excel_path)
    registry = ECFTestRegistry(registry_path)

    # The 21 main ECF cases exclude the four E32 cases sent as RFCE.
    primary_cases = certification_order(summary)

    print(f"Excel: {excel_path}")
    print(f"Registro local: {registry_path}")
    print("NOTA: esta auditoría solo consulta SQLite; no confirma el estado real en DGII.\n")

    print("=== ECF PRINCIPALES ===")
    print("Caso | Tipo | e-NCF | Estado local | Resultado DGII")

    registered_ecf = 0
    pending_ecf = []
    for case in primary_cases:
        if print_case(case, registry, case.tipo_ecf):
            registered_ecf += 1
        else:
            pending_ecf.append(case)

    print("\n=== RFCE ===")
    registered_rfce = 0
    pending_rfce = []
    for case in summary.rfce_cases:
        if print_case(case, registry, "RFCE-32"):
            registered_rfce += 1
        else:
            pending_rfce.append(case)

    print("\n=== RESUMEN ===")
    print(f"ECF principales registrados: {registered_ecf}/{len(primary_cases)}")
    print(f"ECF principales pendientes: {len(pending_ecf)}")
    print(f"RFCE registrados: {registered_rfce}/{len(summary.rfce_cases)}")
    print(f"RFCE pendientes: {len(pending_rfce)}")

    print("\n=== SIGUIENTE CASO ECF A REVISAR ===")
    if pending_ecf:
        case = pending_ecf[0]
        print(f"Caso: {case.case_id}")
        print(f"Tipo e-CF: {case.tipo_ecf}")
        print(f"e-NCF: {case.encf}")
        print(
            "Este caso no aparece en el registro local. Antes de enviarlo, "
            "confirma que no se haya enviado ya a DGII por otro medio y que "
            "su XML esté preparado y validado."
        )
    else:
        print("No quedan casos ECF principales sin registrar en este SQLite.")

    if pending_rfce:
        case = pending_rfce[0]
        print("\n=== SIGUIENTE RFCE A REVISAR ===")
        print(f"Caso: {case.case_id} | e-NCF: {case.encf}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
