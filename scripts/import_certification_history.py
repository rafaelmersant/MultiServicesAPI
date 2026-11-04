"""Import existing DGII certification test results into the Django e-CF table.

This command never sends documents. It verifies the saved XML signatures, XSDs,
registry hashes and results before creating missing ElectronicInvoice rows.
Run with --apply to persist; the default is a dry run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from django.utils import timezone
from lxml import etree

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env", override=False)

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MultiServices.settings")
django.setup()

from administration.models import Company
from ecf.certificate import load_pkcs12
from ecf.config import Settings
from ecf.models import ECFEnvironment, ElectronicInvoice, RFCEStatus
from ecf.signing import verify_xml_signature
from ecf.test_run_registry import ECFTestRegistry
from ecf.test_set_loader import certification_order, load_test_set
from ecf.xml_utils import validate_xsd


EXCEL = PROJECT_ROOT / "backups/dgii_day5/132018559-07102026102146.xlsx"
ECF_DIR = PROJECT_ROOT / "test_data/ecf/cert/ecf"
RFCE_DIR = PROJECT_ROOT / "test_data/ecf/cert/rfce"
ECF_REGISTRY_DB = PROJECT_ROOT / "test_data/ecf/test_run_registry_cert.sqlite3"
RFCE_REGISTRY_DB = PROJECT_ROOT / "test_data/ecf/test_run_registry_cert_rfce.sqlite3"
ISSUER_RNC = "132018559"
SMALL_E32_CASES = {
    f"{ISSUER_RNC}E320000000012",
    f"{ISSUER_RNC}E320000000013",
    f"{ISSUER_RNC}E320000000014",
    f"{ISSUER_RNC}E320000000015",
}


def read_identity(xml_data: bytes) -> tuple[str, str, str]:
    root = etree.fromstring(
        xml_data,
        etree.XMLParser(resolve_entities=False, no_network=True),
    )
    def value(name: str) -> str:
        nodes = root.xpath(f".//*[local-name()='{name}']")
        return (nodes[0].text or "").strip() if nodes else ""
    return value("RNCEmisor"), value("eNCF"), value("TipoeCF")


def read_rfce_identity(xml_data: bytes) -> tuple[str, str]:
    root = etree.fromstring(
        xml_data,
        etree.XMLParser(resolve_entities=False, no_network=True),
    )
    def value(name: str) -> str:
        nodes = root.xpath(f".//*[local-name()='{name}']")
        return (nodes[0].text or "").strip() if nodes else ""
    return value("RNCEmisor"), value("eNCF")


def parse_datetime(value: str | None):
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    return timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed


def xsd_path(document_type: str) -> Path:
    return PROJECT_ROOT / "xsd" / f"ECF{document_type}V1.0.xsd"


def prepare_sources(certificate):
    if not EXCEL.is_file():
        raise FileNotFoundError(f"No existe el set de certificación: {EXCEL}")
    for path in (ECF_REGISTRY_DB, RFCE_REGISTRY_DB):
        if not path.is_file():
            raise FileNotFoundError(f"No existe el registro existente: {path}")

    summary = load_test_set(EXCEL)
    primary_cases = certification_order(summary)
    small_cases = [case for case in summary.ecf_cases if case.case_id in SMALL_E32_CASES]
    if len(primary_cases) != 21 or len(small_cases) != 4 or len(summary.rfce_cases) != 4:
        raise ValueError("La composición del set de pruebas no coincide con los 21 e-CF y 4 RFCE esperados.")

    ecf_registry = ECFTestRegistry(ECF_REGISTRY_DB)
    rfce_registry = ECFTestRegistry(RFCE_REGISTRY_DB)
    company = Company.objects.get(rnc=ISSUER_RNC)
    prepared = []

    for case in primary_cases + small_cases:
        signed_path = ECF_DIR / f"{case.case_id}_firmado.xml"
        if not signed_path.is_file():
            raise FileNotFoundError(f"Falta el XML firmado para {case.case_id}.")
        signed_xml = signed_path.read_bytes()
        rnc, encf, document_type = read_identity(signed_xml)
        if (rnc, encf, document_type) != (ISSUER_RNC, case.encf, case.tipo_ecf):
            raise ValueError(f"Identidad XML no coincide con el Excel: {case.case_id}.")
        verify_xml_signature(signed_xml, certificate)
        validate_xsd(signed_xml, xsd_path(document_type))

        record = ecf_registry.get(ISSUER_RNC, case.encf)
        data = {
            "case": case,
            "company": company,
            # Retain the exact signed artifact used/required by DGII. The
            # test set's unsigned drafts are not necessarily independently
            # XSD-valid and are not needed for portal upload or audit.
            "raw_xml": "",
            "signed_xml": signed_xml.decode("utf-8"),
            "xml_hash": hashlib.sha256(signed_xml).hexdigest(),
        }

        if case.case_id in SMALL_E32_CASES:
            if record is not None:
                raise ValueError(f"El ECF pequeño {case.encf} tiene un envío directo registrado; requiere conciliación manual.")
            rfce_record = rfce_registry.get(ISSUER_RNC, case.encf)
            if not rfce_record or rfce_record.status != "accepted" or rfce_record.dgii_code != 1:
                raise ValueError(f"El RFCE de {case.encf} no aparece aceptado en el registro.")
            rfce_signed_path = RFCE_DIR / f"{case.case_id}_rfce_firmado.xml"
            rfce_result_path = RFCE_DIR / f"{case.case_id}_rfce_firmado_resultado_dgii.json"
            if not all(path.is_file() for path in (rfce_signed_path, rfce_result_path)):
                raise FileNotFoundError(f"Faltan artefactos RFCE para {case.case_id}.")
            signed_rfce = rfce_signed_path.read_bytes()
            if read_rfce_identity(signed_rfce) != (ISSUER_RNC, case.encf):
                raise ValueError(f"La identidad del RFCE no coincide: {case.case_id}.")
            if hashlib.sha256(signed_rfce).hexdigest() != rfce_record.xml_sha256:
                raise ValueError(f"El hash RFCE no coincide con su registro: {case.case_id}.")
            verify_xml_signature(signed_rfce, certificate)
            validate_xsd(signed_rfce, PROJECT_ROOT / "xsd/RFCE32V1.0.xsd")
            result_data = json.loads(rfce_result_path.read_text(encoding="utf-8"))
            if (
                result_data.get("eNCF") != case.encf
                or result_data.get("codigo") != 1
                or str(result_data.get("estado", "")).casefold() != "aceptado"
                or result_data.get("secuenciaUtilizada") is not True
            ):
                raise ValueError(f"El acuse RFCE no coincide con el resultado aceptado: {case.case_id}.")
            data.update(
                status=ElectronicInvoice.Status.READY,
                rfce_xml="",
                signed_rfce_xml=signed_rfce.decode("utf-8"),
                rfce_status=RFCEStatus.ACCEPTED,
                rfce_code=rfce_record.dgii_code,
                rfce_status_text=rfce_record.dgii_status or "Aceptado",
                rfce_messages=result_data.get("mensajes") or [],
                rfce_sequence_used=rfce_record.sequence_used,
                rfce_resolved_at=parse_datetime(rfce_record.result_at),
                last_error="",
            )
        else:
            if not record or record.status != "accepted" or record.dgii_code != 1 or not record.track_id:
                raise ValueError(f"El e-CF {case.encf} no figura aceptado con TrackId.")
            if hashlib.sha256(signed_xml).hexdigest() != record.xml_sha256:
                raise ValueError(f"El hash firmado no coincide con el registro DGII local: {case.case_id}.")
            result_path = ECF_DIR / f"{case.case_id}_sin_firma_resultado.json"
            result_data = json.loads(result_path.read_text(encoding="utf-8"))
            if (
                result_data.get("trackId") != record.track_id
                or result_data.get("rnc") != ISSUER_RNC
                or result_data.get("eNCF") != case.encf
                or result_data.get("codigo") != 1
                or str(result_data.get("estado", "")).casefold() != "aceptado"
            ):
                raise ValueError(f"El resultado guardado no coincide con el registro: {case.case_id}.")
            data.update(
                status=ElectronicInvoice.Status.ACCEPTED,
                track_id=record.track_id,
                dgii_code=record.dgii_code,
                dgii_status=record.dgii_status or "Aceptado",
                dgii_messages=result_data.get("mensajes") or [],
                sent_at=parse_datetime(record.sent_at),
                resolved_at=parse_datetime(record.result_at),
            )

        existing = ElectronicInvoice.objects.filter(encf=case.encf).first()
        if existing:
            if existing.company_id != company.pk or existing.environment != ECFEnvironment.CERT:
                raise ValueError(f"El e-NCF {case.encf} ya está asociado a otro emisor o ambiente.")
            if existing.xml_hash and existing.xml_hash != data["xml_hash"]:
                raise ValueError(f"El e-NCF {case.encf} ya existe con otro XML; no se sobrescribirá.")
            data["existing"] = existing
        else:
            data["existing"] = None
        prepared.append(data)

    return prepared


def main() -> int:
    parser = argparse.ArgumentParser(description="Importa historial local de pruebas DGII; nunca envía comprobantes.")
    parser.add_argument("--apply", action="store_true", help="Persiste filas nuevas después de validar todos los artefactos.")
    args = parser.parse_args()

    settings = Settings.from_env()
    if settings.environment != "cert":
        parser.error("La importación de historial exige DGII_ENVIRONMENT=cert.")
    certificate = load_pkcs12(settings.certificate_path, settings.certificate_password)
    prepared = prepare_sources(certificate)
    new_rows = [item for item in prepared if item["existing"] is None]
    existing_rows = len(prepared) - len(new_rows)
    print(f"XML firmados y XSD validados: {len(prepared)} e-CF; 4 RFCE asociados verificados.")
    print(f"Aceptados por consulta DGII: {sum(item['status'] == ElectronicInvoice.Status.ACCEPTED for item in prepared)}.")
    print(f"Listos para carga portal (E32 menor de DOP 250,000): {sum(item['status'] == ElectronicInvoice.Status.READY for item in prepared)}.")
    print(f"Filas nuevas: {len(new_rows)}; filas ya existentes conciliadas: {existing_rows}.")
    if not args.apply:
        print("DRY RUN: no se modificó la base Django. Usa --apply para crear las filas verificadas.")
        return 0

    from django.db import transaction

    with transaction.atomic():
        for item in new_rows:
            case = item["case"]
            ElectronicInvoice.objects.create(
                company=item["company"],
                environment=ECFEnvironment.CERT,
                document_type=case.tipo_ecf,
                encf=case.encf,
                payload={"certification_case_id": case.case_id, "imported_from_verified_history": True},
                raw_xml=item["raw_xml"],
                signed_xml=item["signed_xml"],
                xml_hash=item["xml_hash"],
                status=item["status"],
                **{key: value for key, value in item.items() if key in {
                    "track_id", "dgii_code", "dgii_status", "dgii_messages", "sent_at", "resolved_at",
                    "rfce_xml", "signed_rfce_xml", "rfce_status", "rfce_code", "rfce_status_text",
                    "rfce_messages", "rfce_sequence_used", "rfce_resolved_at", "last_error",
                }},
            )
    print(f"Importación completada: {len(new_rows)} filas creadas; no hubo solicitudes de envío a DGII.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
