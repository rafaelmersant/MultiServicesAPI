from pathlib import Path

import pytest
from lxml import etree

from ecf.test_set_loader import load_test_set
from ecf.xml_builder import build_ecf_xml


def test_all_ecf_cases_build_and_validate_before_signing():
    excel = Path("test_data/132018559-07102026102146.xlsx")
    xsd_dir = Path("xsd")
    if not excel.exists() or not xsd_dir.exists():
        pytest.skip("Configura el Excel en test_data/ y los XSD oficiales en xsd/.")

    summary = load_test_set(excel)
    assert len(summary.ecf_cases) == 25

    for case in summary.ecf_cases:
        xsd_path = xsd_dir / f"ECF{case.tipo_ecf}V1.0.xsd"
        xml = build_ecf_xml(case, xsd_path, validate=True)
        root = etree.fromstring(xml)

        assert root.tag == "ECF"
        assert root.xpath("string(.//*[local-name()='RNCEmisor'])") == "132018559"
        assert root.xpath("string(.//*[local-name()='eNCF'])") == case.encf


def test_first_case_preserves_excel_line_values():
    excel = Path("test_data/132018559-07102026102146.xlsx")
    xsd_dir = Path("xsd")
    if not excel.exists() or not xsd_dir.exists():
        pytest.skip("Configura el Excel en test_data/ y los XSD oficiales en xsd/.")

    summary = load_test_set(excel)
    case = next(c for c in summary.ecf_cases if c.case_id == "132018559E310000000001")
    xml = build_ecf_xml(case, xsd_dir / "ECF31V1.0.xsd")
    root = etree.fromstring(xml)

    assert root.xpath("string(.//*[local-name()='NumeroLinea'])") == "1"
    assert root.xpath("string(.//*[local-name()='NombreItem'])") == "ASW DTU"
    assert root.xpath("string(.//*[local-name()='MontoTotal'])") == "7080.00"
