from unittest.mock import patch
import base64
import os
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
import hashlib

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MultiServices.settings")
import django

django.setup()

import pytest
from django.urls import resolve
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from lxml import etree
from signxml import XMLSigner, methods
import jwt
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from signxml import XMLVerifier

from ecf.inbound import (
    InboundDocumentError,
    _verify_certificate_chain,
    _verify_embedded_signature,
    build_arecf,
)
from ecf.inbound_auth import TOKEN_AUDIENCE, TOKEN_ISSUER
from ecf.models import ECFAuthenticationChallenge
from ecf.models import ReceivedElectronicDocument
from ecf.xml_utils import validate_xsd


def test_dgii_standard_receiver_paths_are_mapped():
    assert resolve("/fe/recepcion/api/ecf").url_name == "dgii-recepcion-standard"
    assert resolve("/fe/aprobacioncomercial/api/ecf").url_name == "dgii-aprobacion-standard"


@pytest.mark.parametrize(
    ("url", "name"),
    [
        ("/FE/RECEPCION/API/ECF", "dgii-recepcion-standard"),
        ("/Fe/Autenticacion/Api/Semilla/", "dgii-semilla-standard"),
        ("/FE/AUTENTICACION/API/VALIDACIONCERTIFICADO", "dgii-auth-standard"),
        ("/Fe/AprobacionComercial/Api/Ecf/", "dgii-aprobacion-standard"),
        ("/api/v1/FE/RECEPCION/API/ECF", "dgii-recepcion"),
    ],
)
def test_dgii_service_paths_are_case_insensitive_and_allow_optional_trailing_slash(url, name):
    assert resolve(url).url_name == name


@pytest.mark.parametrize(
    "url",
    [
        "/fe/recepcion/api/ecf",
        "/fe/aprobacioncomercial/api/ecf",
    ],
)
def test_receiver_endpoints_reject_missing_xml_without_accepting_placeholder_data(url):
    response = APIClient().post(url, {}, format="multipart")
    assert response.status_code == 400
    if "aprobacioncomercial" in url:
        assert response.content.startswith(b"Error:")
    else:
        assert response.data["status"] == "error"


def test_arecf_acknowledgement_matches_dgii_xsd_and_contains_rejection_reason():
    with patch("ecf.inbound._sign_response", side_effect=lambda xml: xml):
        xml_data = build_arecf("132018559", "132018559", "E310000000001", 1, 1)

    validate_xsd(xml_data, "xsd/ARECF v1.0.xsd")
    assert b"<Estado>1</Estado>" in xml_data
    assert b"<CodigoMotivoNoRecibido>1</CodigoMotivoNoRecibido>" in xml_data


def test_receiver_accepts_signed_ecf_and_returns_arecf():
    path = Path("test_data/ecf/caso_prueba_firmado.xml")
    if not path.is_file():
        pytest.skip("El XML firmado de referencia no se distribuye por GitHub.")
    xml_data = path.read_bytes()
    root = etree.fromstring(xml_data)
    buyer_rnc = root.xpath(".//*[local-name()='Comprador']/*[local-name()='RNCComprador']/text()")[0]
    cert_value = root.xpath(".//*[local-name()='X509Certificate']/text()")[0]
    signer = x509.load_der_x509_certificate(base64.b64decode("".join(cert_value.split())))
    signer_pem = signer.public_bytes(serialization.Encoding.PEM)
    XMLVerifier().verify(xml_data, x509_cert=signer_pem)

    with (
        patch("ecf.inbound.Company.objects.filter") as company_filter,
        patch.object(ReceivedElectronicDocument.objects, "get_or_create", return_value=(object(), True)),
        patch("ecf.inbound._verify_embedded_signature"),
        patch("ecf.inbound._sign_response", side_effect=lambda data: data),
    ):
        company_filter.return_value.first.return_value = SimpleNamespace(rnc=buyer_rnc)
        response = APIClient().post(
            "/fe/recepcion/api/ecf",
            {"xml": SimpleUploadedFile("ecf.xml", xml_data, content_type="text/xml")},
            format="multipart",
        )

    assert response.status_code == 200, response.data
    assert b"<Estado>0</Estado>" in response.content


def test_receiver_accepts_commercial_approval_and_returns_ok():
    xml_data = b"""<?xml version='1.0' encoding='UTF-8'?>
    <ACECF><DetalleAprobacionComercial>
      <Version>1.0</Version><RNCEmisor>132018559</RNCEmisor>
      <eNCF>E310000000001</eNCF><FechaEmision>17-10-2026</FechaEmision>
      <MontoTotal>100.00</MontoTotal><RNCComprador>132018559</RNCComprador>
      <Estado>1</Estado><FechaHoraAprobacionComercial>17-10-2026 12:00:00</FechaHoraAprobacionComercial>
    </DetalleAprobacionComercial></ACECF>"""
    with (
        patch("ecf.inbound.Company.objects.filter") as company_filter,
        patch.object(ReceivedElectronicDocument.objects, "get_or_create", return_value=(object(), True)),
        patch("ecf.inbound._verify_embedded_signature"),
    ):
        company_filter.return_value.first.return_value = SimpleNamespace(rnc="132018559")
        response = APIClient().post(
            "/fe/aprobacioncomercial/api/ecf",
            {"xml": SimpleUploadedFile("acecf.xml", xml_data, content_type="text/xml")},
            format="multipart",
        )

    assert response.status_code == 200
    assert response.content == b"OK"


