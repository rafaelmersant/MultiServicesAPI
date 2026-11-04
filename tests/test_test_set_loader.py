from pathlib import Path
import pytest

from ecf.test_set_loader import (
    load_test_set,
    certification_order,
)


EXCEL = (
    Path(__file__).resolve().parents[1]
    / "test_data"
    / "132018559-07102026102146.xlsx"
)


def test_dgii_download_has_expected_shape():

    if not EXCEL.is_file():
        pytest.skip("El Excel de certificación es un archivo local, excluido de GitHub.")

    summary = load_test_set(
        EXCEL
    )

    assert (
        len(summary.rfce_cases)
        == 4
    )

    assert (
        len(certification_order(summary))
        == 21
    )

    assert [case.tipo_ecf for case in certification_order(summary)] == (
        ["31"] * 4
        + ["32"] * 2
        + ["41"] * 2
        + ["43"] * 2
        + ["44"] * 2
        + ["45"] * 2
        + ["46"] * 2
        + ["47"] * 2
        + ["33"]
        + ["34"] * 2
    )

    assert summary.counts_by_type == {
        "33": 1,
        "32": 6,
        "34": 2,
        "31": 4,
        "41": 2,
        "43": 2,
        "44": 2,
        "45": 2,
        "46": 2,
        "47": 2,
    }
