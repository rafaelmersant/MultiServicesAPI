"""Send one DGII certification stage in the portal's required order.

Each invocation handles one primary e-CF type or the RFCE stage. Without
``--send`` it only reports the pending records. Small type-32 e-CFs are never
sent by this script; DGII requires those to be uploaded through the portal.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MultiServices.settings")

import django  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env", override=False)
django.setup()

from ecf.config import Settings  # noqa: E402
from ecf.models import ECFEnvironment, ElectronicInvoice, RFCEStatus  # noqa: E402
from ecf.test_set_loader import (  # noqa: E402
    CERTIFICATION_EXPECTED_COUNTS,
    CERTIFICATION_SEND_ORDER,
    certification_order,
    load_test_set,
)
from ecf.workflow import query_record_result, send_record, send_rfce_record  # noqa: E402


DEFAULT_EXCEL = PROJECT_ROOT / "test_data/132018559-07102026102146.xlsx"
DEFAULT_ATTEMPT = "portal-reset-20261017-01"
STAGE_ORDER = CERTIFICATION_SEND_ORDER
EXPECTED = CERTIFICATION_EXPECTED_COUNTS


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--excel", type=Path, default=DEFAULT_EXCEL)
    parser.add_argument("--attempt", default=DEFAULT_ATTEMPT)
    stage = parser.add_mutually_exclusive_group(required=True)
    stage.add_argument("--type", choices=STAGE_ORDER)
    stage.add_argument("--rfce", action="store_true")
    parser.add_argument("--send", action="store_true", help="Transmit the pending records in this stage.")
    parser.add_argument("--limit", type=int, help="Límite por corrida; útil para verificar el portal entre comprobantes.")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        raise SystemExit("--limit debe ser positivo.")

    summary = load_test_set(args.excel)
    primary = certification_order(summary)
    small_ids = {case.case_id for case in summary.ecf_cases if case not in primary}
    cases = [case for case in primary if case.tipo_ecf == args.type] if args.type else []
    if args.type == "32":
        cases = [case for case in cases if case.case_id not in small_ids]
    small_cases = [case for case in summary.ecf_cases if case.case_id in small_ids]
    ids_by_type = {
        doc_type: [case.case_id for case in primary if case.tipo_ecf == doc_type]
        for doc_type in STAGE_ORDER
    }

    attempt_records = ElectronicInvoice.objects.filter(
        environment=ECFEnvironment.CERT,
        payload__certification_attempt=args.attempt,
    )
    if attempt_records.count() != 25:
        raise SystemExit(f"El intento local debe contener 25 registros; hay {attempt_records.count()}.")
    if args.send:
        settings = Settings.from_env()
        if settings.environment != ECFEnvironment.CERT:
            raise SystemExit("DGII_ENVIRONMENT debe ser cert antes de transmitir.")

    if args.rfce:
        for doc_type, ids in ids_by_type.items():
            accepted = attempt_records.filter(
                document_type=doc_type,
                payload__test_case_id__in=ids,
                status=ElectronicInvoice.Status.ACCEPTED,
            ).count()
            if accepted != EXPECTED[doc_type]:
                raise SystemExit(
                    f"RFCE no habilitado: tipo {doc_type} aceptado {accepted}/{EXPECTED[doc_type]}."
                )
        pending = []
        for case in small_cases:
            record = attempt_records.filter(payload__test_case_id=case.case_id).first()
            if record is None or record.rfce_status not in {
                RFCEStatus.READY,
                RFCEStatus.ACCEPTED,
            }:
                raise SystemExit(f"El RFCE del caso {case.case_id} no está firmado y listo.")
            if record.rfce_status != RFCEStatus.ACCEPTED:
                pending.append(record)

        print(f"Etapa RFCE: {len(small_cases)} requeridos; pendientes: {len(pending)}")
        if not args.send:
            print("Solo preflight; no se contactó a DGII.")
            return 0
        selected = pending[:args.limit] if args.limit else pending
        for record in selected:
            receipt = send_rfce_record(record)
            record.refresh_from_db()
            print(f"RFCE tipo 32 | estado={record.rfce_status} | codigo={receipt.code}")
            if record.rfce_status != RFCEStatus.ACCEPTED:
                raise SystemExit("DGII no aceptó este RFCE; se detuvo la secuencia.")
        total_accepted = attempt_records.filter(
            document_type="32",
            payload__test_case_id__in=[case.case_id for case in small_cases],
            rfce_status=RFCEStatus.ACCEPTED,
        ).count()
        print(f"RFCE aceptados: {total_accepted}/{len(small_cases)}.")
        if total_accepted == len(small_cases):
            print("Los cuatro E32 pequenos quedan pendientes de carga en el portal.")
        return 0

    stage_index = STAGE_ORDER.index(args.type)
    for previous_type in STAGE_ORDER[:stage_index]:
        previous_ids = ids_by_type[previous_type]
        accepted = attempt_records.filter(
            document_type=previous_type,
            payload__test_case_id__in=previous_ids,
            status=ElectronicInvoice.Status.ACCEPTED,
        ).count()
        if accepted != EXPECTED[previous_type]:
            raise SystemExit(
                f"Tipo {args.type} bloqueado: primero se requiere tipo {previous_type} aceptado "
                f"{accepted}/{EXPECTED[previous_type]}."
            )

    pending = []
    for case in cases:
        record = attempt_records.filter(payload__test_case_id=case.case_id).first()
        if record is None or record.document_type != args.type:
            raise SystemExit(f"Falta el registro local para el caso de tipo {args.type}.")
        if record.status == ElectronicInvoice.Status.ACCEPTED:
            continue
        if record.status not in {
            ElectronicInvoice.Status.READY,
            ElectronicInvoice.Status.SUBMITTED,
            ElectronicInvoice.Status.PROCESSING,
            ElectronicInvoice.Status.UNCERTAIN,
        }:
            raise SystemExit(f"El caso de tipo {args.type} está en estado {record.status}; se detuvo.")
        pending.append(record)

    print(f"Etapa tipo {args.type}: {len(cases)} requeridos; pendientes: {len(pending)}")
    if not args.send:
        print("Solo preflight; no se contactó a DGII.")
        return 0

    selected = pending[:args.limit] if args.limit else pending
    for record in selected:
        if record.status == ElectronicInvoice.Status.READY:
            send_record(record)
            record.refresh_from_db()
        for poll in range(1, 31):
            if record.status == ElectronicInvoice.Status.ACCEPTED:
                break
            if record.status not in {
                ElectronicInvoice.Status.SUBMITTED,
                ElectronicInvoice.Status.PROCESSING,
                ElectronicInvoice.Status.UNCERTAIN,
            }:
                break
            query_record_result(record)
            record.refresh_from_db()
            if record.status != ElectronicInvoice.Status.PROCESSING:
                break
            time.sleep(2)
        print(
            f"Tipo {args.type} | estado={record.status} | codigo={record.dgii_code} | "
            f"trackid={'si' if record.track_id else 'no'} | consultas={poll}"
        )
        if record.status != ElectronicInvoice.Status.ACCEPTED:
            raise SystemExit("DGII no devolvió Aceptado (código 1); se detuvo el orden de envío.")

    accepted = attempt_records.filter(
        document_type=args.type,
        payload__test_case_id__in=ids_by_type[args.type],
        status=ElectronicInvoice.Status.ACCEPTED,
    ).count()
    if accepted != EXPECTED[args.type]:
        if args.limit:
            print(f"Tipo {args.type}: {accepted}/{EXPECTED[args.type]}; etapa parcial, continuar este tipo antes del siguiente.")
            return 0
        raise SystemExit(f"Tipo {args.type} quedó en {accepted}/{EXPECTED[args.type]}.")
    print(f"Etapa tipo {args.type} completada: {accepted}/{EXPECTED[args.type]}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
