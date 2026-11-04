"""Checks for blank-page rejection in grouped certification RIs."""

import os
from decimal import Decimal

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MultiServices.settings")

import django

django.setup()

from scripts.build_certification_representations import page_has_fiscal_content
from ecf.models import ECFEnvironment
from ecf.workflow import (
    ECFWorkflowError,
    _apply_registered_issuer_identity,
    _is_valid_dgii_email,
    _representation_qr_url,
    _validate_expected_tax_id,
    build_representation_pdf,
    representation_pdf_identity_is_current,
    send_record,
    send_rfce_record,
    sign_record,
)


class TextPage:
    def __init__(self, text):
        self.text = text

    def extract_text(self):
        return self.text


def test_ri_page_with_only_footer_is_rejected():
    page = TextPage(
        "Código de Seguridad: ABC123\n"
        "Fecha Firma: 17-10-2026 12:00:00\n"
        "Estado DGII: Aceptado\n"
        "Página 2\n"
    )

    assert not page_has_fiscal_content(page)


def test_ri_page_with_invoice_totals_has_fiscal_content():
    page = TextPage(
        "Valor a pagar 1000.00\n"
        "Total 1000.00\n"
        "Código de Seguridad: ABC123\n"
        "Página 2\n"
    )

    assert page_has_fiscal_content(page)


def test_certification_ri_qr_uses_certecf_and_percent_encodes_reserved_characters():
    from types import SimpleNamespace
    from urllib.parse import parse_qs, urlsplit

    url = _representation_qr_url(
        SimpleNamespace(environment=ECFEnvironment.CERT, document_type="31"),
        issuer_rnc="132018559",
        buyer_rnc="131880681",
        encf="E310000000035",
        emission_date="01-04-2020",
        signed_date="17-10-2026 17:44:28",
        total=Decimal("7080.00"),
        security_code="A+B #C",
    )

    parsed = urlsplit(url)
    assert parsed.netloc == "ecf.dgii.gov.do"
    assert parsed.path == "/certecf/consultatimbre"
    assert parse_qs(parsed.query)["CodigoSeguridad"] == ["A+B #C"]
    assert "%20" in parsed.query


def test_small_consumer_ri_qr_uses_certification_rfce_endpoint():
    from types import SimpleNamespace
    from urllib.parse import urlsplit

    url = _representation_qr_url(
        SimpleNamespace(environment=ECFEnvironment.CERT, document_type="32"),
        issuer_rnc="132018559",
        buyer_rnc="",
        encf="E320000000018",
        emission_date="01-04-2020",
        signed_date="17-10-2026 17:44:28",
        total=Decimal("249999.99"),
        security_code="A1B2C3",
    )

    parsed = urlsplit(url)
    assert parsed.netloc == "fc.dgii.gov.do"
    assert parsed.path == "/certecf/consultatimbrefc"


def test_expense_qr_omits_absent_optional_buyer():
    from types import SimpleNamespace
    from urllib.parse import parse_qs, urlsplit

    url = _representation_qr_url(
        SimpleNamespace(environment=ECFEnvironment.CERT, document_type="43"),
        issuer_rnc="132018559", buyer_rnc="", encf="E430000000013",
        emission_date="20-10-2026", signed_date="20-10-2026 10:11:12",
        total=Decimal("253770.00"), security_code="ABC123",
    )
    assert "RncComprador" not in parse_qs(urlsplit(url).query, keep_blank_values=True)
    assert "RncComprador=" not in url


def test_consumer_exactly_250000_uses_ecf_service():
    from types import SimpleNamespace
    from urllib.parse import urlsplit

    url = _representation_qr_url(
        SimpleNamespace(environment=ECFEnvironment.CERT, document_type="32"),
        issuer_rnc="132018559", buyer_rnc="131880681", encf="E320000000022",
        emission_date="20-10-2026", signed_date="20-10-2026 10:11:12",
        total=Decimal("250000.00"), security_code="ABC123",
    )
    assert urlsplit(url).netloc == "ecf.dgii.gov.do"


