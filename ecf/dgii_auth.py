
import json
import logging
from dataclasses import dataclass
from urllib.parse import urljoin

import requests
from lxml import etree

from .certificate import LoadedCertificate
from .config import Settings
from .exceptions import ECFError
from .signing import sign_xml, verify_xml_signature


logger = logging.getLogger(__name__)


class DGIIAuthenticationError(ECFError):
    """Error durante la autenticación DGII."""


@dataclass(frozen=True)
class AuthenticationToken:
    token: str
    expira: str
    expedido: str


class DGIIAuthenticator:
    def __init__(
        self,
        settings: Settings,
        certificate: LoadedCertificate,
        session: requests.Session | None = None,
    ):
        self.settings = settings
        self.certificate = certificate
        self.session = session or requests.Session()

        self.session.headers.update({
            "Accept": "application/json",
        })

        self.seed_url = urljoin(
            settings.auth_base_url.rstrip("/") + "/",
            "api/autenticacion/semilla",
        )

        self.validation_url = urljoin(
            settings.auth_base_url.rstrip("/") + "/",
            "api/autenticacion/validarsemilla",
        )

    def get_seed(self) -> bytes:
        """
        Solicita la semilla a DGII.
        No transmite el certificado ni la clave privada.
        """

        try:
            response = self.session.get(
                self.seed_url,
                headers={"Accept": "application/xml, */*"},
                timeout=self.settings.request_timeout_seconds,
            )

        except requests.RequestException as exc:
            raise DGIIAuthenticationError(
                "No se pudo conectar con el endpoint de semilla."
            ) from exc

        if response.status_code != 200:
            raise DGIIAuthenticationError(
                "DGII no entregó la semilla. "
                f"HTTP {response.status_code}."
            )

        seed_xml = response.content

        try:
            root = etree.fromstring(
                seed_xml,
                parser=etree.XMLParser(
                    resolve_entities=False,
                    no_network=True,
                ),
            )

        except etree.XMLSyntaxError as exc:
            raise DGIIAuthenticationError(
                "DGII devolvió una respuesta que no es XML válido."
            ) from exc

        if etree.QName(root).localname.lower() != "semillamodel":
            raise DGIIAuthenticationError(
                "La respuesta no contiene el elemento SemillaModel."
            )

        valor = root.find(
            "{*}valor"
        )

        fecha = root.find(
            "{*}fecha"
        )

        if (
            valor is None
            or not (valor.text or "").strip()
            or fecha is None
            or not (fecha.text or "").strip()
        ):
            raise DGIIAuthenticationError(
                "La semilla no contiene valor y fecha."
            )

        logger.info(
            "Semilla recibida correctamente de DGII."
        )

        return seed_xml

    def sign_seed(
        self,
        seed_xml: bytes,
    ) -> bytes:
        """
        Firma la semilla y verifica localmente el resultado.
        """

        signed_xml = sign_xml(
            seed_xml,
            self.certificate,
        )

        verify_xml_signature(
            signed_xml,
            self.certificate,
        )

        logger.info(
            "Firma de la semilla verificada localmente."
        )

        return signed_xml

    def validate_seed(
        self,
        signed_xml: bytes,
    ) -> AuthenticationToken:
        """
        Envía la semilla firmada como multipart/form-data.

        El campo requerido por DGII es 'xml'.
        """

        files = {
            "xml": (
                "SemillaFirmada.xml",
                signed_xml,
                "text/xml",
            )
        }

        try:
            response = self.session.post(
                self.validation_url,
                files=files,
                headers={
                    "Accept": "application/json",
                },
                timeout=self.settings.request_timeout_seconds,
            )

        except requests.RequestException as exc:
            raise DGIIAuthenticationError(
                "No se pudo conectar con el endpoint de validación."
            ) from exc

        if not response.ok:
            logger.error(
                "DGII validarsemilla HTTP %s. Respuesta: %s",
                response.status_code,
                response.text,
            )

            raise DGIIAuthenticationError(
                f"DGII rechazó la validación de la semilla. "
                f"HTTP {response.status_code}. "
                f"Respuesta DGII: {response.text}"
            )

        try:
            data = response.json()

        except (ValueError, json.JSONDecodeError) as exc:
            raise DGIIAuthenticationError(
                "DGII respondió, pero el cuerpo no es JSON válido. "
                "Revisa el formato de respuesta documentado."
            ) from exc

        token = data.get("token")
        expira = data.get("expira")
        expedido = data.get("expedido")

        if not all(
            isinstance(value, str) and value.strip()
            for value in (token, expira, expedido)
        ):
            raise DGIIAuthenticationError(
                "La respuesta de DGII no contiene "
                "token, expira y expedido válidos."
            )

        logger.info(
            "DGII devolvió un token de autenticación."
        )

        return AuthenticationToken(
            token=token,
            expira=expira,
            expedido=expedido,
        )

    def authenticate(self) -> AuthenticationToken:
        """
        Ejecuta el flujo completo:
          1. Solicitar semilla
          2. Firmar semilla
          3. Validar semilla
          4. Obtener token
        """

        seed_xml = self.get_seed()

        signed_xml = self.sign_seed(
            seed_xml
        )

        return self.validate_seed(
            signed_xml
        )