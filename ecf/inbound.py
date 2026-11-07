"""Public receiver services required by DGII's emitter certification."""

from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path
import re

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.x509.verification import PolicyBuilder, Store
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.utils import timezone
from lxml import etree
from .xml_verifier import ReceiverXMLVerifier

from administration.models import Company

from .certificate import load_pkcs12
from .certificate_trust import certification_pinning_enabled, verify_certification_pin
from .config import Settings
from .models import ReceivedElectronicDocument
from .signing import sign_xml
from .xml_utils import validate_xsd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
XSD_DIR = PROJECT_ROOT / "xsd"


class InboundDocumentError(ValueError):
    """An incoming document cannot be safely accepted."""


def _verify_certificate_chain(certificate, intermediates, trusted_ca_path: str | Path) -> None:
    # Explicitly authorized leaf fingerprint is an alternative trust anchor
    # only in cert. Signature and digest were already verified by the caller.
    if verify_certification_pin(certificate):
        return
    ca_data = Path(trusted_ca_path).read_bytes()
    try:
        trust_anchors = x509.load_pem_x509_certificates(ca_data)
    except ValueError:
        trust_anchors = [x509.load_der_x509_certificate(ca_data)]
    verifier = PolicyBuilder().store(Store(trust_anchors)).build_client_verifier()
    verifier.verify(certificate, intermediates)


def _xml_from_request(request) -> bytes:
    uploaded = request.data.get("xml")
    if hasattr(uploaded, "read"):
        content = uploaded.read()
    elif isinstance(uploaded, (str, bytes)):
        content = uploaded.encode("utf-8") if isinstance(uploaded, str) else uploaded
    else:
        raise InboundDocumentError("Envía el XML en el campo multipart 'xml'.")
    if not content or len(content) > 5 * 1024 * 1024:
        raise InboundDocumentError("El XML está vacío o supera el límite de 5 MB.")
    return content


def _parse(xml_data: bytes):
    parser = etree.XMLParser(resolve_entities=False, no_network=True, recover=False)
    try:
        return etree.fromstring(xml_data, parser=parser)
    except (etree.XMLSyntaxError, ValueError) as exc:
        raise InboundDocumentError("El archivo recibido no contiene XML válido.") from exc


def _value(root, path: str) -> str:
    values = root.xpath(path)
    return (values[0].text or "").strip() if values else ""


def _verify_embedded_signature(xml_data: bytes) -> None:
    try:
        root = _parse(xml_data)
        certificates = root.xpath(".//*[local-name()='X509Certificate']/text()")
        if not certificates:
            raise InboundDocumentError("El XML firmado no contiene certificado X.509.")
        der = base64.b64decode("".join(certificates[0].split()), validate=True)
        certificate = x509.load_der_x509_certificate(der)
        signer_pem = certificate.public_bytes(serialization.Encoding.PEM)
        ReceiverXMLVerifier().verify(xml_data, x509_cert=signer_pem)
        trusted_ca_path = os.getenv("ECF_TRUSTED_CA_PATH", "").strip()
        if not trusted_ca_path and not certification_pinning_enabled():
            raise InboundDocumentError("Configura ECF_TRUSTED_CA_PATH con la raíz DGII antes de habilitar la recepción.")
        try:
            intermediates = [
                x509.load_der_x509_certificate(base64.b64decode("".join(value.split()), validate=True))
                for value in certificates[1:]
            ]
            _verify_certificate_chain(certificate, intermediates, trusted_ca_path)
        except OSError as exc:
            raise InboundDocumentError("No se pudo leer el certificado raíz configurado.") from exc
    except InboundDocumentError:
        raise
    except Exception as exc:
        raise InboundDocumentError("La firma digital del XML no es válida.") from exc


def _validate_xsd(xml_data: bytes, schema_name: str) -> None:
    schema_path = XSD_DIR / schema_name
    if not schema_path.is_file():
        raise InboundDocumentError("No está disponible el esquema XSD del documento.")
    try:
        validate_xsd(xml_data, schema_path)
    except Exception as exc:
        raise InboundDocumentError("El XML no cumple el formato requerido por DGII.") from exc


def _sign_response(xml_data: bytes) -> bytes:
    settings = Settings.from_env()
    certificate = load_pkcs12(settings.certificate_path, settings.certificate_password)
    return sign_xml(xml_data, certificate)


def build_arecf(issuer_rnc: str, buyer_rnc: str, encf: str, state: int, reason: int | None = None) -> bytes:
    root = etree.Element("ARECF")
    detail = etree.SubElement(root, "DetalleAcusedeRecibo")
    etree.SubElement(detail, "Version").text = "1.0"
    etree.SubElement(detail, "RNCEmisor").text = issuer_rnc
    etree.SubElement(detail, "RNCComprador").text = buyer_rnc
    etree.SubElement(detail, "eNCF").text = encf
    etree.SubElement(detail, "Estado").text = str(state)
    if reason is not None:
        etree.SubElement(detail, "CodigoMotivoNoRecibido").text = str(reason)
    etree.SubElement(detail, "FechaHoraAcuseRecibo").text = timezone.localtime().strftime("%d-%m-%Y %H:%M:%S")
    unsigned = etree.tostring(root, encoding="UTF-8", xml_declaration=True)
    _validate_xsd(unsigned, "ARECF v1.0.xsd")
    return _sign_response(unsigned)


