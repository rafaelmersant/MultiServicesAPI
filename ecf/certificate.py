
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import (
    pkcs12,
)

from .exceptions import ECFError


class CertificateError(ECFError):
    """Problema al cargar o verificar el certificado."""


@dataclass(frozen=True)
class LoadedCertificate:
    private_key: rsa.RSAPrivateKey
    certificate: x509.Certificate
    private_key_pem: bytes
    certificate_pem: bytes


def load_pkcs12(
    path: str | Path,
    password: str,
) -> LoadedCertificate:
    """
    Carga un certificado PKCS#12 (.p12/.pfx).

    No escribe la clave privada en disco.
    """

    certificate_path = Path(path)

    if not certificate_path.is_file():
        raise CertificateError(
            f"No existe el certificado: {certificate_path}"
        )

    if not password:
        raise CertificateError(
            "La contraseña del certificado está vacía."
        )

    try:
        p12_data = certificate_path.read_bytes()

        private_key, certificate, _chain = (
            pkcs12.load_key_and_certificates(
                p12_data,
                password.encode("utf-8"),
            )
        )

    except (ValueError, TypeError) as exc:
        raise CertificateError(
            "No fue posible abrir el PKCS#12. "
            "Verifica el archivo y la contraseña."
        ) from exc

    if private_key is None:
        raise CertificateError(
            "El archivo no contiene una clave privada."
        )

    if certificate is None:
        raise CertificateError(
            "El archivo no contiene un certificado."
        )

    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise CertificateError(
            "El certificado no utiliza una clave RSA. "
            "Verifica el algoritmo requerido por DGII."
        )

    cert_public_key = certificate.public_key()

    if not isinstance(cert_public_key, rsa.RSAPublicKey):
        raise CertificateError(
            "La clave pública del certificado no es RSA."
        )

    if (
        private_key.public_key().public_numbers()
        != cert_public_key.public_numbers()
    ):
        raise CertificateError(
            "La clave privada no corresponde al certificado."
        )

    # Compatibilidad con versiones recientes de cryptography.
    now = datetime.now(timezone.utc)

    not_before = certificate.not_valid_before_utc
    not_after = certificate.not_valid_after_utc

    if now < not_before or now > not_after:
        raise CertificateError(
            "El certificado está fuera de su período de validez."
        )

    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    certificate_pem = certificate.public_bytes(
        serialization.Encoding.PEM
    )

    return LoadedCertificate(
        private_key=private_key,
        certificate=certificate,
        private_key_pem=private_key_pem,
        certificate_pem=certificate_pem,
    )


def certificate_summary(
    loaded: LoadedCertificate,
) -> dict[str, str]:
    """
    Devuelve información pública del certificado.
    Nunca devuelve la clave privada.
    """

    cert = loaded.certificate

    subject = cert.subject.rfc4514_string()
    issuer = cert.issuer.rfc4514_string()

    fingerprint = cert.fingerprint(
        hashes.SHA256()
    ).hex()

    return {
        "subject": subject,
        "issuer": issuer,
        "serial_number": str(cert.serial_number),
        "not_before": (
            cert.not_valid_before_utc.isoformat()
        ),
        "not_after": (
            cert.not_valid_after_utc.isoformat()
        ),
        "sha256_fingerprint": fingerprint,
    }