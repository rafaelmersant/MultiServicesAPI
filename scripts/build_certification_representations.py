"""Build individual RIs and one merged PDF per DGII portal field."""
from __future__ import annotations

import argparse
from collections import defaultdict
from decimal import Decimal
import hashlib
import os
from pathlib import Path
import re
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MultiServices.settings")

import django  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from lxml import etree  # noqa: E402
from pypdf import PdfReader, PdfWriter  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env", override=False)
django.setup()

from django.core.files.base import ContentFile  # noqa: E402

from ecf.models import ECFEnvironment, ElectronicInvoice  # noqa: E402
from ecf.workflow import build_representation_pdf, representation_pdf_identity_is_current  # noqa: E402


DEFAULT_ATTEMPT = "portal-reset-20261017-01"
DEFAULT_OUTPUT = PROJECT_ROOT / "output/pdf/dgii-certification-portal-reset-20261017-step5"
EXPECTED = {
    "31": 4,
    "32-high": 2,
    "33": 1,
    "34": 2,
    "41": 2,
    "43": 2,
    "44": 2,
    "45": 2,
    "46": 2,
    "47": 2,
    "32-small": 4,
}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def page_has_fiscal_content(page) -> bool:
    text = page.extract_text() or ""
    body = re.sub(
        r"(?im)^.*(?:Código de Seguridad:|Fecha de Firma Digital:|Fecha Firma:|Estado DGII:|Página\s+\d+).*$",
        "",
        text,
    )
    return bool(body.strip())


