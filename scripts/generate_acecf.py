from __future__ import annotations

import sys
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ecf.certificate import load_pkcs12

from decimal import Decimal, InvalidOperation
from pathlib import Path

from lxml import etree
import openpyxl

# Reuse the project's existing certificate loader and XML-signing implementation.
from ecf.certificate import load_pkcs12
from ecf.config import Settings
from ecf.signing import sign_xml, verify_xml_signature


def text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def money(value) -> str:
    try:
        amount = Decimal(text(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        raise ValueError(f"MontoTotal inválido: {value!r}")
    if amount < 0:
        raise ValueError(f"MontoTotal no puede ser negativo: {value!r}")
    return f"{amount:.2f}"


def build_xml(row: dict[str, object]) -> bytes:
    required = [
        "Version", "RNCEmisor", "eNCF", "FechaEmision", "MontoTotal",
        "RNCComprador", "Estado", "FechaHoraAprobacionComercial",
    ]
    missing = [key for key in required if text(row.get(key)) == ""]
    if missing:
        raise ValueError("Campos obligatorios vacíos: " + ", ".join(missing))

    estado = text(row["Estado"])
    if estado not in {"1", "2"}:
        raise ValueError(f"Estado debe ser 1 o 2; recibido {estado!r}")
    motivo = text(row.get("DetalleMotivoRechazo"))
    if estado == "2" and not motivo:
        raise ValueError("DetalleMotivoRechazo es obligatorio cuando Estado=2")
    if len(motivo) > 250:
        raise ValueError("DetalleMotivoRechazo supera 250 caracteres")

    root = etree.Element("ACECF")
    detail = etree.SubElement(root, "DetalleAprobacionComercial")
    fields = [
        ("Version", text(row["Version"])),
        ("RNCEmisor", text(row["RNCEmisor"])),
        ("eNCF", text(row["eNCF"])),
        ("FechaEmision", text(row["FechaEmision"])),
        ("MontoTotal", money(row["MontoTotal"])),
        ("RNCComprador", text(row["RNCComprador"])),
        ("Estado", estado),
    ]
    if estado == "2":
        fields.append(("DetalleMotivoRechazo", motivo))
    fields.append(("FechaHoraAprobacionComercial", text(row["FechaHoraAprobacionComercial"])))
    for name, value in fields:
        etree.SubElement(detail, name).text = value
    return etree.tostring(root, encoding="UTF-8", xml_declaration=True, pretty_print=False)


def validate(xml_bytes: bytes, xsd_path: Path) -> None:
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    schema = etree.XMLSchema(etree.parse(str(xsd_path), parser))
    doc = etree.fromstring(xml_bytes, parser)
    schema.assertValid(doc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera, firma y valida XML ACECF desde el Excel de pruebas DGII. No envía documentos.")
    parser.add_argument("--excel", required=True, type=Path)
    parser.add_argument("--xsd", required=True, type=Path)
    parser.add_argument("--output-dir", default=Path("test_data/acecf/generated"), type=Path)
    parser.add_argument("--sheet", default="ACEECF_Generadas")
    parser.add_argument("--unsigned-only", action="store_true", help="Genera y valida XML sin firma; no carga el certificado.")
    args = parser.parse_args()

    if not args.excel.is_file():
        print(f"ERROR: no existe Excel: {args.excel}", file=sys.stderr); return 2
    if not args.xsd.is_file():
        print(f"ERROR: no existe XSD: {args.xsd}", file=sys.stderr); return 2

    wb = openpyxl.load_workbook(args.excel, data_only=True, read_only=True)
    if args.sheet not in wb.sheetnames:
        print(f"ERROR: no existe hoja {args.sheet!r}. Hojas: {wb.sheetnames}", file=sys.stderr); return 2
    ws = wb[args.sheet]
    rows = ws.iter_rows(values_only=True)
    headers = [text(h) for h in next(rows)]
    records = []
    for line_no, values in enumerate(rows, start=2):
        if not any(v is not None and text(v) for v in values):
            continue
        row = dict(zip(headers, values))
        row["_line_no"] = line_no
        records.append(row)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    certificate = None
    if not args.unsigned_only:
        settings = Settings.from_env()
        certificate = load_pkcs12(settings.certificate_path, settings.certificate_password)

    errors = 0
    for row in records:
        encf = text(row.get("eNCF"))
        safe_encf = "".join(c for c in encf if c.isalnum() or c in "-_ ").strip().replace(" ", "_")
        try:
            unsigned = build_xml(row)
            validate(unsigned, args.xsd)
            final_xml = unsigned
            suffix = "_sin_firma"
            if certificate is not None:
                final_xml = sign_xml(unsigned, certificate)
                verify_xml_signature(final_xml, certificate)
                validate(final_xml, args.xsd)
                suffix = "_firmado"
            out = args.output_dir / f"{safe_encf}{suffix}.xml"
            out.write_bytes(final_xml)
            print(f"OK | fila {row['_line_no']} | {encf} | {out}")
        except Exception as exc:
            errors += 1
            print(f"ERROR | fila {row['_line_no']} | {encf} | {exc}", file=sys.stderr)

    print(f"\nProcesados: {len(records)} | Correctos: {len(records)-errors} | Errores: {errors}")
    print("IMPORTANTE: este script solo genera/valida archivos locales; no realiza llamadas a DGII.")
    return 1 if errors else 0

if __name__ == "__main__":
    raise SystemExit(main())
