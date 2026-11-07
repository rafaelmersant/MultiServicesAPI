"""Reproduce DGII's default XMLDSig namespace plus inherited xsi/xsd."""

import base64
from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID
from lxml import etree
from signxml import XMLSigner, methods
from signxml.exceptions import InvalidSignature

from ecf.xml_verifier import ReceiverXMLVerifier


@pytest.fixture
def document():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Receiver interoperability test")])
    now = datetime.now(timezone.utc)
    certificate = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
                   .public_key(key.public_key()).serial_number(100)
                   .not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=1))
                   .sign(key, hashes.SHA256())).public_bytes(serialization.Encoding.PEM)
    root = etree.Element("SemillaModel", nsmap={
        "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xsd": "http://www.w3.org/2001/XMLSchema",
    })
    etree.SubElement(root, "valor").text = "test-seed"
    etree.SubElement(root, "fecha").text = now.isoformat()
    signer = XMLSigner(method=methods.enveloped, signature_algorithm="rsa-sha256",
                       digest_algorithm="sha256", c14n_algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315")
    ns = "http://www.w3.org/2000/09/xmldsig#"
    signer.namespaces = {None: ns}
    signed = signer.sign(root, key=key, cert=certificate, reference_uri=None)
    signed = etree.fromstring(etree.tostring(signed))
    info = signed.find(".//{" + ns + "}SignedInfo")
    # Sign the actual inclusive canonical form, independently of SignXML's
    # in-place subtree path. This is the form found in the received DGII file.
    canonical = etree.tostring(etree.fromstring(etree.tostring(info)), method="c14n")
    signed.find(".//{" + ns + "}SignatureValue").text = base64.b64encode(
        key.sign(canonical, padding.PKCS1v15(), hashes.SHA256())
    ).decode()
    return etree.tostring(signed), certificate


def test_default_namespace_signature_and_digest_are_verified(document):
    xml, certificate = document
    result = ReceiverXMLVerifier().verify(xml, x509_cert=certificate)
    assert result.signed_xml.findtext("valor") == "test-seed"


def test_tampered_payload_is_rejected(document):
    xml, certificate = document
    with pytest.raises(InvalidSignature):
        ReceiverXMLVerifier().verify(xml.replace(b"test-seed", b"modified-seed"), x509_cert=certificate)


def test_tampered_signature_is_rejected(document):
    xml, certificate = document
    root = etree.fromstring(xml)
    value = root.find(".//{http://www.w3.org/2000/09/xmldsig#}SignatureValue")
    value.text = ("A" if value.text[0] != "A" else "B") + value.text[1:]
    with pytest.raises(InvalidSignature):
        ReceiverXMLVerifier().verify(etree.tostring(root), x509_cert=certificate)
