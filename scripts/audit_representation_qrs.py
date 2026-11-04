"""Decode actual PDF QR images and optionally consult DGII, without sending invoices.

Install the optional decoder with pip install zxing-cpp, or use --decoder-dir
to load a decoder installed outside the application's runtime requirements.
--diagnose-certification-route checks old production links using the cert route;
it does not modify the PDFs and never declares those original links valid.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import sys
from urllib.parse import parse_qs, quote, urlencode, urlsplit, urlunsplit

import requests
from lxml import html
from pypdf import PdfReader


def consultation_url(url: str, *, diagnose_certification_route: bool = False) -> str:
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.netloc not in {"ecf.dgii.gov.do", "fc.dgii.gov.do"}:
        raise ValueError("El QR no apunta al servicio HTTPS de DGII.")
    query = parse_qs(parts.query, keep_blank_values=True)
    if any(len(values) != 1 for values in query.values()):
        raise ValueError("El QR contiene parámetros duplicados.")
    small = query.get("ENCF", [""])[0].startswith("E32") and Decimal(query.get("MontoTotal", ["0"])[0]) < Decimal("250000")
    expected_host = "fc.dgii.gov.do" if small else "ecf.dgii.gov.do"
    expected_path = "/certecf/consultatimbrefc" if small else "/certecf/consultatimbre"
    if parts.netloc != expected_host:
        raise ValueError("La factura de consumo y su monto no corresponden al servicio QR.")
    if diagnose_certification_route:
        # DGII distinguishes an absent optional buyer from RncComprador=.
        diagnostic_query = urlencode([
            (key, values[0]) for key, values in query.items()
            if not (key == "RncComprador" and not values[0])
        ], quote_via=quote, safe="")
        return urlunsplit((parts.scheme, parts.netloc, expected_path, diagnostic_query, ""))
    if parts.path.lower() != expected_path:
        raise ValueError("El QR no apunta al ambiente de certificación.")
    return url


def consultation_fields(content: bytes) -> dict[str, str]:
    document = html.fromstring(content)
    result = {}
    for row in document.xpath("//tr"):
        cells = row.xpath("./th|./td")
        if len(cells) == 2:
            label, value = (" ".join(cell.text_content().split()) for cell in cells)
            result[label] = value
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--decoder-dir", type=Path)
    parser.add_argument("--check-dgii", action="store_true")
    parser.add_argument("--diagnose-certification-route", action="store_true")
    parser.add_argument("--expected-issuer", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.decoder_dir:
        sys.path.insert(0, str(args.decoder_dir.resolve()))
    import zxingcpp

    rows = []
    for path in sorted(args.directory.glob("RI-*.pdf")):
        for number, page in enumerate(PdfReader(path).pages, 1):
            codes = [code.text for image in page.images for code in zxingcpp.read_barcodes(image.image)]
            row = {"file": path.name, "page": number, "decoded_count": len(codes), "ready_for_submission": False}
            rows.append(row)
            if len(codes) != 1:
                row["error"] = "Se requiere exactamente un QR legible por página."
                continue
            original = codes[0]
            row["original_url"] = original
            try:
                consultation_url(original)
                row["original_certification_route_valid"] = True
            except ValueError as exc:
                row["original_certification_route_valid"] = False
                row["original_route_error"] = str(exc)
            try:
                url = consultation_url(original, diagnose_certification_route=args.diagnose_certification_route)
                row["consulted_url"] = url
                if args.check_dgii:
                    response = requests.get(url, timeout=30)
                    response.raise_for_status()
                    fields = consultation_fields(response.content)
                    row["dgii_fields"] = fields
                    row["http_status"] = response.status_code
                    expected_encf = parse_qs(urlsplit(original).query)["ENCF"][0]
                    row["invoice_found"] = fields.get("e-NCF") == expected_encf
                    issuer = next((v for k, v in fields.items() if "social emisor" in k.lower() or k.lower() == "razón social"), "")
                    row["issuer_identity_matches"] = issuer == args.expected_issuer
                    row["ready_for_submission"] = bool(
                        row["original_certification_route_valid"]
                        and row["invoice_found"]
                        and row["issuer_identity_matches"]
                        and fields.get("Estado", "").lower() == "aceptado"
                    )
            except (ValueError, requests.RequestException) as exc:
                row["error"] = str(exc)
            print(f"{path.name} p{number}: route={row.get('original_certification_route_valid')} found={row.get('invoice_found')} identity={row.get('issuer_identity_matches')} ready={row['ready_for_submission']}")
    if not rows:
        raise SystemExit("No se encontraron PDF RI para auditar.")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({"checked_at": datetime.now(timezone.utc).isoformat(), "pages": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Páginas: {len(rows)}; listas para envío: {sum(r['ready_for_submission'] for r in rows)}")
    return 0 if all(row["ready_for_submission"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
