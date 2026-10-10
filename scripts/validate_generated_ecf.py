"""Generate and locally validate DGII e-CF test cases; never sends to DGII."""
import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from ecf.test_set_loader import load_test_set
from ecf.xml_builder import build_ecf_xml

DEFAULT_CASE = "132018559E310000000001"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Genera y valida casos e-CF localmente, sin enviarlos a DGII."
    )
    parser.add_argument("--excel", required=True, help="Ruta al Excel oficial del set DGII.")
    parser.add_argument("--xsd-dir", required=True, help="Carpeta con los XSD oficiales.")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--case", help="ID CasoPrueba del Excel; si se omite, usa el caso predeterminado.")
    selection.add_argument("--all", action="store_true", help="Procesa todos los casos de la hoja ECF.")
    parser.add_argument("--output-dir", default="test_data/ecf/generated", help="Carpeta de salida.")
    parser.add_argument("--sign", action="store_true", help="Firma, verifica y valida cada XML localmente. No envía.")
    args = parser.parse_args()

    load_dotenv()
    excel_path = Path(args.excel)
    xsd_dir = Path(args.xsd_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = load_test_set(excel_path)
    if args.all:
        cases = list(summary.ecf_cases)
    else:
        case_id = args.case or DEFAULT_CASE
        case = next((item for item in summary.ecf_cases if item.case_id == case_id), None)
        if case is None:
            raise SystemExit(f"No se encontró el caso ECF {case_id} en {excel_path}")
        cases = [case]

    certificate = None
    if args.sign:
        certificate_path = os.getenv("ECF_CERTIFICATE_PATH", "").strip()
        certificate_password = os.getenv("ECF_CERTIFICATE_PASSWORD", "")
        if not certificate_path or not certificate_password:
            raise SystemExit("Para --sign define ECF_CERTIFICATE_PATH y ECF_CERTIFICATE_PASSWORD en .env.")
        from ecf.certificate import load_pkcs12
        certificate = load_pkcs12(certificate_path, certificate_password)
        from ecf.signing import sign_xml, verify_xml_signature
        from ecf.xml_utils import validate_xsd

    successes = []
    failures = []
    print(f"Casos a procesar: {len(cases)} | Modo: {'firmar y validar localmente' if args.sign else 'generar y validar sin firma'}")

    for case in cases:
        xsd_path = xsd_dir / f"ECF{case.tipo_ecf}V1.0.xsd"
        try:
            if not xsd_path.is_file():
                raise FileNotFoundError(f"No se encontró el XSD: {xsd_path}")

            xml_data = build_ecf_xml(case, xsd_path, validate=True)
            unsigned_path = output_dir / f"{case.case_id}_sin_firma.xml"
            unsigned_path.write_bytes(xml_data)

            if args.sign:
                signed_xml = sign_xml(xml_data, certificate)
                verify_xml_signature(signed_xml, certificate)
                validate_xsd(signed_xml, xsd_path)
                signed_path = output_dir / f"{case.case_id}_firmado.xml"
                signed_path.write_bytes(signed_xml)
                print(f"OK | {case.case_id} | tipo {case.tipo_ecf} | {case.encf} | XML firmado y validado: {signed_path}")
            else:
                print(f"OK | {case.case_id} | tipo {case.tipo_ecf} | {case.encf} | XML validado: {unsigned_path}")
            successes.append(case.case_id)
        except Exception as exc:
            failures.append((case.case_id, case.tipo_ecf, case.encf, type(exc).__name__, str(exc)))
            print(f"ERROR | {case.case_id} | tipo {case.tipo_ecf} | {case.encf} | {type(exc).__name__}: {exc}")

    report_path = output_dir / "resumen_validacion.json"
    import json
    report = {
        "total": len(cases),
        "exitosos": len(successes),
        "fallidos": len(failures),
        "modo": "firmar_y_validar_localmente" if args.sign else "generar_y_validar_sin_firma",
        "casos_exitosos": successes,
        "casos_fallidos": [
            {"case_id": case_id, "tipo_ecf": tipo, "encf": encf, "error": error, "detalle": detail}
            for case_id, tipo, encf, error, detail in failures
        ],
        "envio_dgii": False,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nRESUMEN")
    print(f"Total: {len(cases)} | Correctos: {len(successes)} | Fallidos: {len(failures)}")
    print(f"Informe: {report_path}")
    print("No se realizó ninguna petición de red ni envío a DGII.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())