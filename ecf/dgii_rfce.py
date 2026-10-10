"""DGII RFCE reception client.

RFCE reception returns the validation result directly; it does not return an
ECF TrackId and must not use the ECF result-polling endpoint.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import requests

from .dgii_auth import DGIIAuthenticationError
from .exceptions import DGIIReceptionError

logger = logging.getLogger(__name__)

RFCE_RECEPTION_BASE_URLS = {
    "precert": "https://fc.dgii.gov.do/testecf/recepcionfc",
    "cert": "https://fc.dgii.gov.do/Certecf/recepcionfc",
    "prod": "https://fc.dgii.gov.do/ecf/recepcionfc",
}


@dataclass(frozen=True)
class RFCEMessage:
    code: str
    value: str


@dataclass(frozen=True)
class RFCEReceipt:
    code: int
    status: str
    encf: str
    sequence_used: bool
    messages: list[RFCEMessage]
    raw_response: dict[str, Any]


class DGIIRFCEClient:
    def __init__(
        self,
        environment: str = "precert",
        timeout_seconds: int = 30,
        base_url: str | None = None,
    ):
        environment = environment.strip().lower()
        if base_url:
            root = base_url.rstrip("/")
        else:
            try:
                root = RFCE_RECEPTION_BASE_URLS[environment]
            except KeyError as exc:
                raise ValueError(
                    "environment debe ser precert, cert o prod."
                ) from exc
        self.reception_url = root + "/api/recepcion/ecf"
        self.timeout_seconds = timeout_seconds

    def send_rfce(
        self,
        signed_xml: bytes,
        token: str,
        filename: str,
    ) -> RFCEReceipt:
        if not token:
            raise DGIIAuthenticationError("Falta el token DGII.")
        if not signed_xml:
            raise DGIIReceptionError("El XML RFCE firmado está vacío.")
        if not filename.lower().endswith(".xml"):
            raise DGIIReceptionError("El nombre debe terminar en .xml.")

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }
        files = {"xml": (filename, signed_xml, "text/xml")}

        try:
            response = requests.post(
                self.reception_url,
                headers=headers,
                files=files,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            # A timeout/connection failure is an uncertain send. The caller
            # must not retry automatically because DGII may have received it.
            raise DGIIReceptionError(
                "No se pudo confirmar la respuesta de recepción RFCE. "
                "El resultado del envío es incierto; concilia antes de reintentar."
            ) from exc

        if not response.ok:
            logger.error(
                "Recepción RFCE HTTP %s: %s",
                response.status_code,
                response.text[:2000],
            )
            raise DGIIReceptionError(
                f"Recepción RFCE devolvió HTTP {response.status_code}: "
                f"{response.text[:1000]}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise DGIIReceptionError(
                "La respuesta de recepción RFCE no es JSON válido; "
                "no reintentes hasta confirmar el resultado."
            ) from exc

        if not isinstance(data, dict):
            raise DGIIReceptionError(
                "Formato inesperado en la respuesta de recepción RFCE."
            )

        try:
            code = int(data.get("codigo") or 0)
        except (TypeError, ValueError) as exc:
            raise DGIIReceptionError(
                "La respuesta RFCE no contiene un código válido."
            ) from exc

        raw_messages = data.get("mensajes") or []
        if not isinstance(raw_messages, list):
            raise DGIIReceptionError(
                "El campo mensajes de la respuesta RFCE no es una lista."
            )

        messages = []
        for item in raw_messages:
            if not isinstance(item, dict):
                continue
            messages.append(
                RFCEMessage(
                    code=str(item.get("codigo") or ""),
                    value=str(item.get("valor") or ""),
                )
            )

        return RFCEReceipt(
            code=code,
            status=str(data.get("estado") or ""),
            encf=str(data.get("encf") or ""),
            sequence_used=bool(data.get("secuenciaUtilizada", False)),
            messages=messages,
            raw_response=data,
        )
