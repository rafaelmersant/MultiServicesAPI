"""Optional seed and bearer-token service for e-CF receiver endpoints."""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone as datetime_timezone

import jwt
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from lxml import etree
from signxml import XMLVerifier

from .inbound import InboundDocumentError, _verify_certificate_chain
from .models import ECFAuthenticationChallenge


SEED_TTL = timedelta(minutes=5)
TOKEN_TTL = timedelta(hours=1)
TOKEN_ISSUER = "MultiServicesAPI"
TOKEN_AUDIENCE = "ecf-receiver"
logger = logging.getLogger(__name__)


class ECFAuthenticationError(InboundDocumentError):
    """An authentication seed or bearer token is invalid."""


class ECFAuthenticationConfigError(ECFAuthenticationError):
    """A required authentication secret is not configured."""


def _token_secret() -> str:
    secret = os.getenv("ECF_AUTH_TOKEN_SECRET", "").strip()
    if len(secret) < 32:
        raise ECFAuthenticationConfigError(
            "Configura ECF_AUTH_TOKEN_SECRET con al menos 32 caracteres aleatorios."
        )
    return secret


def issue_seed() -> HttpResponse:
    value = base64.b64encode(secrets.token_bytes(32)).decode("ascii")
    now = timezone.now()
    seed_hash = hashlib.sha256(value.encode("ascii")).hexdigest()
    ECFAuthenticationChallenge.objects.filter(expires_at__lt=now - timedelta(hours=1)).delete()
    ECFAuthenticationChallenge.objects.create(
        seed_sha256=seed_hash,
        issued_at=now,
        expires_at=now + SEED_TTL,
    )

    root = etree.Element(
        "SemillaModel",
        nsmap={
            "xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsd": "http://www.w3.org/2001/XMLSchema",
        },
    )
    etree.SubElement(root, "valor").text = value
    etree.SubElement(root, "fecha").text = timezone.localtime(now).isoformat(timespec="microseconds")
    payload = etree.tostring(root, encoding="UTF-8", xml_declaration=True)
    return HttpResponse(payload, content_type="application/xml; charset=utf-8", status=200)


def _signed_seed_parts(request) -> tuple[str, str, datetime]:
    upload = request.data.get("xml")
    if not hasattr(upload, "read"):
        raise ECFAuthenticationError("Envía la semilla firmada en el campo multipart 'xml'.")
    xml_data = upload.read()
    if not xml_data or len(xml_data) > 1_000_000:
        raise ECFAuthenticationError("La semilla firmada está vacía o supera 1 MB.")
    parser = etree.XMLParser(resolve_entities=False, no_network=True, recover=False)
    try:
        root = etree.fromstring(xml_data, parser=parser)
    except etree.XMLSyntaxError as exc:
        raise ECFAuthenticationError("El archivo firmado no contiene XML válido.") from exc

    if etree.QName(root).localname.casefold() != "semillamodel":
        raise ECFAuthenticationError("El XML firmado no contiene SemillaModel.")
    values = root.xpath("./*[local-name()='valor']/text()")
    if not values or not values[0].strip():
        raise ECFAuthenticationError("La semilla firmada no contiene valor.")
    value = values[0].strip()
    try:
        if len(base64.b64decode(value, validate=True)) != 32:
            raise ValueError("longitud inválida")
    except (ValueError, UnicodeEncodeError) as exc:
        raise ECFAuthenticationError("El valor de la semilla no tiene el formato emitido por este servicio.") from exc
    dates = root.xpath("./*[local-name()='fecha']/text()")
    try:
        issued_at = datetime.fromisoformat(dates[0].strip()) if dates else None
        if issued_at is None or issued_at.tzinfo is None:
            raise ValueError("fecha sin zona horaria")
    except ValueError as exc:
        raise ECFAuthenticationError("La semilla firmada no contiene una fecha válida.") from exc

    certificates = root.xpath(".//*[local-name()='X509Certificate']/text()")
    if not certificates:
        raise ECFAuthenticationError("La firma no contiene certificado X.509.")
    stage = "certificate_decode"
    certificate = None
    try:
        der = base64.b64decode("".join(certificates[0].split()), validate=True)
        certificate = x509.load_der_x509_certificate(der)
        certificate_pem = certificate.public_bytes(serialization.Encoding.PEM)
        stage = "xml_signature"
        XMLVerifier().verify(xml_data, x509_cert=certificate_pem)
        trusted_ca_path = os.getenv("ECF_AUTH_TRUSTED_CA_PATH", "").strip()
        if not trusted_ca_path:
            raise ECFAuthenticationConfigError(
                "Configura ECF_AUTH_TRUSTED_CA_PATH con las CA confiables antes de habilitar autenticación."
            )
        intermediates = [
            x509.load_der_x509_certificate(base64.b64decode("".join(value.split()), validate=True))
            for value in certificates[1:]
        ]
        stage = "certificate_chain"
        _verify_certificate_chain(certificate, intermediates, trusted_ca_path)
    except ECFAuthenticationConfigError:
        raise
    except Exception as exc:
        # Never log the signed XML, seed, bearer token or private key.
        issuer = certificate.issuer.rfc4514_string() if certificate is not None else "unknown"
        detail = " ".join(str(exc).split())[:400] if stage == "certificate_chain" else type(exc).__name__
        logger.warning("DGII_AUTH_VERIFY_FAILED stage=%s issuer=%s error=%s", stage, issuer, detail)
        raise ECFAuthenticationError("La firma de la semilla no es válida.") from exc
    fingerprint = certificate.fingerprint(hashes.SHA256()).hex()
    return value, fingerprint, issued_at


