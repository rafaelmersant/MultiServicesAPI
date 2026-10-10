
import logging
import time
from dataclasses import dataclass
from typing import Any

import requests

from .dgii_auth import DGIIAuthenticationError
from .exceptions import DGIIReceptionError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReceptionResponse:
    track_id: str
    error: str
    message: str


@dataclass(frozen=True)
class ECFResult:
    track_id: str
    code: int
    status: str
    rnc: str
    encf: str
    sequence_used: bool
    reception_date: str
    messages: list


class DGIIReceptionClient:
    def __init__(
        self,
        reception_base_url: str,
        result_base_url: str,
        timeout_seconds: int = 30,
    ):
        self.reception_url = (
            reception_base_url.rstrip("/")
            + "/api/facturaselectronicas"
        )
        self.result_url = (
            result_base_url.rstrip("/")
            + "/api/consultas/estado"
        )
        self.timeout_seconds = timeout_seconds

    def send_ecf(
        self,
        signed_xml: bytes,
        token: str,
        filename: str,
    ) -> ReceptionResponse:
        if not token:
            raise DGIIAuthenticationError("Falta el token DGII.")
        if not signed_xml:
            raise DGIIReceptionError("El XML firmado está vacío.")
        if not filename.lower().endswith(".xml"):
            raise DGIIReceptionError("El nombre debe terminar en .xml.")

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }
        files = {
            "xml": (filename, signed_xml, "text/xml"),
        }

        try:
            response = requests.post(
                self.reception_url,
                headers=headers,
                files=files,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise DGIIReceptionError(
                "No fue posible conectar con recepción DGII."
            ) from exc

        if not response.ok:
            # No registrar el token ni cabeceras de autorización.
            logger.error(
                "Recepción DGII HTTP %s: %s",
                response.status_code,
                response.text[:2000],
            )
            raise DGIIReceptionError(
                f"Recepción DGII devolvió HTTP {response.status_code}: "
                f"{response.text[:1000]}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise DGIIReceptionError(
                "La respuesta de recepción no es JSON válido."
            ) from exc

        if not isinstance(data, dict):
            raise DGIIReceptionError(
                "Formato inesperado en la respuesta de recepción."
            )

        track_id = str(data.get("trackId") or "")
        error = str(data.get("error") or "")
        message = str(data.get("mensaje") or "")

        logger.info(
            "Respuesta de recepción recibida. TrackId presente: %s",
            bool(track_id),
        )

        return ReceptionResponse(
            track_id=track_id,
            error=error,
            message=message,
        )

    def get_result(self, track_id: str, token: str) -> ECFResult:
        if not track_id:
            raise DGIIReceptionError("Falta el TrackId.")
        if not token:
            raise DGIIAuthenticationError("Falta el token DGII.")

        try:
            response = requests.get(
                self.result_url,
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                params={"trackid": track_id},
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise DGIIReceptionError(
                "No fue posible consultar el resultado DGII."
            ) from exc

        if not response.ok:
            logger.error(
                "Consulta resultado DGII HTTP %s: %s",
                response.status_code,
                response.text[:2000],
            )
            raise DGIIReceptionError(
                f"Consulta DGII HTTP {response.status_code}: "
                f"{response.text[:1000]}"
            )

        try:
            data: dict[str, Any] = response.json()
        except ValueError as exc:
            raise DGIIReceptionError(
                "La respuesta de consulta no es JSON válido."
            ) from exc

        if not isinstance(data, dict):
            raise DGIIReceptionError(
                "Formato inesperado en la consulta de resultado."
            )

        try:
            return ECFResult(
                track_id=str(data.get("trackId") or track_id),
                code=int(data.get("codigo") or 0),
                status=str(data.get("estado") or ""),
                rnc=str(data.get("rnc") or ""),
                encf=str(data.get("eNCF") or data.get("encf") or ""),
                sequence_used=bool(data.get("secuenciaUtilizada", False)),
                reception_date=str(data.get("fechaRecepcion") or ""),
                messages=data.get("mensajes") or [],
            )
        except (TypeError, ValueError) as exc:
            raise DGIIReceptionError(
                "No se pudieron interpretar los campos de la respuesta DGII."
            ) from exc

    def wait_for_result(
        self,
        track_id: str,
        token: str,
        max_attempts: int = 10,
        wait_seconds: int = 3,
    ) -> ECFResult:
        last_result = None

        for attempt in range(1, max_attempts + 1):
            logger.info(
                "Consulta del TrackId, intento %s/%s",
                attempt,
                max_attempts,
            )
            result = self.get_result(track_id, token)
            last_result = result

            logger.info(
                "Estado DGII: %s (código %s)",
                result.status,
                result.code,
            )

            if result.code != 3:
                return result

            if attempt < max_attempts:
                time.sleep(wait_seconds)

        return last_result
