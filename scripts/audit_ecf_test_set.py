
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ecf.test_run_registry import ECFTestRegistry
from ecf.test_set_loader import certification_order, load_test_set


DEFAULT_EXCEL = "test_data/132018559-07102026102146.xlsx"


def print_case(case, registry, tipo_ecf: str) -> bool:
    """
    Imprime el estado de un caso.
    Devuelve True si ya existe en el registro.
    """
    # En este conjunto, CasoPrueba comienza con el RNC de 9 dígitos.
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

    print(
        f"{case.case_id} | {tipo_ecf} | {case.encf} | "
        "PENDIENTE DE REGISTRO"
    )
    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audita los casos del Excel de DGII contra el registro SQLite. "
            "No envía documentos."
        )
    )
    parser.add_argument(
        "--excel",
        default=DEFAULT_EXCEL,
        help="Ruta al Excel oficial del conjunto de pruebas.",
    )
    args = parser.parse_args()

    excel_path = Path(args.excel)
    if not excel_path.is_file():
        print(f"ERROR: no existe el Excel: {excel_path}")
        return 1

    summary = load_test_set(excel_path)
    registry = ECFTestRegistry()

    # Los 21 casos principales, excluyendo los cuatro E32
    # que se procesan mediante RFCE en este conjunto.
    primary_cases = certification_order(summary)

    print("\n=== ECF PRINCIPALES ===")
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
    print(f"ECF principales registrados: {registered_eccf(registered_ecf)}")
    print(f"ECF principales pendientes: {len(pending_ecf)}")
    print(f"RFCE registrados: {registered_rfce}/4")
    print(f"RFCE pendientes: {len(pending_rfce)}")

    print("\n=== SIGUIENTE CASO ECF A REVISAR ===")
    if pending_ecf:
        case = pending_ecf[0]
        print(f"Caso: {case.case_id}")
        print(f"Tipo e-CF: {case.tipo_ecf}")
        print(f"e-NCF: {case.encf}")
        print(
            "Este caso no aparece en SQLite. Antes de enviarlo, "
            "confirma que no se haya enviado por otro medio y que "
            "su XML firmado esté preparado."
        )
    else:
        print("No quedan casos ECF principales sin registrar.")

    return 0


def registered_eccf(count: int) -> str:
    return f"{count}/21"


if __name__ == "__main__":
    raise SystemExit(main())