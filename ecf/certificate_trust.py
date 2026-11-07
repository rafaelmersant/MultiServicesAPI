"""Explicit signer pinning for DGII certification only; CA trust elsewhere."""

import logging
import os
import re
import secrets
from datetime import datetime, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes


logger = logging.getLogger(__name__)


def certification_pinning_enabled():
    return (os.getenv("DGII_ENVIRONMENT", "").strip().lower() == "cert"
            and bool(os.getenv("ECF_CERT_TRUSTED_SIGNER_SHA256", "").strip()))


def verify_certification_pin(certificate):
    """Called AFTER XML signature/digest verification, never auto-trust input."""
    if not certification_pinning_enabled():
        return False
    pins = [value.strip().replace(":", "").lower()
            for value in os.environ["ECF_CERT_TRUSTED_SIGNER_SHA256"].split(",")]
    if not pins or any(not re.fullmatch(r"[0-9a-f]{64}", value) for value in pins):
        raise ValueError("ECF_CERT_TRUSTED_SIGNER_SHA256 requiere huellas SHA256 de 64 caracteres.")
    fingerprint = certificate.fingerprint(hashes.SHA256()).hex()
    if not any(secrets.compare_digest(fingerprint, pin) for pin in pins):
        raise ValueError("El certificado recibido no coincide con las huellas autorizadas para cert.")
    now = datetime.now(timezone.utc)
    if not certificate.not_valid_before_utc <= now <= certificate.not_valid_after_utc:
        raise ValueError("El certificado autorizado está fuera de su período de vigencia.")
    try:
        if not certificate.extensions.get_extension_for_class(x509.KeyUsage).value.digital_signature:
            raise ValueError("El certificado autorizado no permite firma digital.")
    except x509.ExtensionNotFound:
        pass
    try:
        if certificate.extensions.get_extension_for_class(x509.BasicConstraints).value.ca:
            raise ValueError("La huella debe corresponder al firmante, no a una CA.")
    except x509.ExtensionNotFound:
        pass
    logger.info("DGII_CERT_PIN_ACCEPTED environment=cert sha256=%s", fingerprint)
    return True
