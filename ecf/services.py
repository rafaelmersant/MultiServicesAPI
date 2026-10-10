from pathlib import Path

from .models import (
    TestCase,
    TestSetSummary,
)

from .test_set_loader import (
    certification_order,
    load_test_set,
    export_inventory,
)


def prepare_day1_inventory(
    excel_path: str | Path
) -> tuple[
    TestSetSummary,
    list[dict],
]:

    """
    Lee el Excel de DGII y prepara
    el inventario de pruebas.

    NO realiza ninguna llamada a DGII.
    """

    summary = load_test_set(
        excel_path
    )

    inventory = export_inventory(
        summary
    )

    return summary, inventory


def get_primary_cases(
    summary: TestSetSummary
) -> list[TestCase]:

    return certification_order(
        summary
    )