def test_new_ecf_uses_registered_issuer_identity_instead_of_fixture_values():
    from types import SimpleNamespace

    values = {
        "RNCEmisor": "000000000",
        "RazonSocialEmisor": "DOCUMENTOS ELECTRONICOS DE 02",
        "DireccionEmisor": "DIRECCION DE PRUEBA",
        "NombreComercial": "DOCUMENTOS ELECTRONICOS DE 02",
        "Sucursal": "SUCURSAL DE PRUEBA",
        "Municipio": "010100",
        "Provincia": "010000",
        "TelefonoEmisor[1]": "809-000-0000",
        "TelefonoEmisor[2]": "809-111-1111",
        "WebSite": "www.example.test",
    }
    company = SimpleNamespace(
        rnc="132018559",
        name="Ferreteria Casa Minaya Arias, S.R.L.",
        address="Calle Corazón de Jesús, esq. 12, El Almirante Caña, Sto. Dgo. Este",
        email="Eljoel_00@hotmail.com",
        phoneNumber="(849) 504-7281",
    )

    _apply_registered_issuer_identity(values, company)

    assert values["RNCEmisor"] == company.rnc
    assert values["RazonSocialEmisor"] == company.name
    assert values["DireccionEmisor"] == company.address
    assert "CorreoEmisor" not in values
    assert not _is_valid_dgii_email(company.email)
    assert _is_valid_dgii_email("eljoel00@hotmail.com")
    assert "NombreComercial" not in values
    assert "Sucursal" not in values
    assert "Municipio" not in values
    assert "Provincia" not in values
    assert "WebSite" not in values
    assert values["TelefonoEmisor[1]"] == "849-504-7281"
    assert "TelefonoEmisor[2]" not in values

    from scripts.prepare_certification_restart import build_payload_case

    case = SimpleNamespace(
        case_id="case-1",
        version="1.0",
        tipo_ecf="31",
        encf="E310000000001",
        values={
            "ENCF": "fixture",
            "RNCEmisor": "000000000",
            "RazonSocialEmisor": "DOCUMENTOS ELECTRONICOS DE 02",
            "DireccionEmisor": "DIRECCION DE PRUEBA",
        },
    )
    adapted = build_payload_case(case, case.encf, company)
    assert adapted.values["RNCEmisor"] == company.rnc
    assert adapted.values["RazonSocialEmisor"] == company.name
    assert adapted.values["DireccionEmisor"] == company.address


def test_new_ecf_fails_closed_when_real_issuer_identity_is_incomplete():
    from types import SimpleNamespace
    import pytest

    company = SimpleNamespace(rnc="132018559", name="", address="", email="")

    with pytest.raises(ECFWorkflowError, match="RNC, razón social y dirección reales"):
        _apply_registered_issuer_identity({}, company)


def test_ri_cannot_override_issuer_identity_from_signed_xml():
    from types import SimpleNamespace

    record = SimpleNamespace(
        status="accepted",
        environment=ECFEnvironment.CERT,
        company=SimpleNamespace(
            name="Ferreteria Casa Minaya Arias, S.R.L.",
            rnc="132018559",
            address="Calle Corazón de Jesús, esq. 12, El Almirante Caña, Sto. Dgo. Este",
        ),
        signed_xml=(
            "<ECF><Encabezado><Emisor>"
            "<RazonSocialEmisor>DOCUMENTOS ELECTRONICOS DE 02</RazonSocialEmisor>"
            "<RNCEmisor>132018559</RNCEmisor>"
            "<DireccionEmisor>AVE. ISABEL AGUIAR NO. 269</DireccionEmisor>"
            "</Emisor><Totales/></Encabezado><SignatureValue>ABC123</SignatureValue></ECF>"
        ),
    )
    company_identity = {
        "name": "Ferreteria Casa Minaya Arias, S.R.L.",
        "address": "Calle Corazón de Jesús, esq. 12, El Almirante Caña, Sto. Dgo. Este",
    }

    import pytest

    assert not representation_pdf_identity_is_current(record)
    for requested_identity in (None, company_identity):
        with pytest.raises(ECFWorkflowError, match="no coincide con la razón social"):
            build_representation_pdf(record, registered_issuer=requested_identity)