def receive_ecf(request) -> HttpResponse:
    xml_data = _xml_from_request(request)
    root = _parse(xml_data)
    if etree.QName(root).localname != "ECF":
        raise InboundDocumentError("El documento recibido no tiene raíz ECF.")

    issuer_rnc = _value(root, ".//*[local-name()='Emisor']/*[local-name()='RNCEmisor']")
    buyer_rnc = _value(root, ".//*[local-name()='Comprador']/*[local-name()='RNCComprador']")
    encf = _value(root, ".//*[local-name()='IdDoc']/*[local-name()='eNCF']")
    if not issuer_rnc or not buyer_rnc or not encf:
        raise InboundDocumentError("Faltan RNCEmisor, RNCComprador o eNCF en el e-CF.")

    company = Company.objects.filter(rnc=buyer_rnc).first()
    if company is None:
        raise InboundDocumentError("El RNCComprador no corresponde a una empresa registrada.")

    reason = None
    try:
        doc_type = encf[1:3]
        if len(encf) != 13 or not re.fullmatch(r"E\d{12}", encf) or not doc_type.isdigit():
            raise InboundDocumentError("El e-NCF no tiene un formato válido.")
        _validate_xsd(xml_data, f"ECF{doc_type}V1.0.xsd")
    except InboundDocumentError:
        reason = 1  # Error de especificación.

    if reason is None:
        try:
            _verify_embedded_signature(xml_data)
        except InboundDocumentError:
            reason = 2  # Error de firma digital.

    if reason is None and buyer_rnc != (company.rnc or "").strip():
        reason = 4  # RNC comprador no corresponde.

    if reason is not None:
        receipt = build_arecf(issuer_rnc, buyer_rnc, encf, 1, reason)
        return HttpResponse(receipt, content_type="application/xml; charset=utf-8", status=200)

    digest = hashlib.sha256(xml_data).hexdigest()
    receipt = build_arecf(issuer_rnc, buyer_rnc, encf, 0)
    try:
        with transaction.atomic():
            document, created = ReceivedElectronicDocument.objects.get_or_create(
                company=company,
                kind=ReceivedElectronicDocument.Kind.ECF,
                issuer_rnc=issuer_rnc,
                encf=encf,
                defaults={
                    "buyer_rnc": buyer_rnc,
                    "xml_sha256": digest,
                    "signed_xml": xml_data.decode("utf-8"),
                    "receipt_xml": receipt.decode("utf-8"),
                },
            )
    except IntegrityError:
        created = False
        document = ReceivedElectronicDocument.objects.get(
            company=company,
            kind=ReceivedElectronicDocument.Kind.ECF,
            issuer_rnc=issuer_rnc,
            encf=encf,
        )
    if not created:
        duplicate_receipt = build_arecf(issuer_rnc, buyer_rnc, encf, 1, 3)
        return HttpResponse(duplicate_receipt, content_type="application/xml; charset=utf-8", status=200)
    return HttpResponse(receipt, content_type="application/xml; charset=utf-8", status=200)


def receive_commercial_approval(request) -> HttpResponse:
    xml_data = _xml_from_request(request)
    root = _parse(xml_data)
    if etree.QName(root).localname != "ACECF":
        raise InboundDocumentError("El documento recibido no tiene raíz ACECF.")
    _validate_xsd(xml_data, "ACECF v.1.0.xsd")
    _verify_embedded_signature(xml_data)
    issuer_rnc = _value(root, ".//*[local-name()='DetalleAprobacionComercial']/*[local-name()='RNCEmisor']")
    buyer_rnc = _value(root, ".//*[local-name()='DetalleAprobacionComercial']/*[local-name()='RNCComprador']")
    encf = _value(root, ".//*[local-name()='DetalleAprobacionComercial']/*[local-name()='eNCF']")
    if not issuer_rnc or not buyer_rnc or not encf:
        raise InboundDocumentError("Faltan RNCEmisor, RNCComprador o eNCF en el ACECF.")
    company = Company.objects.filter(rnc=buyer_rnc).first()
    if company is None:
        raise InboundDocumentError("El RNCComprador no corresponde a una empresa registrada.")
    digest = hashlib.sha256(xml_data).hexdigest()
    try:
        ReceivedElectronicDocument.objects.get_or_create(
            company=company,
            kind=ReceivedElectronicDocument.Kind.COMMERCIAL_APPROVAL,
            issuer_rnc=issuer_rnc,
            encf=encf,
            defaults={
                "buyer_rnc": buyer_rnc,
                "xml_sha256": digest,
                "signed_xml": xml_data.decode("utf-8"),
            },
        )
    except IntegrityError:
        if not ReceivedElectronicDocument.objects.filter(
            company=company,
            kind=ReceivedElectronicDocument.Kind.COMMERCIAL_APPROVAL,
            issuer_rnc=issuer_rnc,
            encf=encf,
        ).exists():
            raise
        # A retry is idempotent; the first signed approval is immutable.
    return HttpResponse("OK", content_type="text/plain; charset=utf-8", status=200)
