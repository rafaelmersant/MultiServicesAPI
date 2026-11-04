from pathlib import Path
from typing import Any

import openpyxl

from .exceptions import TestSetError
from .test_models import (
    TestCase,
    TestSetSummary,
)


EMPTY_MARKERS = {
    None,
    "",
    "#e",
}

CERTIFICATION_SEND_ORDER = ("31", "32", "41", "43", "44", "45", "46", "47", "33", "34")
CERTIFICATION_EXPECTED_COUNTS = {
    "31": 4,
    "32": 2,
    "41": 2,
    "43": 2,
    "44": 2,
    "45": 2,
    "46": 2,
    "47": 2,
    "33": 1,
    "34": 2,
}


def _normalize(value: Any) -> Any:

    if value in EMPTY_MARKERS:
        return None

    if (
        isinstance(value, float)
        and value.is_integer()
    ):
        return str(int(value))

    return value


def _read_sheet(ws) -> list[TestCase]:

    headers = [
        ws.cell(1, c).value
        for c in range(
            1,
            ws.max_column + 1
        )
    ]

    if (
        not headers
        or headers[0] != "CasoPrueba"
    ):
        raise TestSetError(
            f"La hoja {ws.title} "
            "no tiene el encabezado "
            "esperado CasoPrueba."
        )

    cases: list[TestCase] = []

    for row_number in range(
        2,
        ws.max_row + 1
    ):

        case_id = _normalize(
            ws.cell(
                row_number,
                1
            ).value
        )

        if not case_id:
            continue

        values: dict[str, Any] = {}

        for col, header in enumerate(
            headers,
            1
        ):

            if not header:
                continue

            values[str(header)] = _normalize(
                ws.cell(
                    row_number,
                    col
                ).value
            )

        tipo = str(
            values.get("TipoeCF") or ""
        )

        encf = str(
            values.get("ENCF") or ""
        )

        version = str(
            values.get("Version") or ""
        )

        cases.append(
            TestCase(
                case_id=str(case_id),
                version=version,
                tipo_ecf=tipo,
                encf=encf,
                values=values,
            )
        )

    return cases


def load_test_set(
    path: str | Path
) -> TestSetSummary:

    path = Path(path)

    if not path.exists():
        raise TestSetError(
            f"No existe el archivo: {path}"
        )

    if path.suffix.lower() not in {
        ".xlsx",
        ".xlsm",
    }:
        raise TestSetError(
            "El set de DGII debe ser "
            "un archivo Excel .xlsx/.xlsm."
        )

    # Para este archivo DGII en particular
    # usamos el modo normal de openpyxl.
    # El workbook tiene muchas columnas
    # estructurales/repetitivas.
    wb = openpyxl.load_workbook(
        path,
        data_only=True,
        read_only=False,
    )

    try:

        if (
            "ECF" not in wb.sheetnames
            or "RFCE" not in wb.sheetnames
        ):
            raise TestSetError(
                "El Excel debe contener "
                "las hojas ECF y RFCE."
            )

        ecf = _read_sheet(
            wb["ECF"]
        )

        rfce = _read_sheet(
            wb["RFCE"]
        )

    finally:

        wb.close()

    if len(ecf) != 25:

        raise TestSetError(
            "Se esperaban 25 filas en ECF; "
            f"se encontraron {len(ecf)}."
        )

    if len(rfce) != 4:

        raise TestSetError(
            "Se esperaban 4 filas en RFCE; "
            f"se encontraron {len(rfce)}."
        )

    # Los cuatro casos E32 de consumo
    # menor a RD$250,000 presentes en
    # tu set.
    special_32 = {
        "132018559E320000000012",
        "132018559E320000000013",
        "132018559E320000000014",
        "132018559E320000000015",
    }

    primary = [
        c
        for c in ecf
        if c.case_id not in special_32
    ]

    type32_special = [
        c
        for c in ecf
        if c.case_id in special_32
    ]

    if (
        len(primary) != 21
        or len(type32_special) != 4
    ):
        raise TestSetError(
            "Composición inesperada del "
            "set de pruebas."
        )

    return TestSetSummary(
        ecf_cases=primary + type32_special,
        rfce_cases=rfce,
    )


def certification_order(
    summary: TestSetSummary
) -> list[TestCase]:

    """
    Devuelve los 21 casos principales
    en el orden de envío publicado por DGII.

    Primero:
        31
        32 de DOP 250,000 o más
        41
        43
        44
        45
        46
        47
    Después:
        33
        34

    Los E32 menores de DOP 250,000 y sus RFCE se procesan en una etapa
    posterior, según indique el portal de certificación.
    """

    special_32 = {
        "132018559E320000000012",
        "132018559E320000000013",
        "132018559E320000000014",
        "132018559E320000000015",
    }

    primary = [
        c
        for c in summary.ecf_cases
        if c.case_id not in special_32
    ]

    order = {
        "31": 0,
        "32": 1,
        "41": 2,
        "43": 3,
        "44": 4,
        "45": 5,
        "46": 6,
        "47": 7,
        "33": 8,
        "34": 9,
    }

    return sorted(
        primary,
        key=lambda c: (
            order.get(c.tipo_ecf, len(order)),
            c.case_id,
        ),
    )


def export_inventory(
    summary: TestSetSummary
) -> list[dict[str, Any]]:

    inventory = []

    for case in summary.ecf_cases:

        inventory.append({
            "case_id": case.case_id,
            "tipo_ecf": case.tipo_ecf,
            "encf": case.encf,
            "version": case.version,
        })

    for case in summary.rfce_cases:

        inventory.append({
            "case_id": case.case_id,
            "tipo_ecf": "RFCE-32",
            "encf": case.encf,
            "version": case.version,
        })

    return inventory