def test_stale_issuer_identity_is_rejected_before_signing_or_sending():
    from types import SimpleNamespace
    import pytest

    company = SimpleNamespace(
        name="Ferreteria Casa Minaya Arias, S.R.L.",
        rnc="132018559",
        address="Calle Corazón de Jesús, esq. 12, El Almirante Caña, Sto. Dgo. Este",
    )
    xml = (
        "<ECF><Encabezado><TipoeCF>31</TipoeCF><eNCF>E310000000039</eNCF><Emisor>"
        "<RNCEmisor>132018559</RNCEmisor>"
        "<RazonSocialEmisor>DOCUMENTOS ELECTRONICOS DE 02</RazonSocialEmisor>"
        "<DireccionEmisor>AVE. ISABEL AGUIAR NO. 269</DireccionEmisor>"
        "</Emisor></Encabezado></ECF>"
    )
    record = SimpleNamespace(
        status="draft",
        environment=ECFEnvironment.CERT,
        company=company,
        encf="E310000000039",
        document_type="31",
        raw_xml=xml,
        signed_xml=xml,
    )

    with pytest.raises(ECFWorkflowError, match="no coincide con la razón social"):
        sign_record(record)
    record.status = "ready"
    with pytest.raises(ECFWorkflowError, match="no coincide con la razón social"):
        send_record(record)

    rfce_record = SimpleNamespace(
        document_type="32",
        status="ready",
        rfce_status="ready",
        signed_rfce_xml="<RFCE/>",
        signed_xml=(
            "<ECF><Encabezado><TipoeCF>32</TipoeCF><eNCF>E320000000022</eNCF><Emisor>"
            "<RNCEmisor>132018559</RNCEmisor>"
            "<RazonSocialEmisor>DOCUMENTOS ELECTRONICOS DE 02</RazonSocialEmisor>"
            "<DireccionEmisor>AVE. ISABEL AGUIAR NO. 269</DireccionEmisor>"
            "</Emisor></Encabezado></ECF>"
        ),
        company=company,
        encf="E320000000022",
    )
    with pytest.raises(ECFWorkflowError, match="no coincide con la razón social"):
        send_rfce_record(rfce_record)


def test_configured_tax_id_must_match_the_company_before_dgii_actions():
    import pytest

    _validate_expected_tax_id("132018559", "132018559")
    _validate_expected_tax_id(None, "132018559")
    with pytest.raises(ECFWorkflowError, match="ECF_EXPECTED_TAX_ID"):
        _validate_expected_tax_id("999999999", "132018559")


def _layout_record(document_type="31", foreign_buyer=False, stale_identity=False):
    from types import SimpleNamespace

    company = SimpleNamespace(
        name="Ferreteria Casa Minaya Arias, S.R.L.", rnc="132018559",
        address="Calle Corazón de Jesús, esq. 12, El Almirante Caña, Sto. Dgo. Este",
        email="",
    )
    name = "EMISOR ANTERIOR DEL TEST" if stale_identity else company.name
    buyer = "<IdentificadorExtranjero>FOREIGN-123</IdentificadorExtranjero>" if foreign_buyer else "<RNCComprador>131880681</RNCComprador>"
    encf = f"E{document_type}0000000001"
    xml = (
        f"<ECF><Encabezado><IdDoc><TipoeCF>{document_type}</TipoeCF><eNCF>{encf}</eNCF></IdDoc>"
        f"<Emisor><RNCEmisor>{company.rnc}</RNCEmisor><RazonSocialEmisor>{name}</RazonSocialEmisor>"
        f"<DireccionEmisor>{company.address}</DireccionEmisor><FechaEmision>20-10-2026</FechaEmision></Emisor>"
        f"<Comprador>{buyer}<DireccionComprador>DIRECCION CLIENTE DEL TEST</DireccionComprador></Comprador><Totales><MontoTotal>118.00</MontoTotal></Totales></Encabezado>"
        "<DetallesItems><Item><CantidadItem>1</CantidadItem><NombreItem>ARTICULO DEL TEST</NombreItem>"
        "<UnidadMedida>43</UnidadMedida><PrecioUnitarioItem>100.00</PrecioUnitarioItem>"
        "<IndicadorFacturacion>1</IndicadorFacturacion><MontoItem>100.00</MontoItem></Item></DetallesItems>"
        "<InformacionReferencia><NCFModificado>E310000000099</NCFModificado><CodigoModificacion>3</CodigoModificacion></InformacionReferencia>"
        "<FechaHoraFirma>20-10-2026 10:11:12</FechaHoraFirma><SignatureValue>ABC123TESTONLY</SignatureValue></ECF>"
    )
    return SimpleNamespace(
        status="accepted", environment=ECFEnvironment.CERT, document_type=document_type,
        company=company, encf=encf, signed_xml=xml, dgii_status="Aceptado",
    )


