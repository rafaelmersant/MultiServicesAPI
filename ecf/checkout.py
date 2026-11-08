"""One checkout attempt for an already saved sale; the manual workflow remains usable."""
from decimal import Decimal

from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from lxml import etree

from sales.models import InvoicesHeader
from .models import ElectronicInvoice, ElectronicInvoiceSequence, RFCEStatus
from .workflow import (
    ECFWorkflowError, _linked_sale_values, build_unsigned_xml, sign_record,
    send_record, query_record_result, build_rfce_from_signed_ecf,
    sign_rfce_record, send_rfce_record, build_representation_pdf,
    _settings_for_record,
)


def prepare_checkout(company_id, invoice_id, document_type, payload):
    if document_type not in {"31", "32"}:
        raise ValueError("La caja solo emite E31 o E32.")
    if not isinstance(payload, dict) or set(payload) - {"zero_tax_treatment", "FechaLimitePago"}:
        raise ValueError("Los ajustes de caja no son válidos.")
    with transaction.atomic():
        source = InvoicesHeader.objects.select_for_update().filter(pk=invoice_id, company_id=company_id, invoiceStatus="").first()
        if source is None:
            raise ValueError("La venta no pertenece a tu empresa o está anulada.")
        record = ElectronicInvoice.objects.filter(invoice=source).first()
        if record:
            if record.environment != "prod" or record.document_type != document_type:
                raise ValueError("La venta ya tiene un e-CF de otro tipo o ambiente.")
            return record
        if (source.ncf or "").strip():
            raise ValueError("La venta ya tiene NCF tradicional; no se emitirá otro comprobante.")
        return ElectronicInvoice.objects.create(company_id=company_id, invoice=source, environment="prod", document_type=document_type, payload=payload)


def _reserve(record):
    with transaction.atomic():
        locked = ElectronicInvoice.objects.select_for_update().get(pk=record.pk)
        if locked.encf:
            record.refresh_from_db()
            return
        source = InvoicesHeader.objects.select_for_update().get(pk=locked.invoice_id)
        if source.ncf:
            raise ECFWorkflowError("La venta ya tiene NCF; no se reservará otro.")
        locked.invoice = source
        _linked_sale_values(locked)  # Stop inconsistent sales before consuming a number.
        sequence = ElectronicInvoiceSequence.objects.filter(
            company_id=record.company_id, environment="prod", document_type=record.document_type,
            active=True, authorized_start__isnull=False, authorized_end__isnull=False,
        ).exclude(authorization_reference="").filter(
            Q(due_date__isnull=True) | Q(due_date__gte=timezone.localdate())
        ).filter(Q(current__isnull=True) | Q(current__lt=F("authorized_end"))).order_by("authorized_start", "pk").first()
        if sequence is None:
            raise ECFWorkflowError("No hay rango productivo autorizado disponible. Continúa desde Facturación e-CF.")
        locked.encf = sequence.allocate_encf()
        locked.sequence = sequence
        locked.save(update_fields=("encf", "sequence", "updated_at"))
    record.refresh_from_db()


def run_checkout(record):
    # A second click/request must never run a parallel fiscal pipeline. A worker
    # crash leaves this claim set; the administrator then uses the manual flow.
    claimed = ElectronicInvoice.objects.filter(pk=record.pk, checkout_in_progress=False).update(checkout_in_progress=True)
    if not claimed:
        return "La venta ya se está procesando o requiere revisión en Facturación e-CF."
    try:
        record.refresh_from_db()
        _settings_for_record(record, require_range=False)
        if record.status == "draft":
            _reserve(record)
            if not record.raw_xml:
                record.raw_xml = build_unsigned_xml(record).decode("utf-8")
                record.save(update_fields=("raw_xml", "updated_at"))
            signed, digest = sign_record(record)
            record.signed_xml, record.xml_hash, record.status = signed.decode("utf-8"), digest, "ready"
            record.save(update_fields=("signed_xml", "xml_hash", "status", "updated_at"))
        if record.status == "ready":
            root = etree.fromstring(record.signed_xml.encode(), etree.XMLParser(resolve_entities=False, no_network=True))
            small = record.document_type == "32" and Decimal(root.xpath(".//*[local-name()='MontoTotal']/text()")[0]) < Decimal("250000")
            if small:
                if record.rfce_status == RFCEStatus.DRAFT:
                    record.rfce_xml = build_rfce_from_signed_ecf(record).decode("utf-8")
                    record.save(update_fields=("rfce_xml", "updated_at"))
                    record.signed_rfce_xml = sign_rfce_record(record).decode("utf-8")
                    record.rfce_status = RFCEStatus.READY
                    record.save(update_fields=("signed_rfce_xml", "rfce_status", "updated_at"))
                if record.rfce_status == RFCEStatus.READY:
                    send_rfce_record(record)
            else:
                send_record(record)
        if record.track_id and record.status in {"submitted", "processing"}:
            query_record_result(record)  # One query, never loop/retry fiscal sends.
        if record.status in {"accepted", "accepted_conditional"} and not record.representation_pdf:
            pdf = build_representation_pdf(record)
            record.representation_pdf.save(f"RI-{record.encf}.pdf", ContentFile(pdf), save=False)
            record.save(update_fields=("representation_pdf", "updated_at"))
        if record.status in {"accepted", "accepted_conditional"}:
            record.last_error = ""
            record.save(update_fields=("last_error", "updated_at"))
        return ""
    finally:
        ElectronicInvoice.objects.filter(pk=record.pk).update(checkout_in_progress=False)
