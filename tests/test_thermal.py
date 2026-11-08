"""Fiscal thermal data: immutable XML, environment QR and fail-closed printing."""
import base64
import hashlib
import os
from io import BytesIO
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MultiServices.settings")
import django
django.setup()
import pytest
from PIL import Image
from ecf.thermal import thermal_representation
from ecf.workflow import ECFWorkflowError


def receipt(document_type="31", total="70.00"):
    encf = f"E{document_type}0000000007"
    xml = f'''<ECF><Encabezado><IdDoc><TipoeCF>{document_type}</TipoeCF><eNCF>{encf}</eNCF><IndicadorMontoGravado>1</IndicadorMontoGravado></IdDoc>
      <Emisor><RNCEmisor>101000001</RNCEmisor><RazonSocialEmisor>EMISOR FISCAL FIRMADO</RazonSocialEmisor><DireccionEmisor>Dirección firmada</DireccionEmisor><FechaEmision>08-11-2026</FechaEmision></Emisor>
      <Comprador><RNCComprador>101000002</RNCComprador><RazonSocialComprador>CLIENTE FIRMADO</RazonSocialComprador><DireccionComprador>No imprimir</DireccionComprador></Comprador>
      <Totales><MontoGravadoTotal>59.32</MontoGravadoTotal><TotalITBIS>10.68</TotalITBIS><MontoTotal>{total}</MontoTotal></Totales></Encabezado>
      <DetallesItems><Item><IndicadorFacturacion>1</IndicadorFacturacion><NombreItem>Producto firmado</NombreItem><CantidadItem>1.00</CantidadItem><UnidadMedida>43</UnidadMedida><PrecioUnitarioItem>70.00</PrecioUnitarioItem><MontoItem>70.00</MontoItem></Item></DetallesItems>
      <FechaHoraFirma>08-11-2026 19:20:30</FechaHoraFirma><Signature><SignatureValue>AbC+/=unit-test-signature</SignatureValue></Signature></ECF>'''
    return SimpleNamespace(status="accepted", signed_xml=xml, xml_hash=hashlib.sha256(xml.encode()).hexdigest(),
                           encf=encf, document_type=document_type, environment="prod",
                           company=SimpleNamespace(rnc="101000001", name="Nombre cambiado posteriormente"))


def test_thermal_uses_signed_identity_amounts_and_six_signature_characters():
    data = thermal_representation(receipt())
    assert data["issuer"]["name"] == "EMISOR FISCAL FIRMADO"
    assert data["buyer"] == {"name": "CLIENTE FIRMADO", "rnc": "101000002"}
    assert data["items"][0]["tax"] == "10.68"
    assert data["totals"][-1] == {"label": "Total:", "value": "70.00"}
    assert data["security_code"] == "AbC+/="
    assert data["signed_date"] == "08-11-2026 19:20:30"
    qr = urlsplit(data["qr_url"])
    assert qr.netloc == "ecf.dgii.gov.do" and qr.path == "/ecf/consultatimbre"
    assert parse_qs(qr.query)["CodigoSeguridad"] == ["AbC+/="]
    image = Image.open(BytesIO(base64.b64decode(data["qr_image"].split(",", 1)[1])))
    assert image.format == "PNG" and image.width == image.height and image.width > 200


@pytest.mark.parametrize("total,host,path", [("249999.99", "fc.dgii.gov.do", "/ecf/consultatimbrefc"), ("250000.00", "ecf.dgii.gov.do", "/ecf/consultatimbre")])
def test_e32_uses_correct_production_qr_service_and_omits_buyer_block(total, host, path):
    data = thermal_representation(receipt("32", total))
    qr = urlsplit(data["qr_url"])
    assert qr.netloc == host and qr.path == path
    assert parse_qs(qr.query)["MontoTotal"] == [total]
    assert data["buyer"] is None


@pytest.mark.parametrize("status", ["draft", "ready", "processing", "rejected", "uncertain"])
def test_unaccepted_electronic_documents_cannot_be_printed_as_fiscal_receipts(status):
    record = receipt()
    record.status = status
    with pytest.raises(ECFWorkflowError, match="aceptación"):
        thermal_representation(record)


def test_changed_stored_xml_is_not_printed_using_an_old_acceptance():
    record = receipt()
    record.signed_xml = record.signed_xml.replace("70.00", "700.00")
    with pytest.raises(ECFWorkflowError, match="hash"):
        thermal_representation(record)


def test_signed_document_from_different_issuer_is_not_printed():
    record = receipt()
    record.company.rnc = "101000099"
    with pytest.raises(ECFWorkflowError, match="identidad"):
        thermal_representation(record)