def test_ri_has_one_right_header_and_both_signature_labels_below_qr():
    from io import BytesIO
    from pypdf import PdfReader
    from pypdf.generic import ContentStream

    reader = PdfReader(BytesIO(build_representation_pdf(_layout_record())))
    page = reader.pages[0]
    text = page.extract_text()
    assert text.count("Factura de Crédito Fiscal Electrónica") == 1
    assert "Dirección:" in text
    assert "Razón Social Cliente:" not in text  # No buyer name in this test XML.
    assert "RNC Cliente:" in text
    assert "DIRECCION CLIENTE DEL TEST" not in text
    assert "Descuento/" not in text
    assert "Fecha Firma:" in text
    assert "Fecha de Firma Digital:" not in text
    positions = {}

    def visit(text, cm, tm, font, size):
        for label in ("Factura de Crédito Fiscal Electrónica", "Código de Seguridad:", "Fecha Firma:"):
            if label in text:
                positions[label] = (tm[4] * cm[0] + tm[5] * cm[2] + cm[4], tm[4] * cm[1] + tm[5] * cm[3] + cm[5])

    page.extract_text(visitor_text=visit)
    assert positions["Factura de Crédito Fiscal Electrónica"][0] > float(page.mediabox.width) / 2
    assert positions["Factura de Crédito Fiscal Electrónica"][1] > 600
    qr_bottom = None
    def image_position(operator, operands, cm, tm):
        nonlocal qr_bottom
        if operator == b"Do" and abs(float(cm[0]) - 22 * 72 / 25.4) < 1:
            qr_bottom = float(cm[5])

    page.extract_text(visitor_operand_before=image_position)
    assert qr_bottom is not None
    assert positions["Código de Seguridad:"][1] < qr_bottom
    assert positions["Fecha Firma:"][1] < positions["Código de Seguridad:"][1]
    assert "20-10-2026 10:11:12" in text
    assert "E310000000099" in text  # Reference data lives outside Encabezado.


def test_foreign_buyer_identifier_is_not_used_as_rnc_in_qr(monkeypatch):
    import ecf.workflow as workflow

    captured = {}
    original = workflow._representation_qr_url

    def capture(record, **values):
        captured.update(values)
        return original(record, **values)

    monkeypatch.setattr(workflow, "_representation_qr_url", capture)
    build_representation_pdf(_layout_record("47", foreign_buyer=True))
    assert captured["buyer_rnc"] == ""


def test_paginated_ri_repeats_issuer_encf_and_header_on_each_page():
    from copy import deepcopy
    from io import BytesIO
    from lxml import etree
    from pypdf import PdfReader

    record = _layout_record()
    root = etree.fromstring(record.signed_xml.encode("utf-8"))
    details = root.find("DetallesItems")
    template = deepcopy(details[0])
    for _ in range(45):
        details.append(deepcopy(template))
    record.signed_xml = etree.tostring(root, encoding="unicode")
    reader = PdfReader(BytesIO(build_representation_pdf(record)))
    assert len(reader.pages) > 1
    for page in reader.pages:
        text = page.extract_text()
        assert record.company.name in text
        assert record.encf in text
        assert text.count("Factura de Crédito Fiscal Electrónica") == 1
        assert "Código de Seguridad:" in text


