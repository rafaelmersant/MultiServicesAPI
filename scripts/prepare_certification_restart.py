"""Prepare a fresh DGII certification test run after the portal reset.

This command only builds local records and signed XML. It never calls DGII.
The fresh e-NCFs are allocated from the certification test range shown by the
DGII portal (1 through 10,000,000), after every locally known used sequence.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from decimal import Decimal
import hashlib
import os
from pathlib import Path
import re
import sys
from types import SimpleNamespace

from lxml import etree

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MultiServices.settings")

import django  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env", override=False)
django.setup()

from django.db import transaction  # noqa: E402
from administration.models import Company  # noqa: E402
from ecf.models import ECFEnvironment, ElectronicInvoice, ElectronicInvoiceSequence, RFCEStatus  # noqa: E402
from ecf.signing import sign_xml, verify_xml_signature  # noqa: E402
from ecf.test_set_loader import certification_order, load_test_set  # noqa: E402
from ecf.workflow import (  # noqa: E402
    _apply_registered_issuer_identity,
    build_rfce_from_signed_ecf,
    sign_rfce_record,
    used_encfs_for_company,
)
from ecf.xml_builder import build_ecf_xml  # noqa: E402
from ecf.xml_utils import validate_xsd  # noqa: E402


TEST_RANGE_END = 10_000_000
DEFAULT_EXCEL = PROJECT_ROOT / "test_data/132018559-07102026102146.xlsx"
DEFAULT_ATTEMPT = "portal-reset-20261017-01"
EXPECTED_PRIMARY_COUNTS = {
    "31": 4,
    "32": 2,
    "41": 2,
    "43": 2,
    "44": 2,
    "45": 2,
    "46": 2,
    "47": 2,
    "33": 1,
    "34": 2,
}


def case_rnc(case) -> str:
    return str(case.values.get("RNCEmisor") or "").strip()


def sequence_number(encf: str) -> tuple[str, int] | None:
    match = re.fullmatch(r"E(\d{2})(\d{10})", str(encf or ""))
    if not match:
        return None
    return match.group(1), int(match.group(2))


def ordered_cases(summary):
    primary = certification_order(summary)
    primary_counts = Counter(case.tipo_ecf for case in primary)
    if len(primary) != 21 or dict(primary_counts) != EXPECTED_PRIMARY_COUNTS:
        raise ValueError(f"Composición primaria inesperada: {dict(primary_counts)}")

    primary_ids = {case.case_id for case in primary}
    small = [case for case in summary.ecf_cases if case.case_id not in primary_ids]
    small.sort(key=lambda case: case.case_id)
    if len(small) != 4 or any(case.tipo_ecf != "32" for case in small):
        raise ValueError("Se esperaban cuatro e-CF tipo 32 pequeños para el paso final.")
    if any(Decimal(case.values.get("MontoTotal") or "0") >= Decimal("250000") for case in small):
        raise ValueError("Un caso colocado en la etapa E32 pequeña no es menor de DOP 250,000.")
    return primary, small


def used_high_water(rnc: str, summary) -> dict[str, int]:
    numbers: dict[str, list[int]] = defaultdict(list)
    encfs = set(used_encfs_for_company(rnc))
    encfs.update(
        ElectronicInvoice.objects.filter(company__rnc=rnc)
        .exclude(encf__isnull=True)
        .values_list("encf", flat=True)
    )
    encfs.update(case.encf for case in summary.ecf_cases)
    for encf in encfs:
        parsed = sequence_number(encf)
        if parsed:
            document_type, number = parsed
            numbers[document_type].append(number)
    return {doc_type: max(values) for doc_type, values in numbers.items()}


def build_payload_case(case, encf: str, company):
    values = dict(case.values)
    encf_keys = [key for key in values if str(key).strip().casefold() == "encf"]
    if len(encf_keys) != 1:
        raise ValueError(f"No se pudo identificar unívocamente ENCF en el caso {case.case_id}.")
    values[encf_keys[0]] = encf
    _apply_registered_issuer_identity(values, company)
    return SimpleNamespace(
        case_id=case.case_id,
        version=case.version,
        tipo_ecf=case.tipo_ecf,
        encf=encf,
        values=values,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--excel", type=Path, default=DEFAULT_EXCEL)
    parser.add_argument("--attempt", default=DEFAULT_ATTEMPT)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--apply", action="store_true", help="Crear secuencias y registros locales firmados.")
    actions.add_argument(
        "--validate-signed",
        action="store_true",
        help="Validar y firmar en memoria los casos con identidad Company, sin guardar ni enviar.",
    )
    args = parser.parse_args()

    if args.apply and ElectronicInvoice.objects.filter(
        payload__certification_attempt=args.attempt
    ).exists():
        raise SystemExit(f"El intento {args.attempt} ya existe; no se duplicará.")

    summary = load_test_set(args.excel)
    primary, small = ordered_cases(summary)
    all_cases = primary + small
    rnc_values = {case_rnc(case) for case in all_cases}
    if len(rnc_values) != 1 or not next(iter(rnc_values)):
        raise SystemExit("El set no tiene un único RNC emisor válido.")
    rnc = next(iter(rnc_values))
    expected_rnc = os.getenv("ECF_EXPECTED_TAX_ID", "").strip()
    if expected_rnc and expected_rnc != rnc:
        raise SystemExit("El RNC del set no coincide con ECF_EXPECTED_TAX_ID.")
    companies = Company.objects.filter(rnc=rnc)
    if companies.count() != 1:
        raise SystemExit("Debe existir exactamente una empresa local para el RNC del set.")
    company = companies.get()

    high_water = used_high_water(rnc, summary)
    counts = Counter(case.tipo_ecf for case in all_cases)
    print(f"Intento: {args.attempt}")
    print(f"Casos: {len(primary)} principales + {len(small)} E32 pequenos; envio habilitado: no")
    print("Orden principal:", " -> ".join(case.tipo_ecf for case in primary))
    print("Siguiente secuencia por tipo:", {
        doc_type: high_water.get(doc_type, 0) + 1
        for doc_type in sorted(counts)
    })
    if not args.apply and not args.validate_signed:
        print("Preflight solamente; no se modificó la base de datos ni se contactó a DGII.")
        return 0

    from ecf.certificate import load_pkcs12
    from ecf.config import Settings

    settings = Settings.from_env()
    if settings.environment != ECFEnvironment.CERT:
        raise SystemExit("DGII_ENVIRONMENT debe ser cert para preparar este intento.")
    certificate = load_pkcs12(settings.certificate_path, settings.certificate_password)

    if args.validate_signed:
        next_by_type = {}
        for doc_type in counts:
            sequence = ElectronicInvoiceSequence.objects.filter(
                company=company,
                environment=ECFEnvironment.CERT,
                document_type=doc_type,
            ).first()
            current = sequence.current if sequence else 0
            next_by_type[doc_type] = max(current or 0, high_water.get(doc_type, 0))

        signed_count = 0
        signed_rfce_count = 0
        for case in all_cases:
            next_by_type[case.tipo_ecf] += 1
            if next_by_type[case.tipo_ecf] > TEST_RANGE_END:
                raise SystemExit(f"Se agotó el rango de certificación del tipo {case.tipo_ecf}.")
            encf = f"E{case.tipo_ecf}{next_by_type[case.tipo_ecf]:010d}"
            adapted_case = build_payload_case(case, encf, company)
            xsd_path = PROJECT_ROOT / "xsd" / f"ECF{case.tipo_ecf}V1.0.xsd"
            unsigned_xml = build_ecf_xml(adapted_case, xsd_path, validate=True)
            signed_xml = sign_xml(unsigned_xml, certificate)
            verify_xml_signature(signed_xml, certificate)
            validate_xsd(signed_xml, xsd_path)
            root = etree.fromstring(signed_xml)
            values = {
                name: (root.xpath(f".//*[local-name()='{name}']")[0].text or "").strip()
                for name in ("RNCEmisor", "RazonSocialEmisor", "DireccionEmisor", "eNCF")
            }
            if (
                values["RNCEmisor"] != (company.rnc or "").strip()
                or values["RazonSocialEmisor"] != (company.name or "").strip()
                or values["DireccionEmisor"] != (company.address or "").strip()
                or values["eNCF"] != encf
            ):
                raise SystemExit(f"La identidad firmada no coincide con Company para {encf}.")
            signed_count += 1

            if case in small:
                rfce_record = SimpleNamespace(
                    document_type=case.tipo_ecf,
                    signed_xml=signed_xml.decode("utf-8"),
                    company=company,
                    encf=encf,
                    environment=ECFEnvironment.CERT,
                    rfce_status=RFCEStatus.DRAFT,
                    rfce_xml="",
                )
                rfce_xml = build_rfce_from_signed_ecf(rfce_record)
                rfce_record.rfce_xml = rfce_xml.decode("utf-8")
                signed_rfce = sign_rfce_record(rfce_record)
                rfce_root = etree.fromstring(signed_rfce)
                rfce_identity = {
                    name: (rfce_root.xpath(f".//*[local-name()='{name}']")[0].text or "").strip()
                    for name in ("RNCEmisor", "RazonSocialEmisor", "eNCF")
                }
                if (
                    rfce_identity["RNCEmisor"] != (company.rnc or "").strip()
                    or rfce_identity["RazonSocialEmisor"] != (company.name or "").strip()
                    or rfce_identity["eNCF"] != encf
                ):
                    raise SystemExit(f"La identidad del RFCE firmado no coincide para {encf}.")
                signed_rfce_count += 1

        print(
            f"Validación firmada correcta: {signed_count} XML e-CF y {signed_rfce_count} RFCE; "
            "todos conservan la identidad Company."
        )
        print("Se usó el certificado local; no se modificó la base de datos ni se contactó a DGII.")
        return 0

    with transaction.atomic():
        sequences = {}
        for doc_type in sorted(counts):
            sequence, created = ElectronicInvoiceSequence.objects.get_or_create(
                company=company,
                environment=ECFEnvironment.CERT,
                document_type=doc_type,
                defaults={
                    "authorized_start": 1,
                    "authorized_end": TEST_RANGE_END,
                    "current": high_water.get(doc_type, 0),
                    "active": True,
                },
            )
            if not created and (
                sequence.authorized_start != 1
                or sequence.authorized_end != TEST_RANGE_END
            ):
                raise ValueError(
                    f"El rango local del tipo {doc_type} difiere del rango de prueba DGII; no se modificó."
                )
            if not created:
                current = sequence.current or 0
                required_current = max(current, high_water.get(doc_type, 0))
                if required_current != current or not sequence.active:
                    sequence.current = required_current
                    sequence.active = True
                    sequence.save(update_fields=("current", "active"))
            sequences[doc_type] = sequence

        for case in all_cases:
            sequence = sequences[case.tipo_ecf]
            used_now = set(used_encfs_for_company(rnc))
            while True:
                encf = sequence.allocate_encf()
                if encf not in used_now and not ElectronicInvoice.objects.filter(encf=encf).exists():
                    break
            adapted_case = build_payload_case(case, encf, company)
            xsd_path = PROJECT_ROOT / "xsd" / f"ECF{case.tipo_ecf}V1.0.xsd"
            unsigned_xml = build_ecf_xml(adapted_case, xsd_path, validate=True)
            signed_xml = sign_xml(unsigned_xml, certificate)
            verify_xml_signature(signed_xml, certificate)
            validate_xsd(signed_xml, xsd_path)

            record = ElectronicInvoice.objects.create(
                company=company,
                environment=ECFEnvironment.CERT,
                sequence=sequence,
                document_type=case.tipo_ecf,
                encf=encf,
                status=ElectronicInvoice.Status.READY,
                payload={
                    "certification_attempt": args.attempt,
                    "test_case_id": case.case_id,
                },
                raw_xml=unsigned_xml.decode("utf-8"),
                signed_xml=signed_xml.decode("utf-8"),
                xml_hash=hashlib.sha256(signed_xml).hexdigest(),
                last_error="Preparado; pendiente de envío según el orden del portal DGII.",
            )

            if case in small:
                rfce_xml = build_rfce_from_signed_ecf(record)
                record.rfce_xml = rfce_xml.decode("utf-8")
                record.rfce_status = RFCEStatus.DRAFT
                record.save(update_fields=("rfce_xml", "rfce_status", "updated_at"))
                signed_rfce = sign_rfce_record(record)
                record.signed_rfce_xml = signed_rfce.decode("utf-8")
                record.rfce_status = RFCEStatus.READY
                record.save(update_fields=("signed_rfce_xml", "rfce_status", "updated_at"))

    print("Creado:", dict(counts), "| XML e-CF firmados:", len(all_cases), "| RFCE listos:", len(small))
    print("Ningún documento se envió a DGII. Envíalos siguiendo el orden mostrado arriba.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
