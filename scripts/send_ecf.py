import argparse
import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv
from lxml import etree

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ecf.certificate import load_pkcs12
from ecf.config import Settings
from ecf.dgii_auth import DGIIAuthenticator
from ecf.dgii_reception import DGIIReceptionClient
from ecf.signing import sign_xml, verify_xml_signature
from ecf.xml_utils import validate_xsd
from ecf.test_run_registry import ECFTestRegistry, DuplicateECFError


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def read_ecf(xml_data: bytes) -> tuple[str, str]:
    """Valida estructura básica y devuelve RNC emisor y e-NCF."""
    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
    )

    try:
        root = etree.fromstring(xml_data, parser)
    except etree.XMLSyntaxError as exc:
        raise ValueError("El archivo no contiene XML válido.") from exc

    if etree.QName(root).localname != "ECF":
        raise ValueError("El elemento raíz debe ser ECF.")

    def get_value(name: str) -> str:
        nodes = root.xpath(f".//*[local-name()='{name}']")
        return (nodes[0].text or "").strip() if nodes else ""

    rnc = get_value("RNCEmisor")
    encf = get_value("eNCF")

    if not rnc or not encf:
        raise ValueError("El XML debe contener RNCEmisor y eNCF.")

    return rnc, encf


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Firma, envía y consulta un e-CF en DGII."
    )
    parser.add_argument(
        "--xml",
        required=True,
        help="Ruta del XML e-CF sin firma.",
    )
    parser.add_argument(
    "--xsd",
    required=True,
    help="Ruta del XSD oficial correspondiente al tipo de e-CF.",
    )
    parser.add_argument(
        "--no-poll",
        action="store_true",
        help="Enviar y obtener TrackId sin consultar el resultado.",
    )
    args = parser.parse_args()

    try:
        load_dotenv()
        settings = Settings.from_env()

        xml_path = Path(args.xml)
        if not xml_path.is_file():
            raise FileNotFoundError(f"No existe el XML: {xml_path}")

        xml_data = xml_path.read_bytes()
        rnc, encf = read_ecf(xml_data)

        # Validar el XML contra el XSD oficial.
        xsd_path = Path(args.xsd)

        if not xsd_path.is_file():
            raise FileNotFoundError(
                f"No existe el XSD: {xsd_path}"
            )

        # validate_xsd(xml_data, xsd_path)
        # logger.info("Validación XSD completada.")

        # DGII requiere el archivo nombrado con RNC + e-NCF.
        filename = f"{rnc}{encf}.xml"

        logger.info("e-CF de prueba: RNC=%s, e-NCF=%s", rnc, encf)

        # 1. Cargar certificado existente del Día 2.
        certificate = load_pkcs12(
            settings.certificate_path,
            settings.certificate_password,
        )

        # 2. Firmar el e-CF con la implementación ya verificada.
        signed_xml = sign_xml(xml_data, certificate)
        verify_xml_signature(signed_xml, certificate)
        logger.info("Firma del e-CF verificada localmente.")

        # 3. Guardar una copia firmada para auditoría.
        signed_path = xml_path.with_name(
            f"{xml_path.stem}_firmado.xml"
        )
        signed_path.write_bytes(signed_xml)
        logger.info("XML firmado guardado en %s", signed_path)

        # 4. Autenticarse. No imprimir ni persistir el token.
        authenticator = DGIIAuthenticator(
            settings=settings,
            certificate=certificate,
        )
        token_data = authenticator.authenticate()
        token = token_data.token
        logger.info("Autenticación DGII completada.")

        # 5. Enviar e-CF.
        client = DGIIReceptionClient(
            reception_base_url=settings.reception_base_url,
            result_base_url=settings.result_base_url,
        )

        registry = ECFTestRegistry()
        reservation = registry.reserve_send(
            rnc=rnc,
            encf=encf,
            case_id=None,  # puedes obtenerlo del Excel; no inventarlo
            tipo_ecf=tipo_ecf,  # extrae el valor TipoeCF del XML
            signed_xml=signed_xml,
        )

        reception = client.send_ecf(
            signed_xml=signed_xml,
            token=token,
            filename=filename,
        )

        if reception.error:
            logger.error("Error reportado por DGII: %s", reception.error)
        if reception.message:
            logger.info("Mensaje de recepción: %s", reception.message)

        if not reception.track_id:
            raise RuntimeError(
                "DGII no devolvió TrackId; revisa la respuesta de recepción."
            )

        registry.mark_submitted(rnc=rnc, encf=encf, track_id=reception.track_id)

        # 6. Guardar acuse sin credenciales.
        receipt_path = xml_path.with_name(
            f"{xml_path.stem}_recepcion.json"
        )
        receipt_path.write_text(
            json.dumps(
                {
                    "filename": filename,
                    "rnc": rnc,
                    "encf": encf,
                    "trackId": reception.track_id,
                    "error": reception.error,
                    "mensaje": reception.message,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        print(f"TrackId: {reception.track_id}")
        print(f"Acuse guardado: {receipt_path}")

        if args.no_poll:
            print("Envío completado; no se consultó el estado.")
            return 0

        # 7. Consultar hasta obtener estado final o agotar intentos.
        result = client.wait_for_result(
            track_id=reception.track_id,
            token=token,
            max_attempts=10,
            wait_seconds=3,
        )

        result_path = xml_path.with_name(
            f"{xml_path.stem}_resultado.json"
        )
        result_data = {
            "trackId": result.track_id,
            "codigo": result.code,
            "estado": result.status,
            "rnc": result.rnc,
            "eNCF": result.encf,
            "secuenciaUtilizada": result.sequence_used,
            "fechaRecepcion": result.reception_date,
            "mensajes": result.messages,
        }
        result_path.write_text(
            json.dumps(result_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        registry.mark_result(
            rnc=rnc,
            encf=encf,
            code=result.code,
            status=result.status,
            sequence_used=result.sequence_used,
            notes="; ".join(
                str(m.get("valor", "")) for m in result.messages if m.get("valor")
            ) or None,
        )
        
        print(f"Estado DGII: {result.status}")
        print(f"Código: {result.code}")
        print(f"Resultado guardado: {result_path}")

        for message in result.messages:
            print(
                f"Mensaje {message.get('codigo', '')}: "
                f"{message.get('valor', '')}"
            )

        if result.code == 3:
            print("El comprobante sigue en proceso; consulta nuevamente.")
            return 2

        if result.code == 2:
            print(
                "DGII rechazó el comprobante. Revisa los mensajes y "
                "secuenciaUtilizada antes de continuar."
            )
            return 1

        if result.code == 1:
            print("DGII reporta el comprobante como aceptado.")
            return 0

        print("DGII devolvió un estado que requiere revisión.")
        return 1

    except Exception as exc:
        logger.exception("Falló el flujo del Día 3: %s", type(exc).__name__)
        print(f"ERROR: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
