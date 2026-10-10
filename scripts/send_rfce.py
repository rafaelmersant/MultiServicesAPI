"""Send one previously signed RFCE to DGII and save its direct response.

This script sends a real request to DGII. Run only after reviewing the XML,
confirming the e-NCF has not already been submitted, and backing up the registry.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from lxml import etree

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from ecf.certificate import load_pkcs12
from ecf.config import Settings
from ecf.dgii_auth import DGIIAuthenticator
from ecf.dgii_rfce import DGIIRFCEClient
from ecf.exceptions import DGIIReceptionError
from ecf.signing import verify_xml_signature
from ecf.test_run_registry import ECFTestRegistry, DuplicateECFError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def read_rfce_identity(xml_data: bytes) -> tuple[str, str]:
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    try:
        root = etree.fromstring(xml_data, parser)
    except etree.XMLSyntaxError as exc:
        raise ValueError("El archivo no contiene XML válido.") from exc

    if etree.QName(root).localname != "RFCE":
        raise ValueError("El elemento raíz debe ser RFCE.")

    def value(name: str) -> str:
        nodes = root.xpath(f".//*[local-name()='{name}']")
        return (nodes[0].text or "").strip() if nodes else ""

    rnc = value("RNCEmisor")
    encf = value("eNCF")
    if not rnc or not encf:
        raise ValueError("El RFCE debe contener RNCEmisor y eNCF.")
    return rnc, encf


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Envía un RFCE firmado a DGII. Este comando realiza un envío real."
    )
    parser.add_argument("--xml", required=True, help="Ruta del RFCE firmado.")
    parser.add_argument(
        "--case-id",
        required=True,
        help="Identificador CasoPrueba del Excel, por ejemplo 132018559E320000000012.",
    )
    parser.add_argument(
        "--confirm-send",
        action="store_true",
        help="Confirmación obligatoria para realizar una petición real a DGII.",
    )
    parser.add_argument(
        "--result-json",
        help="Ruta opcional para guardar la respuesta JSON. Por defecto junto al XML.",
    )
    args = parser.parse_args()

    if not args.confirm_send:
        parser.error(
            "No se realizó ningún envío. Agrega --confirm-send solo después de revisar "
            "el XML y confirmar que el e-NCF no fue enviado previamente."
        )

    try:
        load_dotenv()
        settings = Settings.from_env()
        xml_path = Path(args.xml)
        if not xml_path.is_file():
            raise FileNotFoundError(f"No existe el XML: {xml_path}")

        signed_xml = xml_path.read_bytes()
        rnc, encf = read_rfce_identity(signed_xml)
        filename = f"{rnc}{encf}.xml"

        # Verify the signature locally before any network call.
        certificate = load_pkcs12(
            settings.certificate_path,
            settings.certificate_password,
        )
        verify_xml_signature(signed_xml, certificate)
        logger.info("Firma RFCE verificada localmente. RNC=%s e-NCF=%s", rnc, encf)

        authenticator = DGIIAuthenticator(settings=settings, certificate=certificate)
        token_data = authenticator.authenticate()
        token = token_data.token

        registry = ECFTestRegistry()
        # Reserve immediately before the RFCE POST. If already registered,
        # abort; if the POST outcome is uncertain, the reservation remains
        # "sending" and must be reconciled manually.
        registry.reserve_send(
            rnc=rnc,
            encf=encf,
            case_id=args.case_id,
            tipo_ecf="RFCE-32",
            signed_xml=signed_xml,
        )

        client = DGIIRFCEClient(
            environment=settings.environment,
            timeout_seconds=settings.request_timeout_seconds,
        )
        # No automatic retry on timeout.
        receipt = client.send_rfce(
            signed_xml=signed_xml,
            token=token,
            filename=filename,
        )

        registry.mark_result(
            rnc=rnc,
            encf=encf,
            code=receipt.code,
            status=receipt.status,
            sequence_used=receipt.sequence_used,
            notes="; ".join(
                f"{message.code}: {message.value}"
                for message in receipt.messages
                if message.value
            ) or None,
        )

        result_path = (
            Path(args.result_json)
            if args.result_json
            else xml_path.with_name(f"{xml_path.stem}_resultado_dgii.json")
        )
        result_data = {
            "tipoDocumento": "RFCE",
            "caseId": args.case_id,
            "filename": filename,
            "rnc": rnc,
            "eNCF": encf,
            "codigo": receipt.code,
            "estado": receipt.status,
            "secuenciaUtilizada": receipt.sequence_used,
            "mensajes": [
                {"codigo": m.code, "valor": m.value}
                for m in receipt.messages
            ],
            "respuestaOriginal": receipt.raw_response,
        }
        result_path.write_text(
            json.dumps(result_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print(f"Estado DGII RFCE: {receipt.status}")
        print(f"Código: {receipt.code}")
        print(f"Secuencia utilizada: {receipt.sequence_used}")
        print(f"Resultado guardado: {result_path}")
        for message in receipt.messages:
            print(f"Mensaje {message.code}: {message.value}")

        # Use the returned status text to distinguish conditional acceptance;
        # do not assume undocumented numeric RFCE status mappings.
        normalized_status = receipt.status.strip().casefold()
        if normalized_status == "aceptado":
            return 0
        if normalized_status == "aceptado condicional":
            return 2
        return 1

    except DuplicateECFError as exc:
        logger.error("Envío bloqueado por posible duplicado: %s", exc)
        return 1
    except Exception as exc:
        logger.exception("Falló el envío RFCE: %s", type(exc).__name__)
        print(f"ERROR: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
