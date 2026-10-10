import argparse
import json
from pathlib import Path

from ecf.logging_config import (
    configure_logging
)

from ecf.services import (
    prepare_day1_inventory,
    get_primary_cases,
)


def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "Inspecciona el set de "
            "pruebas DGII sin enviar nada."
        )
    )

    parser.add_argument(
        "excel",
        type=Path,
    )

    args = parser.parse_args()

    configure_logging()

    summary, inventory = (
        prepare_day1_inventory(
            args.excel
        )
    )

    print(
        f"Total filas: {summary.total}"
    )

    print(
        f"ECF: {len(summary.ecf_cases)}"
        f" | RFCE: "
        f"{len(summary.rfce_cases)}"
    )

    print(
        "Conteo e-CF:",
        summary.counts_by_type,
    )

    print(
        "\nOrden de prueba para "
        "los 21 e-CF principales:"
    )

    for i, case in enumerate(
        get_primary_cases(summary),
        1,
    ):

        print(
            f"{i:02d}. "
            f"{case.tipo_ecf} | "
            f"{case.encf} | "
            f"{case.case_id}"
        )

    Path(
        "test_set_inventory.json"
    ).write_text(
        json.dumps(
            inventory,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        "\nInventario guardado en "
        "test_set_inventory.json"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )