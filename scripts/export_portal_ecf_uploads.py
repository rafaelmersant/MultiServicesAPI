"""Export accepted-RFCE, small E32 XMLs for the DGII portal upload step."""
from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MultiServices.settings")

import django  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from lxml import etree  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env", override=False)
django.setup()

from ecf.certificate import load_pkcs12  # noqa: E402
from ecf.config import Settings  # noqa: E402
from ecf.models import ECFEnvironment, ElectronicInvoice, ElectronicInvoiceSequence, RFCEStatus  # noqa: E402
from ecf.signing import verify_xml_signature  # noqa: E402
from ecf.workflow import _validate_rfce_xml, _xsd_for_record  # noqa: E402
from ecf.xml_utils import validate_xsd  # noqa: E402


DEFAULT_ATTEMPT = "portal-reset-20261017-01"
DEFAULT_OUTPUT = PROJECT_ROOT / "test_data/ecf/cert/portal-reset-20261017-01"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", default=DEFAULT_ATTEMPT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    if not output_dir.is_relative_to(PROJECT_ROOT):
        raise SystemExit("La carpeta de salida debe estar dentro del proyecto.")
    settings = Settings.from_env()
    if settings.environment != ECFEnvironment.CERT:
        raise SystemExit("DGII_ENVIRONMENT debe ser cert.")
    certificate = load_pkcs12(settings.certificate_path, settings.certificate_password)
    candidates = ElectronicInvoice.objects.filter(
        environment=ECFEnvironment.CERT,
        payload__certification_attempt=args.attempt,
        document_type="32",
        rfce_status=RFCEStatus.ACCEPTED,
    ).select_related("company")

    small = []
    for record in candidates:
        if not record.signed_xml or not record.signed_rfce_xml:
            raise SystemExit(f"Falta XML firmado de e-CF/RFCE: {record.encf}.")
        root = etree.fromstring(
            record.signed_xml.encode("utf-8"),
            etree.XMLParser(resolve_entities=False, no_network=True),
        )
        total = Decimal((root.xpath(".//*[local-name()='MontoTotal']")[0].text or "0"))
        if total < Decimal("250000"):
            small.append(record)

    if len(small) != 4:
        raise SystemExit(f"Se esperaban cuatro E32 pequeños con RFCE aceptado; hay {len(small)}.")

    output_dir.mkdir(parents=True, exist_ok=True)
    exported = []
    for record in sorted(small, key=lambda item: item.encf or ""):
        if record.status != ElectronicInvoice.Status.READY:
            raise SystemExit(f"El e-CF {record.encf} no está pendiente de carga portal.")
        if record.track_id or record.sent_at:
            raise SystemExit(f"El e-CF {record.encf} tiene envío directo; no se exportará.")
        ecf_xml = record.signed_xml.encode("utf-8")
        rfce_xml = record.signed_rfce_xml.encode("utf-8")
        verify_xml_signature(ecf_xml, certificate)
        validate_xsd(ecf_xml, _xsd_for_record(record))
        verify_xml_signature(rfce_xml, certificate)
        _validate_rfce_xml(rfce_xml, allow_unsigned=False)

        filename = f"{record.company.rnc}{record.encf}.xml"
        destination = output_dir / filename
        if destination.exists():
            if hashlib.sha256(destination.read_bytes()).digest() != hashlib.sha256(ecf_xml).digest():
                raise SystemExit(f"Ya existe un archivo distinto; no se sobrescribirá: {destination}")
        else:
            with destination.open("xb") as stream:
                stream.write(ecf_xml)
        exported.append(destination)

    print(f"Listos para carga portal: {len(exported)} e-CF; todos con RFCE aceptado.")
    for path in exported:
        print(path)
    print("No se contactó a DGII ni se sobrescribieron archivos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