def validate_seed(request):
    value, fingerprint, signed_issued_at = _signed_seed_parts(request)
    digest = hashlib.sha256(value.encode("ascii")).hexdigest()
    now = timezone.now()
    challenge = ECFAuthenticationChallenge.objects.filter(
        seed_sha256=digest,
        consumed_at__isnull=True,
        expires_at__gt=now,
    ).first()
    if challenge is None:
        raise ECFAuthenticationError("La semilla expiró, ya fue utilizada o no fue emitida por este servicio.")
    token_secret = _token_secret()
    if abs((signed_issued_at - challenge.issued_at).total_seconds()) > 2:
        raise ECFAuthenticationError("La fecha firmada no coincide con la semilla emitida.")

    with transaction.atomic():
        consumed = ECFAuthenticationChallenge.objects.filter(
            pk=challenge.pk,
            consumed_at__isnull=True,
            expires_at__gt=now,
        ).update(consumed_at=now)
    if consumed != 1:
        raise ECFAuthenticationError("La semilla ya fue utilizada o expiró.")

    expires_at = now + TOKEN_TTL
    token = jwt.encode(
        {
            "sub": fingerprint,
            "iat": now,
            "exp": expires_at,
            "jti": secrets.token_hex(16),
            "iss": TOKEN_ISSUER,
            "aud": TOKEN_AUDIENCE,
        },
        token_secret,
        algorithm="HS256",
    )
    result = {
        "token": token,
        "expira": expires_at.astimezone(datetime_timezone.utc).isoformat().replace("+00:00", "Z"),
        "expedido": now.astimezone(datetime_timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    if "application/xml" in request.headers.get("Accept", "").casefold():
        root = etree.Element("RespuestaAutenticacion")
        for key, content in result.items():
            etree.SubElement(root, key).text = content
        payload = etree.tostring(root, encoding="UTF-8", xml_declaration=True)
        return HttpResponse(payload, content_type="application/xml; charset=utf-8", status=200)
    return result


def verify_receiver_authorization(request) -> None:
    """Require a token only when the optional auth URL is declared active."""
    if os.getenv("ECF_REQUIRE_INBOUND_AUTH", "").strip().casefold() not in {"1", "true", "yes"}:
        return
    token_secret = _token_secret()
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.casefold() != "bearer" or not token.strip():
        raise ECFAuthenticationError("Se requiere un token Bearer válido.")
    try:
        jwt.decode(
            token.strip(),
            token_secret,
            algorithms=["HS256"],
            issuer=TOKEN_ISSUER,
            audience=TOKEN_AUDIENCE,
            options={"require": ["exp", "iat", "jti", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise ECFAuthenticationError("El token Bearer es inválido o expiró.") from exc