def group_for(record: ElectronicInvoice) -> str:
    if record.document_type != "32":
        return record.document_type
    root = etree.fromstring(
        record.signed_xml.encode("utf-8"),
        etree.XMLParser(resolve_entities=False, no_network=True),
    )
    total = Decimal((root.xpath(".//*[local-name()='MontoTotal']")[0].text or "0"))
    return "32-high" if total >= Decimal("250000") else "32-small"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", default=DEFAULT_ATTEMPT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--refresh-individuals",
        action="store_true",
        help="Regenerar las RI individuales desde el XML firmado actual.",
    )
    parser.add_argument(
        "--registered-issuer",
        action="store_true",
        help="Exigir que nombre y dirección de Company coincidan con el XML firmado.",
    )
    parser.add_argument(
        "--one-per-type",
        action="store_true",
        help="Incluir un e-CF aceptado por cada casilla/tipo de carga de DGII.",
    )
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    if not output_dir.is_relative_to(PROJECT_ROOT):
        raise SystemExit("La carpeta de salida debe estar dentro del proyecto.")
    records = list(
        ElectronicInvoice.objects.filter(
            environment=ECFEnvironment.CERT,
            payload__certification_attempt=args.attempt,
        ).order_by("document_type", "encf")
    )
    if len(records) != 25:
        raise SystemExit(f"Se esperaban 25 comprobantes de la corrida; hay {len(records)}.")
    if any(record.status != ElectronicInvoice.Status.ACCEPTED for record in records):
        raise SystemExit("Todas las facturas e-CF deben constar aceptadas antes de crear las RI.")
    mismatched = [record.encf for record in records if not representation_pdf_identity_is_current(record)]
    if mismatched:
        raise SystemExit(
            "No se crearán ni reutilizarán RI: la identidad firmada no coincide con Company para "
            + ", ".join(mismatched)
        )

    grouped: dict[str, list[ElectronicInvoice]] = defaultdict(list)
    for record in records:
        if not record.signed_xml:
            raise SystemExit(f"Falta el XML firmado para {record.encf}.")
        grouped[group_for(record)].append(record)
    actual = {name: len(grouped.get(name, [])) for name in EXPECTED}
    if actual != EXPECTED:
        raise SystemExit(f"Composición de RI inesperada: {actual}")

    output_dir.mkdir(parents=True, exist_ok=True)
    portal_pdfs = []
    total_pages = 0
    for group, members in grouped.items():
        members = sorted(members, key=lambda item: item.encf or "")
        if args.one_per_type:
            members = members[:1]
        readers = []
        group_pages = 0
        for record in members:
            if (
                not args.refresh_individuals
                and record.representation_pdf
                and Path(record.representation_pdf.path).is_file()
            ):
                individual_path = Path(record.representation_pdf.path)
            else:
                registered_issuer = None
                if args.registered_issuer:
                    company = record.company
                    xml_root = etree.fromstring(
                        record.signed_xml.encode("utf-8"),
                        etree.XMLParser(resolve_entities=False, no_network=True),
                    )
                    xml_rnc = (xml_root.xpath(".//*[local-name()='RNCEmisor']")[0].text or "").strip()
                    xml_name = (xml_root.xpath(".//*[local-name()='RazonSocialEmisor']")[0].text or "").strip()
                    xml_address = (xml_root.xpath(".//*[local-name()='DireccionEmisor']")[0].text or "").strip()
                    company_rnc = (company.rnc or "").strip()
                    if (
                        not company.name.strip()
                        or not company_rnc
                        or company_rnc != xml_rnc
                        or company.name.strip() != xml_name
                        or (company.address or "").strip() != xml_address
                    ):
                        raise SystemExit(
                            f"La identidad legal de Company no coincide con el XML firmado para {record.encf}. "
                            "No se puede corregir solo la representación impresa; se requiere un e-CF nuevo, "
                            "generado y firmado con la identidad legal correcta."
                        )
                    registered_issuer = {
                        "name": company.name,
                        "address": company.address or "",
                    }
                pdf_data = build_representation_pdf(
                    record,
                    registered_issuer=registered_issuer,
                )
                filename = (
                    f"RI-{record.encf}-step5-corrected.pdf"
                    if args.refresh_individuals and args.registered_issuer
                    else f"RI-{record.encf}-step5.pdf"
                    if args.refresh_individuals
                    else f"RI-{record.encf}.pdf"
                )
                record.representation_pdf.save(
                    filename, ContentFile(pdf_data), save=True
                )
                individual_path = Path(record.representation_pdf.path)
            raw = individual_path.read_bytes()
            if not raw.startswith(b"%PDF-"):
                raise ValueError(f"La RI individual no es un PDF válido: {record.encf}.")
            reader = PdfReader(individual_path)
            if reader.is_encrypted or not reader.pages:
                raise ValueError(f"La RI individual está vacía o protegida: {record.encf}.")
            blank_pages = [
                page_number
                for page_number, page in enumerate(reader.pages, 1)
                if not page_has_fiscal_content(page)
            ]
            if blank_pages:
                raise ValueError(
                    f"La RI contiene páginas de continuación vacías para {record.encf}: {blank_pages}. "
                    "Regenera las RI con --refresh-individuals antes de preparar la carga."
                )
            if record.encf not in "\n".join(page.extract_text() or "" for page in reader.pages):
                raise ValueError(f"La RI individual no identifica el e-NCF {record.encf}.")
            readers.append((record.encf, individual_path, len(reader.pages)))
            group_pages += len(reader.pages)

        output_name = f"RI-{group}.pdf"
        output_path = output_dir / output_name
        if output_path.exists():
            raise SystemExit(f"No se sobrescribirá el PDF ya existente: {output_path}")
        writer = PdfWriter()
        for _, individual_path, _ in readers:
            writer.append(str(individual_path))
        with output_path.open("xb") as stream:
            writer.write(stream)
        merged = output_path.read_bytes()
        if not merged.startswith(b"%PDF-"):
            raise ValueError(f"La RI agrupada no es un PDF válido: {output_path.name}.")
        merged_reader = PdfReader(output_path)
        if len(merged_reader.pages) != group_pages:
            raise ValueError(f"El total de páginas no coincide en {output_path.name}.")
        merged_text = "\n".join(page.extract_text() or "" for page in merged_reader.pages)
        missing_encfs = [encf for encf, _, _ in readers if encf not in merged_text]
        if missing_encfs:
            raise ValueError(f"Faltan e-NCF en {output_path.name}: {missing_encfs}")
        digest = hashlib.sha256(merged).hexdigest()[:12]
        print(f"{group}: {len(readers)} e-CF, {group_pages} páginas, {len(merged)} bytes, sha256={digest}")
        portal_pdfs.append(output_path)
        total_pages += group_pages

    total_bytes = sum(path.stat().st_size for path in portal_pdfs)
    if len(portal_pdfs) != len(EXPECTED) or total_bytes > MAX_UPLOAD_BYTES:
        raise SystemExit(
            f"Los archivos exceden la cantidad/tamaño permitido: {len(portal_pdfs)} PDFs, {total_bytes} bytes."
        )
    print(f"Verificados: {len(portal_pdfs)} PDFs de carga, {total_pages} páginas, {total_bytes}/{MAX_UPLOAD_BYTES} bytes.")
    if args.one_per_type:
        print("Cada PDF contiene una representación de e-CF aceptado para su casilla DGII.")
    else:
        print("Cada PDF agrupa todas las representaciones de su campo de carga DGII.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