def test_inbound_signature_verification_fails_closed_without_dgii_root(monkeypatch):
    monkeypatch.delenv("ECF_TRUSTED_CA_PATH", raising=False)
    path = Path("test_data/ecf/caso_prueba_firmado.xml")
    if not path.is_file():
        pytest.skip("El XML firmado de referencia no se distribuye por GitHub.")
    xml_data = path.read_bytes()

    with pytest.raises(InboundDocumentError, match="ECF_TRUSTED_CA_PATH"):
        _verify_embedded_signature(xml_data)


def test_trusted_ca_path_accepts_valid_client_chain(tmp_path):
    now = datetime.now(timezone.utc)
    root_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    root_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "DGII test root")])
    root_cert = (
        x509.CertificateBuilder()
        .subject_name(root_name)
        .issuer_name(root_name)
        .public_key(root_key.public_key())
        .serial_number(1001)
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=True, path_length=1), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(root_key.public_key()), critical=False)
        .add_extension(
            x509.KeyUsage(
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=None,
                decipher_only=None,
            ),
            critical=True,
        )
        .sign(root_key, hashes.SHA256())
    )
    leaf_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    leaf_cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "DGII test sender")]))
        .issuer_name(root_name)
        .public_key(leaf_key.public_key())
        .serial_number(1002)
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(root_key.public_key()), critical=False)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(leaf_key.public_key()), critical=False)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("sender.example")]), critical=False)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False)
        .sign(root_key, hashes.SHA256())
    )
    root_path = tmp_path / "dgii-root.pem"
    root_path.write_bytes(root_cert.public_bytes(serialization.Encoding.PEM))

    _verify_certificate_chain(leaf_cert, [], root_path)


def _signed_seed_file(value=None):
    value = value or base64.b64encode(bytes(range(32))).decode("ascii")
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Seed client")])
    now = datetime.now(timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(2001)
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    root = etree.Element("semillamodel")
    etree.SubElement(root, "valor").text = value
    etree.SubElement(root, "fecha").text = now.isoformat()
    signed = XMLSigner(
        method=methods.enveloped,
        signature_algorithm="rsa-sha256",
        digest_algorithm="sha256",
        c14n_algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315",
    ).sign(
        root,
        key=key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
        cert=certificate.public_bytes(serialization.Encoding.PEM),
        reference_uri=None,
    )
    return etree.tostring(signed, encoding="UTF-8", xml_declaration=True)


def test_seed_endpoint_returns_xml_and_persists_only_seed_hash():
    with (
        patch.object(ECFAuthenticationChallenge.objects, "filter") as filters,
        patch.object(ECFAuthenticationChallenge.objects, "create") as create,
    ):
        filters.return_value.delete.return_value = (0, {})
        response = APIClient().get("/fe/autenticacion/api/semilla", HTTP_ACCEPT="application/xml")

    assert response.status_code == 200
    root = etree.fromstring(response.content)
    value = root.xpath("./*[local-name()='valor']/text()")[0]
    assert len(base64.b64decode(value)) == 32
    assert create.call_args.kwargs["seed_sha256"] == hashlib.sha256(value.encode("ascii")).hexdigest()
    assert "seed" not in create.call_args.kwargs


def test_valid_signed_seed_returns_one_hour_bearer_token(monkeypatch):
    token_secret = "test-only-token-secret-0123456789abcdef"
    monkeypatch.setenv("ECF_AUTH_TOKEN_SECRET", token_secret)
    monkeypatch.setenv("ECF_AUTH_TRUSTED_CA_PATH", "test-ca.pem")
    xml_data = _signed_seed_file()
    root = etree.fromstring(xml_data)
    issued_at = datetime.fromisoformat(root.xpath("./*[local-name()='fecha']/text()")[0])
    challenge = SimpleNamespace(pk=7, issued_at=issued_at)
    querysets = [
        SimpleNamespace(first=lambda: challenge),
        SimpleNamespace(update=lambda **kwargs: 1),
    ]
    with (
        patch("ecf.inbound_auth._verify_certificate_chain"),
        patch.object(ECFAuthenticationChallenge.objects, "filter", side_effect=querysets) as filters,
    ):
        response = APIClient().post(
            "/fe/autenticacion/api/validacioncertificado",
            {"xml": SimpleUploadedFile("seed.xml", xml_data, content_type="text/xml")},
            format="multipart",
            HTTP_ACCEPT="application/json",
        )

    assert response.status_code == 200, response.data
    assert set(response.data) == {"token", "expira", "expedido"}
    assert filters.call_args_list[0].kwargs["seed_sha256"] == hashlib.sha256(
        base64.b64encode(bytes(range(32)))
    ).hexdigest()
    claims = jwt.decode(
        response.data["token"],
        token_secret,
        algorithms=["HS256"],
        issuer="MultiServicesAPI",
        audience="ecf-receiver",
    )
    assert claims["sub"]
    assert claims["exp"] - claims["iat"] == 3600


def test_receiver_can_require_bearer_tokens_when_auth_service_is_declared(monkeypatch):
    monkeypatch.setenv("ECF_REQUIRE_INBOUND_AUTH", "true")
    token_secret = "test-only-token-secret-0123456789abcdef"
    monkeypatch.setenv("ECF_AUTH_TOKEN_SECRET", token_secret)
    unauthorized = APIClient().post("/fe/recepcion/api/ecf", {}, format="multipart")
    assert unauthorized.status_code == 401

    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": "test-certificate",
            "iat": now,
            "exp": now + timedelta(hours=1),
            "jti": "test-token",
            "iss": TOKEN_ISSUER,
            "aud": TOKEN_AUDIENCE,
        },
        token_secret,
        algorithm="HS256",
    )
    authorized = APIClient().post(
        "/fe/recepcion/api/ecf",
        {},
        format="multipart",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert authorized.status_code == 400
    assert "campo multipart" in authorized.data["message"]
