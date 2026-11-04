from pathlib import Path

from lxml import etree

from ecf.test_set_loader import load_test_set
from ecf.xml_builder import build_ecf_xml


def test_case_310000000003_includes_item_level_additional_tax_codes():
    excel = Path("test_data/132018559-07102026102146.xlsx")
    xsd = Path("xsd/ECF31V1.0.xsd")
    if not excel.exists() or not xsd.exists():
        import pytest
        pytest.skip("Configura el Excel oficial y los XSD en test_data/ y xsd/.")

    summary = load_test_set(excel)
    case = next(c for c in summary.ecf_cases if c.case_id == "132018559E310000000003")
    root = etree.fromstring(build_ecf_xml(case, xsd, validate=True))

    items = root.findall(".//DetallesItems/Item")
    assert len(items) == 2
    for item in items:
        codes = [n.text for n in item.findall("./TablaImpuestoAdicional/ImpuestoAdicional/TipoImpuesto")]
        assert codes == ["002", "004"]

    totals = root.findall(".//Totales/ImpuestosAdicionales/ImpuestoAdicional")
    assert [n.findtext("TipoImpuesto") for n in totals] == ["002", "004"]
    assert [n.findtext("OtrosImpuestosAdicionales") for n in totals] == ["2369.28", "11846.42"]
