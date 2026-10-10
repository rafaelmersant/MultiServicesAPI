"""Generate, validate and optionally sign RFCE summaries locally.

This script never sends documents to DGII.
The official XSD file is not modified. For lxml compatibility only, the script
normalizes XML Schema's unsupported non-capturing-group syntax in an in-memory
copy (?:...) -> (...), then validates against that compiled copy.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Mapping

from lxml import etree

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from ecf.certificate import load_pkcs12
from ecf.signing import sign_xml, verify_xml_signature
from ecf.test_set_loader import load_test_set

XSD_NS = "http://www.w3.org/2001/XMLSchema"
DS_NS = "http://www.w3.org/2000/09/xmldsig#"
INDEX_RE = re.compile(r"\[(\d+)\]")


def normal_name(value: str) -> str:
    return re.sub(r"\s+", "", value).casefold()


def split_header(header: str) -> tuple[str, tuple[int, ...]]:
    indexes = tuple(int(x) for x in INDEX_RE.findall(header))
    base = INDEX_RE.sub("", header).strip()
    return normal_name(base), indexes


def clean_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value or value.casefold() == "#e":
            return None
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


class ExcelValues:
    def __init__(self, values: Mapping[str, Any]):
        self.values: dict[tuple[str, tuple[int, ...]], str] = {}
        for header, raw in values.items():
            if not header:
                continue
            name, indexes = split_header(str(header))
            value = clean_value(raw)
            if value is not None:
                self.values[(name, indexes)] = value

    def get(self, element_name: str, indexes: tuple[int, ...]) -> str | None:
        return self.values.get((normal_name(element_name), indexes))

    def max_for_subtree(self, element: etree._Element, indexes: tuple[int, ...]) -> int:
        candidates: list[int] = []
        for leaf in element.iter(f"{{{XSD_NS}}}element"):
            name = leaf.get("name")
            if not name:
                continue
            normalized = normal_name(name)
            for (column_name, column_indexes), _ in self.values.items():
                if (
                    column_name == normalized
                    and len(column_indexes) > len(indexes)
                    and column_indexes[:len(indexes)] == indexes
                ):
                    candidates.append(column_indexes[len(indexes)])
        return max(candidates, default=0)


def is_complex(element: etree._Element) -> bool:
    return element.find(f"{{{XSD_NS}}}complexType") is not None


def children(element: etree._Element) -> list[etree._Element]:
    complex_type = element.find(f"{{{XSD_NS}}}complexType")
    if complex_type is None:
        return []
    sequence = complex_type.find(f"{{{XSD_NS}}}sequence")
    if sequence is None:
        return []
    return sequence.findall(f"{{{XSD_NS}}}element")


def max_occurs(element: etree._Element) -> int:
    value = element.get("maxOccurs", "1")
    if value == "unbounded":
        return 10000
    try:
        return int(value)
    except ValueError:
        return 1


def subtree_has_data(
    element: etree._Element,
    values: ExcelValues,
    indexes: tuple[int, ...],
) -> bool:
    name = element.get("name")
    if not is_complex(element):
        return bool(name and values.get(name, indexes) is not None)
    for child in children(element):
        if subtree_has_data(child, values, indexes):
            return True
        if child.get("maxOccurs", "1") != "1":
            limit = values.max_for_subtree(child, indexes)
            for occurrence in range(1, limit + 1):
                if subtree_has_data(child, values, indexes + (occurrence,)):
                    return True
    return False


def append_element(
    parent_xml: etree._Element,
    xsd_element: etree._Element,
    values: ExcelValues,
    indexes: tuple[int, ...],
) -> None:
    name = xsd_element.get("name")
    if not name:
        return

    minimum = int(xsd_element.get("minOccurs", "1"))
    maximum = max_occurs(xsd_element)

    if maximum > 1:
        limit = min(maximum, values.max_for_subtree(xsd_element, indexes))
        for occurrence in range(1, limit + 1):
            child_indexes = indexes + (occurrence,)
            if not subtree_has_data(xsd_element, values, child_indexes):
                continue
            node = etree.SubElement(parent_xml, name)
            if is_complex(xsd_element):
                for child in children(xsd_element):
                    append_element(node, child, values, child_indexes)
            else:
                value = values.get(name, child_indexes)
                if value is not None:
                    node.text = value
        return

    if minimum == 0 and not subtree_has_data(xsd_element, values, indexes):
        return

    node = etree.SubElement(parent_xml, name)
    if is_complex(xsd_element):
        for child in children(xsd_element):
            append_element(node, child, values, indexes)
    else:
        value = values.get(name, indexes)
        if value is not None:
            node.text = value


def compile_rfce_schema(xsd_path: Path, allow_unsigned: bool) -> etree.XMLSchema:
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    schema_doc = etree.parse(str(xsd_path), parser)
    schema_root = schema_doc.getroot()

    # libxml2 rejects XSD non-capturing groups. Convert syntax in memory only.
    for pattern in schema_root.iter(f"{{{XSD_NS}}}pattern"):
        value = pattern.get("value")
        if value and "(?:" in value:
            pattern.set("value", value.replace("(?:", "("))

    if allow_unsigned:
        for any_node in schema_root.iter(f"{{{XSD_NS}}}any"):
            any_node.set("minOccurs", "0")

    return etree.XMLSchema(schema_doc)


def validate_xml(xml_bytes: bytes, schema: etree.XMLSchema) -> None:
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    root = etree.fromstring(xml_bytes, parser)
    schema.assertValid(root)


def security_code_from_signed_ecf(signed_ecf: bytes) -> str:
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    root = etree.fromstring(signed_ecf, parser)
    if etree.QName(root).localname != "ECF":
        raise ValueError("El documento firmado asociado no tiene raíz ECF.")

    nodes = root.xpath(
        ".//ds:SignatureValue",
        namespaces={"ds": DS_NS},
    )
    if not nodes or not nodes[0].text:
        raise ValueError("El ECF firmado no contiene ds:SignatureValue.")

    signature_value = "".join(nodes[0].text.split())
    if len(signature_value) < 6:
        raise ValueError("SignatureValue tiene menos de seis caracteres.")

    # The RFCE security code is derived from the signed ECF SignatureValue.
    # The DGII technical guidance describes the six-character security code;
    # the widely used DGII e-CF implementation takes the first six characters.
    return signature_value[:6]


def build_rfce_xml(test_case: Any, xsd_path: Path, security_code: str) -> bytes:
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    schema_doc = etree.parse(str(xsd_path), parser)
    schema_root = schema_doc.getroot()
    root_decl = schema_root.find(f"{{{XSD_NS}}}element[@name='RFCE']")
    if root_decl is None:
        raise ValueError(f"El XSD no define la raíz RFCE: {xsd_path}")

    values_dict = dict(test_case.values)
    values_dict["CodigoSeguridadeCF"] = security_code
    values = ExcelValues(values_dict)

    root = etree.Element("RFCE")
    for child in children(root_decl):
        append_element(root, child, values, ())

    return etree.tostring(
        root.getroottree(),
        encoding="UTF-8",
        xml_declaration=True,
        pretty_print=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Genera, valida y opcionalmente firma RFCE localmente; no envía a DGII."
    )
    parser.add_argument("--excel", required=True, help="Ruta al Excel del set DGII.")
    parser.add_argument("--xsd", default="xsd/RFCE32V1.0.xsd", help="Ruta al XSD RFCE oficial.")
    parser.add_argument(
        "--signed-ecf-dir",
        default="test_data/ecf/generated",
        help="Directorio con los ECF32 firmados: <CasoPrueba>_firmado.xml.",
    )
    parser.add_argument(
        "--output-dir",
        default="test_data/ecf/rfce",
        help="Directorio de salida para XML RFCE e informe.",
    )
    parser.add_argument(
        "--sign",
        action="store_true",
        help="También firma RFCE, verifica la firma y valida el XML firmado.",
    )
    args = parser.parse_args()

    load_dotenv()
    excel_path = Path(args.excel)
    xsd_path = Path(args.xsd)
    signed_ecf_dir = Path(args.signed_ecf_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not xsd_path.is_file():
        raise SystemExit(f"No existe el XSD RFCE: {xsd_path}")

    summary = load_test_set(excel_path)
    cases = summary.rfce_cases
    print(f"Casos RFCE a procesar: {len(cases)} | Modo: {'firmar y validar' if args.sign else 'generar y validar sin firma'}")

    unsigned_schema = compile_rfce_schema(xsd_path, allow_unsigned=True)
    signed_schema = compile_rfce_schema(xsd_path, allow_unsigned=False)

    certificate = None
    if args.sign:
        certificate_path = os.getenv("ECF_CERTIFICATE_PATH", "").strip()
        certificate_password = os.getenv("ECF_CERTIFICATE_PASSWORD", "")
        if not certificate_path or not certificate_password:
            raise SystemExit("Para --sign define ECF_CERTIFICATE_PATH y ECF_CERTIFICATE_PASSWORD en .env.")
        certificate = load_pkcs12(certificate_path, certificate_password)

    results: list[dict[str, Any]] = []
    success = 0

    for case in cases:
        result: dict[str, Any] = {
            "case_id": case.case_id,
            "tipo_ecf": case.tipo_ecf,
            "encf": case.encf,
            "status": "ERROR",
        }
        try:
            signed_ecf_path = signed_ecf_dir / f"{case.case_id}_firmado.xml"
            if not signed_ecf_path.is_file():
                raise FileNotFoundError(
                    f"No se encontró el ECF32 firmado requerido para obtener CodigoSeguridadeCF: {signed_ecf_path}"
                )

            security_code = security_code_from_signed_ecf(signed_ecf_path.read_bytes())
            result["codigoSeguridad"] = security_code

            unsigned_xml = build_rfce_xml(case, xsd_path, security_code)
            validate_xml(unsigned_xml, unsigned_schema)
            unsigned_path = output_dir / f"{case.case_id}_rfce_sin_firma.xml"
            unsigned_path.write_bytes(unsigned_xml)
            result["unsigned_xml"] = str(unsigned_path)

            if args.sign:
                assert certificate is not None
                signed_xml = sign_xml(unsigned_xml, certificate)
                verify_xml_signature(signed_xml, certificate)
                validate_xml(signed_xml, signed_schema)
                signed_path = output_dir / f"{case.case_id}_rfce_firmado.xml"
                signed_path.write_bytes(signed_xml)
                result["signed_xml"] = str(signed_path)
                print(f"OK | {case.case_id} | {case.encf} | RFCE firmado y validado | código {security_code}")
            else:
                print(f"OK | {case.case_id} | {case.encf} | RFCE generado y validado previo a firma | código {security_code}")

            result["status"] = "OK"
            success += 1
        except Exception as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
            print(f"ERROR | {case.case_id} | {case.encf} | {result['error']}")
        results.append(result)

    report = {
        "excel": str(excel_path),
        "xsd": str(xsd_path),
        "total": len(cases),
        "correctos": success,
        "fallidos": len(cases) - success,
        "modo": "firmar_y_validar" if args.sign else "generar_y_validar_sin_firma",
        "resultados": results,
        "envio_dgii": False,
    }
    report_path = output_dir / "resumen_validacion_rfce.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nRESUMEN RFCE")
    print(f"Total: {len(cases)} | Correctos: {success} | Fallidos: {len(cases) - success}")
    print(f"Informe: {report_path}")
    print("No se realizó ninguna petición de red ni envío a DGII.")
    return 0 if success == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
