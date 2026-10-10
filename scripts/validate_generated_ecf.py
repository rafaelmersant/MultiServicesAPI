"""Generate and locally validate one DGII e-CF test case.

This script does not authenticate or send anything to DGII.
"""
import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

from ecf.certificate import load_pkcs12
from ecf.signing import sign_xml, verify_xml_signature
from ecf.test_set_loader import load_test_set
from ecf.xml_builder import build_ecf_xml
from ecf.xml_utils import validate_xsd


DEFAULT_CASE = "132018559E310000000001"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Genera y valida localmente un caso e-CF, sin enviarlo a DGII."
    )
    parser.add_argument("--excel", required=True, help="Ruta al Excel oficial del set DGII.")
    parser.add_argument("--xsd-dir", required=True, help="Carpeta con los XSD oficiales.")
    parser.add_argument("--case", default=DEFAULT_CASE, help="ID CasoPrueba del Excel.")
    parser.add_argument("--output-dir", default="test_data/ecf/generated", help="Carpeta de salida.")
    parser.add_argument(
        "--sign",
        action="store_true",
        help="También firma, verifica la firma y valida contra el XSD oficial. No envía.",
    )
    args = parser.parse_args()

    load_dotenv()
    excel_path = Path(args.excel)
    xsd_dir = Path(args.xsd_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = load_test_set(excel_path)
    case = next(
        (item for item in summary.ecf_cases if item.case_id == args.case),
        None,
    )
    if case is None:
        raise SystemExit(f"No se encontró el caso ECF {args.case} en {excel_path}")

    xsd_path = xsd_dir / f"ECF{case.tipo_ecf}V1.0.xsd"
    if not xsd_path.is_file():
        raise SystemExit(f"No se encontró el XSD correspondiente: {xsd_path}")

    unsigned_xml = build_ecf_xml(case, xsd_path, validate=True)
    unsigned_path = output_dir / f"{case.case_id}_sin_firma.xml"
    unsigned_path.write_bytes(unsigned_xml)
    print(f"XML generado y validado previo a firma: {unsigned_path}")
    print(f"Tipo e-CF: {case.tipo_ecf} | e-NCF del Excel: {case.encf}")

    if not args.sign:
        print("Modo local solamente: no se firmó ni se envió a DGII.")
        return 0

    certificate_path = os.getenv("ECF_CERTIFICATE_PATH", "").strip()
    certificate_password = os.getenv("ECF_CERTIFICATE_PASSWORD", "")
    if not certificate_path or not certificate_password:
        raise SystemExit(
            "Para --sign define ECF_CERTIFICATE_PATH y ECF_CERTIFICATE_PASSWORD en .env."
        )

    # Import signing dependencies only when explicitly requested.
    from ecf.certificate import load_pkcs12
    from ecf.signing import sign_xml, verify_xml_signature
    from ecf.xml_utils import validate_xsd

    certificate = load_pkcs12(certificate_path, certificate_password)
    signed_xml = sign_xml(unsigned_xml, certificate)
    verify_xml_signature(signed_xml, certificate)
    print("Firma XML verificada localmente.")

    # Validate the signed document against the untouched official XSD.
    validate_xsd(signed_xml, xsd_path)
    signed_path = output_dir / f"{case.case_id}_firmado.xml"
    signed_path.write_bytes(signed_xml)
    print(f"XML firmado y validado contra XSD oficial: {signed_path}")
    print("No se realizó ninguna petición de red ni envío a DGII.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
