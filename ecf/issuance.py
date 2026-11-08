"""Range checks shared by reservation, signing and transmission."""
from datetime import datetime
from zoneinfo import ZoneInfo


def validate_sequence(sequence):
    today = datetime.now(ZoneInfo("America/Santo_Domingo")).date()
    if not sequence.active:
        raise ValueError("La secuencia e-CF no está activa.")
    start, end = sequence.authorized_start, sequence.authorized_end
    if start is None or end is None:
        raise ValueError("La secuencia no tiene un rango autorizado configurado.")
    maximum = 9_999_999_999 if sequence.environment == "prod" else 10_000_000
    if not 1 <= start <= end <= maximum:
        raise ValueError("El rango autorizado no es válido para este ambiente.")
    if sequence.due_date and sequence.due_date < today:
        raise ValueError("El rango autorizado está vencido.")
    if sequence.environment == "prod":
        if not sequence.authorization_reference.strip():
            raise ValueError("Registra la referencia de autorización DGII del rango productivo.")
        if sequence.document_type not in {"32", "34"} and not sequence.due_date:
            raise ValueError("Registra el vencimiento autorizado por DGII para este tipo e-CF.")


def validate_production_record(record):
    if record.environment != "prod":
        return
    if not record.sequence_id or not record.encf:
        raise ValueError("Producción requiere un e-NCF de un rango DGII autorizado.")
    sequence = record.sequence
    validate_sequence(sequence)
    if (sequence.company_id, sequence.environment, sequence.document_type) != (
        record.company_id, record.environment, record.document_type,
    ):
        raise ValueError("El rango no corresponde a la empresa, ambiente o tipo del documento.")
    prefix = f"E{record.document_type}"
    if len(record.encf) != 13 or not record.encf.startswith(prefix) or not record.encf[3:].isdigit():
        raise ValueError("El e-NCF no tiene el formato esperado.")
    if not sequence.authorized_start <= int(record.encf[3:]) <= sequence.authorized_end:
        raise ValueError("El e-NCF está fuera del rango autorizado.")
    if record.invoice_id and (record.invoice.ncf or "").strip() not in {"", record.encf}:
        raise ValueError("La venta ya tiene un NCF; no se puede emitir otro comprobante para ella.")


def link_accepted_sale(record):
    """Expose the accepted electronic NCF in existing sales lists and reports."""
    if record.environment != "prod" or not record.invoice_id or record.status not in {"accepted", "accepted_conditional"}:
        return
    from django.db.models import Q
    from sales.models import InvoicesHeader
    updated = InvoicesHeader.objects.filter(pk=record.invoice_id, company_id=record.company_id).filter(
        Q(ncf__isnull=True) | Q(ncf="") | Q(ncf=record.encf)
    ).update(ncf=record.encf)
    if updated != 1:
        raise ValueError("El e-CF fue aceptado pero la venta tiene otro NCF. Concilia sin reenviar el comprobante.")
