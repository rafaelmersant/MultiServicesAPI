"""Send DGII ACECF commercial approvals in certification only.

Safe by default: without --confirm-send, this script only checks files and
prints the endpoint. It never retries automatically.
"""
import argparse
import argparse
import os
import sys
from pathlib import Path
from urllib.parse import urljoin

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import requests
from dotenv import load_dotenv
from lxml import etree

from ecf.certificate import load_pkcs12
from ecf.config import Settings
from ecf.dgii_auth import DGIIAuthenticator


CERT_APPROVAL_ENDPOINT = (
    "https://ecf.dgii.gov.do/certecf/"
    "aprobacioncomercial/api/aprobacioncomercial"
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Envía XML ACECF a DGII certificación. Sin --confirm-send no transmite."
    )
    parser.add_argument(
        "--input-dir",
        default="test_data/acecf/generated",
        help="Carpeta con archivos *_firmado.xml",
    )
    parser.add_argument(
        "--file",
        help="Envía solo este XML firmado (ruta relativa o absoluta).",
    )
    parser.add_argument(
        "--confirm-send",
        action="store_true",
        help="Autoriza el envío real a DGII certificación.",
    )
    args = parser.parse_args()

    load_dotenv(PROJECT_ROOT / ".env", override=False)

    environment = os.getenv("DGII_ENVIRONMENT", "").strip().lower()
    if environment != "cert":
        raise SystemExit(
            f"Bloqueado: DGII_ENVIRONMENT debe ser 'cert', actual={environment or '(vacío)'}."
        )

    if args.file:
        files_to_send = [Path(args.file)]
    else:
        files_to_send = sorted(Path(args.input_dir).glob("*_firmado.xml"))

    if not files_to_send:
        raise SystemExit("No se encontraron archivos *_firmado.xml.")

    # Local preflight: parse each file, ensure it has a root and XML Signature.
    for path in files_to_send:
        if not path.is_file():
            raise SystemExit(f"No existe el archivo: {path}")
        try:
            root = etree.fromstring(
                path.read_bytes(),
                parser=etree.XMLParser(resolve_entities=False, no_network=True),
            )
        except (OSError, etree.XMLSyntaxError) as exc:
            raise SystemExit(f"XML inválido o ilegible {path}: {exc}") from exc
        signature = root.xpath(
            "//*[local-name()='Signature' and namespace-uri()='http://www.w3.org/2000/09/xmldsig#']"
        )
        if not signature:
            raise SystemExit(f"El XML no contiene Signature XMLDSIG: {path}")
        print(f"PRECHECK OK | {path}")

    print(f"Ambiente: {environment}")
    print(f"Endpoint: {CERT_APPROVAL_ENDPOINT}")
    print(f"Archivos: {len(files_to_send)}")

    if not args.confirm_send:
        print("DRY RUN: no se autenticó ni se enviaron archivos.")
        print("Para enviar un único archivo, agrega --file <ruta> --confirm-send.")
        return 0

    settings = Settings.from_env()
    certificate = load_pkcs12(
        settings.certificate_path,
        settings.certificate_password,
    )
    authenticator = DGIIAuthenticator(settings, certificate)
    token_data = authenticator.authenticate()

    headers = {
        "Authorization": f"Bearer {token_data.token}",
        "Accept": "application/json",
    }

    session = requests.Session()
    sent_any = False
    failures = 0

    for path in files_to_send:
        print(f"ENVIANDO | {path.name}")
        try:
            with path.open("rb") as stream:
                response = session.post(
                    CERT_APPROVAL_ENDPOINT,
                    headers=headers,
                    files={"xml": (path.name, stream, "text/xml")},
                    timeout=settings.request_timeout_seconds,
                )
        except requests.RequestException as exc:
            failures += 1
            print(
                f"RESULTADO INCIERTO | {path.name} | {type(exc).__name__}: {exc}"
            )
            print("No reintentar automáticamente; verificar estado antes de reenviar.")
            continue

        sent_any = True
        body = response.text.strip()
        print(f"HTTP {response.status_code} | {path.name}")
        if body:
            print(f"RESPUESTA DGII | {body[:2000]}")

        if response.status_code == 200:
            print(f"ACEPTADO POR ENDPOINT | {path.name}")
        else:
            failures += 1
            print(f"NO CONFIRMADO | {path.name}")
            print("No reintentar automáticamente; revisar respuesta y portal DGII.")

    print(
        f"Resumen: {len(files_to_send)} procesados; "
        f"{len(files_to_send) - failures} HTTP 200; {failures} no confirmados."
    )
    return 0 if sent_any and failures == 0 else (2 if failures else 0)


if __name__ == "__main__":
    raise SystemExit(main())
