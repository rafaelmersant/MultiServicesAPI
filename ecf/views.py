from decimal import Decimal

import os
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import HttpResponse
from django.core.files.base import ContentFile
from django.utils import timezone
from lxml import etree
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from sales.models import InvoicesHeader

from .authentication import ECFUserAuthentication
from .models import ECF_DOCUMENT_TYPES, ElectronicInvoice, ElectronicInvoiceSequence, RFCEStatus
from .permissions import ECFAdminOrOwnerPermission, ECFCompanyAccessPermission
from .serializers import ElectronicInvoiceSerializer, ElectronicInvoiceSequenceSerializer
from .exceptions import ECFError
from .workflow import (
    ECFWorkflowError,
    build_unsigned_xml,
    query_record_result,
    build_rfce_from_signed_ecf,
    build_representation_pdf,
    send_rfce_record,
    sign_rfce_record,
    send_record,
    sign_record,
    representation_pdf_identity_is_current,
    _registry_for_environment,
    used_encfs_for_company,
    _linked_sale_values,
)


class ECFCompanyViewSet(ModelViewSet):
    authentication_classes = (ECFUserAuthentication,)
    permission_classes = (IsAuthenticated, ECFCompanyAccessPermission)
    http_method_names = ("get", "post", "head", "options")

    def get_queryset(self):
        return ElectronicInvoice.objects.filter(
            company_id=self.request.user.company_id
        ).select_related("invoice", "sequence")

    def get_serializer_class(self):
        return ElectronicInvoiceSerializer

    @action(detail=False, methods=("get",), url_path="sale-representation")
    def sale_representation(self, request):
        invoice_id = request.query_params.get("invoice", "")
        if not str(invoice_id).isdigit():
            raise ValidationError("Indica el identificador de la venta.")
        record = self.get_queryset().filter(environment="prod", invoice_id=invoice_id).first()
        if record is None:
            raise ValidationError("No existe un e-CF productivo asociado a esta venta para tu empresa.")
        try:
            pdf = build_representation_pdf(record)
        except ECFError as exc:
            raise ValidationError(str(exc)) from exc
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="RI-{record.encf}.pdf"'
        return response

    @action(detail=False, methods=("get",), url_path="eligible-sales")
    def eligible_sales(self, request):
        """Expose active source transactions without changing legacy invoices."""
        rows = InvoicesHeader.objects.filter(
            company_id=request.user.company_id,
            invoiceStatus="",
        ).exclude(electronic_invoice__isnull=False)
        if request.query_params.get("environment") == "prod":
            rows = rows.filter(Q(ncf__isnull=True) | Q(ncf=""))
        rows = rows.select_related("customer").order_by("-creationDate")[:200]
        return Response([
            {
                "id": row.pk,
                "sequence": row.sequence,
                "date": row.creationDate,
                "total": str(row.subtotal - row.discount),
                "payment_method": row.paymentMethod,
                "customer": f"{row.customer.firstName} {row.customer.lastName}".strip(),
                "customer_id": row.customer.identification or "",
            }
            for row in rows
        ])

    @action(detail=False, methods=("get",), url_path="configuration")
    def configuration(self, request):
        configured = os.getenv("DGII_ENVIRONMENT", "precert").strip().lower()
        return Response({
            "environment": configured,
            "production_requires_authorized_range": True,
            "production_range_configured": ElectronicInvoiceSequence.objects.filter(
                company_id=request.user.company_id, environment="prod", active=True,
                authorized_start__isnull=False, authorized_end__isnull=False,
            ).exclude(authorization_reference="").exists(),
        })

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        invoice_id = request.data.get("invoice")
        document_type = str(request.data.get("document_type") or "")
        environment = str(request.data.get("environment") or "cert")
        if not document_type.isdigit() or len(document_type) != 2:
            raise ValidationError({"document_type": "Usa el código e-CF de dos dígitos."})
        if document_type not in ECF_DOCUMENT_TYPES:
            raise ValidationError({"document_type": "Ese tipo no pertenece al set de certificación habilitado."})
        payload = request.data.get("payload") or {}
        if not isinstance(payload, dict):
            raise ValidationError({"payload": "Envía los campos fiscales como un objeto JSON."})
        if environment not in {"precert", "cert", "prod"}:
            raise ValidationError({"environment": "Usa precert, cert o prod."})
        if environment == "prod" and payload.get("certification_attempt"):
            raise ValidationError({"payload": "Los casos de certificación no se emiten en producción."})

        invoice = None
        if invoice_id not in (None, ""):
            invoice = InvoicesHeader.objects.select_for_update().filter(
                pk=invoice_id,
                company_id=request.user.company_id,
                invoiceStatus="",
            ).first()
            if invoice is None:
                raise ValidationError({"invoice": "La factura no pertenece a esta empresa."})
            if environment == "prod" and (invoice.ncf or "").strip():
                raise ValidationError({"invoice": "La venta ya tiene NCF. Selecciona una venta sin comprobante fiscal."})
        if environment == "prod" and document_type in {"31", "32"} and invoice is None:
            raise ValidationError({"invoice": "Selecciona una venta real sin NCF para este comprobante."})

        try:
            record = ElectronicInvoice.objects.create(
                company_id=request.user.company_id,
                environment=environment,
                invoice=invoice,
                document_type=document_type,
                payload=payload,
            )
        except IntegrityError as exc:
            raise ValidationError(
                {"invoice": "Esta factura ya tiene un registro e-CF."}
            ) from exc

        return Response(
            self.get_serializer(record).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=("post",), url_path="reserve-encf")
    @transaction.atomic
    def reserve_encf(self, request, pk=None):
        record = self.get_queryset().select_related(None).select_for_update().get(pk=self.get_object().pk)
        if record.status != ElectronicInvoice.Status.DRAFT or record.encf:
            raise ValidationError("Solo se puede asignar e-NCF a un borrador sin secuencia.")

        sequence_id = request.data.get("sequence")
        sequence = ElectronicInvoiceSequence.objects.filter(
            pk=sequence_id,
            company_id=request.user.company_id,
            document_type=record.document_type,
            environment=record.environment,
        ).first()
        if sequence is None:
            raise ValidationError({"sequence": "No existe una secuencia autorizada para este tipo."})

        try:
            if record.environment == "prod" and record.invoice_id:
                record.invoice = InvoicesHeader.objects.select_for_update().get(pk=record.invoice_id)
                if (record.invoice.ncf or "").strip():
                    raise ValueError("La venta ya tiene un NCF tradicional.")
                if record.document_type in {"31", "32"}:
                    _linked_sale_values(record)
            used_encfs = _used_encfs_for_sequence(sequence)
            while True:
                encf = sequence.allocate_encf()
                if encf not in used_encfs:
                    break
            record.sequence = sequence
            record.encf = encf
            record.save(update_fields=("sequence", "encf", "updated_at"))
        except (ValueError, RuntimeError, ECFError) as exc:
            raise ValidationError({"sequence": str(exc)}) from exc

        return Response(self.get_serializer(record).data)

    @action(detail=True, methods=("post",), url_path="update-draft")
    @transaction.atomic
    def update_draft(self, request, pk=None):
        record = self.get_queryset().select_related(None).select_for_update().get(pk=self.get_object().pk)
        if record.status != ElectronicInvoice.Status.DRAFT or record.encf:
            raise ValidationError("Solo se ajustan datos fiscales antes de reservar el e-NCF.")
        payload = request.data.get("payload")
        if not isinstance(payload, dict):
            raise ValidationError({"payload": "Los datos fiscales deben ser un objeto JSON."})
        if record.environment == "prod" and payload.get("certification_attempt"):
            raise ValidationError("Los casos de certificación no se emiten en producción.")
        record.payload = payload
        record.save(update_fields=("payload", "updated_at"))
        return Response(self.get_serializer(record).data)

    @action(detail=True, methods=("post",), url_path="build-xml")
    def build_xml(self, request, pk=None):
        record = self.get_object()
        if record.status != ElectronicInvoice.Status.DRAFT:
            raise ValidationError("Solo se genera XML para un borrador.")
        try:
            xml_data = build_unsigned_xml(record)
        except ECFError as exc:
            raise ValidationError({"ecf": str(exc)}) from exc
        record.raw_xml = xml_data.decode("utf-8")
        record.save(update_fields=("raw_xml", "updated_at"))
        return Response(self.get_serializer(record).data)

    @action(detail=True, methods=("get",), url_path="xml")
    def xml(self, request, pk=None):
        record = self.get_object()
        xml_data = record.signed_xml or record.raw_xml
        if not xml_data:
            raise ValidationError("El documento todavía no tiene XML generado.")
        response = HttpResponse(xml_data, content_type="application/xml; charset=utf-8")
        if record.signed_xml:
            response["Content-Disposition"] = f'attachment; filename="eCF-{record.encf}.xml"'
        return response

    @action(detail=True, methods=("post",), url_path="sign")
    def sign(self, request, pk=None):
        record = self.get_object()
        try:
            signed_xml, digest = sign_record(record)
        except ECFError as exc:
            raise ValidationError({"ecf": str(exc)}) from exc
        record.signed_xml = signed_xml.decode("utf-8")
        record.xml_hash = digest
        record.status = ElectronicInvoice.Status.READY
        record.last_error = ""
        record.save(
            update_fields=("signed_xml", "xml_hash", "status", "last_error", "updated_at")
        )
        return Response(self.get_serializer(record).data)

    @action(detail=True, methods=("post",), url_path="build-rfce")
    def build_rfce(self, request, pk=None):
        record = self.get_object()
        if record.status != ElectronicInvoice.Status.READY:
            raise ValidationError("Firma primero el e-CF tipo 32 asociado.")
        try:
            xml_data = build_rfce_from_signed_ecf(record)
        except ECFError as exc:
            raise ValidationError({"rfce": str(exc)}) from exc
        record.rfce_xml = xml_data.decode("utf-8")
        record.rfce_status = RFCEStatus.DRAFT
        record.save(update_fields=("rfce_xml", "rfce_status", "updated_at"))
        return Response(self.get_serializer(record).data)

    @action(detail=True, methods=("get",), url_path="rfce-xml")
    def rfce_xml(self, request, pk=None):
        record = self.get_object()
        xml_data = record.signed_rfce_xml or record.rfce_xml
        if not xml_data:
            raise ValidationError("El RFCE todavía no tiene XML generado.")
        return HttpResponse(xml_data, content_type="application/xml; charset=utf-8")

    @action(detail=True, methods=("post",), url_path="sign-rfce")
    def sign_rfce(self, request, pk=None):
        record = self.get_object()
        try:
            signed_xml = sign_rfce_record(record)
        except ECFError as exc:
            raise ValidationError({"rfce": str(exc)}) from exc
        record.signed_rfce_xml = signed_xml.decode("utf-8")
        record.rfce_status = RFCEStatus.READY
        record.save(update_fields=("signed_rfce_xml", "rfce_status", "updated_at"))
        return Response(self.get_serializer(record).data)

    @action(detail=True, methods=("post",), url_path="send-rfce")
    def send_rfce(self, request, pk=None):
        record = self.get_object()
        try:
            receipt = send_rfce_record(record)
        except (ECFWorkflowError, RuntimeError) as exc:
            raise ValidationError({"rfce": str(exc)}) from exc
        return Response(
            {
                **self.get_serializer(record).data,
                "rfce_result": {
                    "code": receipt.code,
                    "status": receipt.status,
                    "sequence_used": receipt.sequence_used,
                    "messages": [
                        {"code": message.code, "value": message.value}
                        for message in receipt.messages
                    ],
                },
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=("post",), url_path="send")
    def send(self, request, pk=None):
        record = self.get_object()
        try:
            receipt = send_record(record)
        except (ECFWorkflowError, RuntimeError) as exc:
            raise ValidationError({"ecf": str(exc)}) from exc
        return Response(
            {
                **self.get_serializer(record).data,
                "track_id": receipt.track_id,
                "reception_error": receipt.error,
                "reception_message": receipt.message,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=("post",), url_path="query-result")
    def query_result(self, request, pk=None):
        record = self.get_object()
        try:
            result = query_record_result(record)
        except (ECFWorkflowError, RuntimeError) as exc:
            raise ValidationError({"ecf": str(exc)}) from exc
        record.refresh_from_db()
        return Response(
            {
                **self.get_serializer(record).data,
                "result": {
                    "track_id": result.track_id,
                    "code": result.code,
                    "status": result.status,
                    "rnc": result.rnc,
                    "encf": result.encf,
                    "sequence_used": result.sequence_used,
                    "reception_date": result.reception_date,
                    "messages": result.messages,
                },
            }
        )

    @action(detail=True, methods=("post",), url_path="portal-result")
    def portal_result(self, request, pk=None):
        record = self.get_object()
        if record.environment != "cert":
            raise ValidationError("La confirmación manual del portal solo aplica a certificación.")
        result = str(request.data.get("result") or "").strip().lower()
        if result not in {"accepted", "rejected"}:
            raise ValidationError({"result": "Registra accepted o rejected según el portal DGII."})
        if record.document_type != "32" or record.status != ElectronicInvoice.Status.READY:
            raise ValidationError("El resultado manual aplica a un e-CF tipo 32 firmado pendiente de carga portal.")
        if record.portal_result:
            raise ValidationError("Ya se registró un resultado portal para este e-NCF; no se sobrescribe.")
        try:
            root = etree.fromstring(record.signed_xml.encode("utf-8"), etree.XMLParser(resolve_entities=False, no_network=True))
            total = Decimal((root.xpath(".//*[local-name()='MontoTotal']")[0].text or "0"))
        except Exception as exc:
            raise ValidationError("No se pudo verificar el total del XML firmado.") from exc
        if total >= Decimal("250000"):
            raise ValidationError("Las facturas tipo 32 de DOP 250,000 o más se consultan por TrackId, no por esta confirmación portal.")
        if record.rfce_status != RFCEStatus.ACCEPTED:
            raise ValidationError("El RFCE debe constar aceptado antes de registrar el resultado portal.")

        registry = _registry_for_environment(record.environment)
        existing = registry.get((record.company.rnc or "").strip(), record.encf)
        if existing:
            raise ValidationError("Este e-NCF ya figura en el registro de envíos; concilia el resultado antes de registrarlo como carga portal.")
        note = str(request.data.get("confirmation") or "").strip()[:500]
        if not note:
            raise ValidationError({"confirmation": "Describe brevemente el resultado observado en el portal DGII."})
        normalized_status = (
            ElectronicInvoice.Status.ACCEPTED
            if result == "accepted"
            else ElectronicInvoice.Status.REJECTED
        )
        dgii_status = f"Portal DGII: {result} (confirmación manual)"
        registry.record_historical(
            rnc=(record.company.rnc or "").strip(), encf=record.encf,
            case_id=f"portal-upload-{record.pk}", tipo_ecf=record.document_type,
            status=result, dgii_code=None, dgii_status=dgii_status,
            notes=note,
        )
        record.portal_result = result
        record.portal_result_at = timezone.now()
        record.status = normalized_status
        record.dgii_code = None
        record.dgii_status = dgii_status
        record.dgii_messages = [{"valor": note}]
        record.resolved_at = record.portal_result_at
        record.save(update_fields=(
            "portal_result", "portal_result_at", "status", "dgii_code", "dgii_status",
            "dgii_messages", "resolved_at", "updated_at",
        ))
        return Response(self.get_serializer(record).data)

    @action(detail=True, methods=("post",), url_path="build-representation")
    def build_representation(self, request, pk=None):
        record = self.get_object()
        try:
            pdf_data = build_representation_pdf(record)
        except ECFError as exc:
            raise ValidationError({"representation": str(exc)}) from exc
        record.representation_pdf.save(
            f"RI-{record.encf}.pdf", ContentFile(pdf_data), save=True
        )
        return Response(self.get_serializer(record).data)

    @action(detail=True, methods=("get",), url_path="representation")
    def representation(self, request, pk=None):
        record = self.get_object()
        if not record.representation_pdf:
            raise ValidationError("La representación impresa aún no ha sido generada.")
        if not representation_pdf_identity_is_current(record):
            raise ValidationError(
                "No se entrega la RI: la identidad del XML firmado no coincide con los datos legales actuales. "
                "Se requiere un e-CF nuevo firmado con la identidad correcta."
            )
        response = HttpResponse(record.representation_pdf.read(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="RI-{record.encf}.pdf"'
        return response


class ECFSequenceViewSet(ModelViewSet):
    authentication_classes = (ECFUserAuthentication,)
    permission_classes = (IsAuthenticated, ECFAdminOrOwnerPermission)
    serializer_class = ElectronicInvoiceSequenceSerializer
    http_method_names = ("get", "post", "head", "options")

    def get_queryset(self):
        return ElectronicInvoiceSequence.objects.filter(
            company_id=self.request.user.company_id
        ).order_by("document_type", "id")

    def perform_create(self, serializer):
        serializer.save(
            company_id=self.request.user.company_id,
            created_user=self.request.user.email,
        )


def _used_encfs_for_sequence(sequence):
    if sequence.environment == "prod":
        return set(ElectronicInvoice.objects.filter(
            company_id=sequence.company_id, environment="prod", encf__isnull=False,
        ).values_list("encf", flat=True))
    return used_encfs_for_company(sequence.company.rnc)

