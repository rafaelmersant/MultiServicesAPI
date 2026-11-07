import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MultiServices.settings")
import django
django.setup()

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from ecf.certificate_trust import verify_certification_pin
from ecf.inbound import _verify_certificate_chain


def certificate(expired=False):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Explicit test signer")])
    now = datetime.now(timezone.utc)
    return (x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(key.public_key()).serial_number(100)
            .not_valid_before(now - timedelta(days=2))
            .not_valid_after(now + timedelta(days=-1 if expired else 1))
            .sign(key, hashes.SHA256()))


def configure(monkeypatch, cert, environment="cert"):
    monkeypatch.setenv("DGII_ENVIRONMENT", environment)
    monkeypatch.setenv("ECF_CERT_TRUSTED_SIGNER_SHA256", cert.fingerprint(hashes.SHA256()).hex())


def test_exact_pin_is_trusted_without_reading_ca_file(monkeypatch):
    cert = certificate()
    configure(monkeypatch, cert)
    _verify_certificate_chain(cert, [], "does-not-exist.pem")


def test_different_signer_is_rejected(monkeypatch):
    configure(monkeypatch, certificate())
    with pytest.raises(ValueError, match="no coincide"):
        verify_certification_pin(certificate())


@pytest.mark.parametrize("environment", ["prod", "precert", ""])
def test_non_cert_environment_never_bypasses_ca(monkeypatch, environment):
    cert = certificate()
    configure(monkeypatch, cert, environment)
    assert verify_certification_pin(cert) is False
    with pytest.raises(FileNotFoundError):
        _verify_certificate_chain(cert, [], "does-not-exist.pem")


def test_expired_matching_certificate_is_rejected(monkeypatch):
    cert = certificate(expired=True)
    configure(monkeypatch, cert)
    with pytest.raises(ValueError, match="vigencia"):
        verify_certification_pin(cert)


def test_malformed_pin_is_rejected(monkeypatch):
    monkeypatch.setenv("DGII_ENVIRONMENT", "cert")
    monkeypatch.setenv("ECF_CERT_TRUSTED_SIGNER_SHA256", "not-a-fingerprint")
    with pytest.raises(ValueError, match="64 caracteres"):
        verify_certification_pin(certificate())


def test_empty_pin_keeps_ca_validation(monkeypatch):
    monkeypatch.setenv("DGII_ENVIRONMENT", "cert")
    monkeypatch.delenv("ECF_CERT_TRUSTED_SIGNER_SHA256", raising=False)
    with pytest.raises(FileNotFoundError):
        _verify_certificate_chain(certificate(), [], "does-not-exist.pem")
