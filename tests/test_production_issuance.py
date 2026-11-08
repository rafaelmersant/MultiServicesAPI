"""Production preparation tests: synthetic data, no network or commercial DB writes."""
import hashlib
import os
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MultiServices.settings")
import django
django.setup()

import pytest
from rest_framework.test import APIRequestFactory, force_authenticate
from ecf.issuance import validate_production_record, validate_sequence, link_accepted_sale
from ecf.models import ElectronicInvoice, ElectronicInvoiceSequence, RFCEStatus
from ecf.serializers import ElectronicInvoiceSequenceSerializer
from ecf.views import ECFCompanyViewSet, _used_encfs_for_sequence
from ecf.workflow import (
    ECFWorkflowError, _linked_sale_values, _settings_for_record,
    _registry_for_environment, _rfce_registry_for_environment,
    build_unsigned_xml, send_rfce_record,
)


def sequence(**changes):
    values = dict(company_id=1, environment="prod", document_type="31", active=True,
                  authorized_start=1, authorized_end=9_999_999_999, current=None,
                  authorization_reference="UNIT-TEST-AUTHORIZATION", due_date=date(2099, 12, 31))
    values.update(changes)
    return SimpleNamespace(**values)


@pytest.mark.parametrize("changes", [
    {"active": False}, {"authorized_start": None}, {"authorization_reference": ""},
    {"due_date": date(2000, 1, 1)}, {"due_date": None}, {"authorized_end": 10_000_000_000},
])
def test_production_rejects_missing_invalid_or_expired_authorization(changes):
    with pytest.raises(ValueError):
        validate_sequence(sequence(**changes))


def test_production_supports_ten_digit_sequence_but_certification_keeps_its_limit():
    validate_sequence(sequence())
    with pytest.raises(ValueError):
        validate_sequence(sequence(environment="cert"))


def test_production_cannot_bypass_range_checks_with_a_hand_entered_encf():
    record = SimpleNamespace(environment="prod", sequence_id=None, encf="E310000000001")
    with pytest.raises(ValueError, match="rango DGII"):
        validate_production_record(record)


@pytest.mark.parametrize("changes", [{"company_id": 2}, {"environment": "cert"}, {"authorized_start": 2}])
def test_record_cannot_use_another_company_environment_or_out_of_range_number(changes):
    record = SimpleNamespace(environment="prod", company_id=1, document_type="31", sequence_id=1,
                             sequence=sequence(**changes), encf="E310000000001", invoice_id=None)
    with pytest.raises(ValueError):
        validate_production_record(record)


def sale_record():
    company = SimpleNamespace(rnc="101000001", name="EMISOR DE PRUEBA UNITARIA", address="Dirección de prueba", email="", phoneNumber="")
    customer = SimpleNamespace(pk=7, company_id=1, identification="131246796", identificationType="R", firstName="CLIENTE", lastName="PRUEBA", email="", address="")
    invoice = SimpleNamespace(company_id=1, invoiceStatus="", ncf="", paymentMethod="CASH", subtotal=Decimal("236"),
                              discount=Decimal("20"), itbis=Decimal("32.95"), customer=customer,
                              creationDate=datetime(2026, 11, 8, tzinfo=timezone.utc))
    detail = SimpleNamespace(quantity=Decimal("2"), price=Decimal("118"), itbis=Decimal("36"),
                             discount=Decimal("20"), product=SimpleNamespace(description="Producto de prueba", measure="43"))
    record = SimpleNamespace(company_id=1, environment="prod", company=company, invoice=invoice, invoice_id=1,
                             document_type="31", sequence_id=1, sequence=sequence(), encf="E310000000001", payload={})
    return record, detail


def test_discounted_sale_builds_valid_xml_from_empty_payload_without_changing_sale():
    record, detail = sale_record()
    with patch("sales.models.InvoicesDetail.objects.filter") as details:
        details.return_value.select_related.return_value.order_by.return_value = [detail]
        xml = build_unsigned_xml(record)
    assert b"<MontoTotal>216.00</MontoTotal>" in xml
    assert b"<DescuentoMonto>20.00</DescuentoMonto>" in xml
    assert b"<MontoItem>216.00</MontoItem>" in xml
    assert b"<TotalITBIS>32.95</TotalITBIS>" in xml
    assert b"<FechaVencimientoSecuencia>31-12-2099</FechaVencimientoSecuencia>" in xml
    assert record.invoice.ncf == "" and record.invoice.subtotal == Decimal("236")


def test_mixed_exempt_and_taxed_lines_preserve_total_and_explicit_treatment():
    record, detail = sale_record()
    detail.discount = Decimal("0")
    record.invoice.discount = Decimal("0")
    record.invoice.subtotal = Decimal("336")
    record.invoice.itbis = Decimal("36")
    record.payload = {"zero_tax_treatment": "4"}
    exempt = SimpleNamespace(quantity=Decimal("1"), price=Decimal("100"), itbis=Decimal("0"), discount=Decimal("0"), product=detail.product)
    with patch("sales.models.InvoicesDetail.objects.filter") as details:
        details.return_value.select_related.return_value.order_by.return_value = [detail, exempt]
        xml = build_unsigned_xml(record)
    assert b"<MontoExento>100.00</MontoExento>" in xml
    assert b"<MontoTotal>336.00</MontoTotal>" in xml


def test_source_with_traditional_ncf_is_never_converted():
    record, _ = sale_record()
    record.invoice.ncf = "B0100000001"
    with pytest.raises(ValueError, match="ya tiene un NCF"):
        validate_production_record(record)


def test_source_tax_mismatch_is_rejected_instead_of_changing_existing_totals():
    record, detail = sale_record()
    record.invoice.itbis = Decimal("1")
    with patch("sales.models.InvoicesDetail.objects.filter") as details:
        details.return_value.select_related.return_value.order_by.return_value = [detail]
        with pytest.raises(ECFWorkflowError, match="ITBIS"):
            _linked_sale_values(record)


def test_manual_certification_acceptance_is_not_allowed_for_production():
    record = SimpleNamespace(environment="prod")
    request = APIRequestFactory().post("/", {"result": "accepted"}, format="json")
    force_authenticate(request, user=SimpleNamespace(is_authenticated=True, role="Admin", company_id=1))
    with patch.object(ECFCompanyViewSet, "get_object", return_value=record):
        response = ECFCompanyViewSet.as_view({"post": "portal_result"})(request)
    assert response.status_code == 400


def test_production_and_certification_use_different_transmission_registries(tmp_path, monkeypatch):
    monkeypatch.setenv("ECF_PRODUCTION_REGISTRY_DIR", str(tmp_path))
    with patch("ecf.workflow.django_settings.MEDIA_ROOT", str(tmp_path / "public-media")):
        assert _registry_for_environment("prod").db_path != _registry_for_environment("cert").db_path
        assert _rfce_registry_for_environment("prod").db_path != _rfce_registry_for_environment("cert").db_path


@pytest.mark.parametrize("dgii_status, expected", [("Aceptado", "accepted"), ("Aceptado Condicional", "accepted_conditional"), ("Rechazado", "rejected")])
def test_production_small_consumption_uses_actual_rfce_response_without_manual_portal(dgii_status, expected):
    ecf = '<ECF><TipoeCF>32</TipoeCF><RNCEmisor>101000001</RNCEmisor><eNCF>E320000000001</eNCF><SignatureValue>abcdefghi</SignatureValue></ECF>'
    rfce = '<RFCE><TipoeCF>32</TipoeCF><RNCEmisor>101000001</RNCEmisor><eNCF>E320000000001</eNCF><MontoTotal>100.00</MontoTotal><CodigoSeguridadeCF>abcdef</CodigoSeguridadeCF></RFCE>'
    record = SimpleNamespace(pk=1, invoice_id=None, environment="prod", payload={}, document_type="32", status="ready", rfce_status="ready",
                             encf="E320000000001", signed_xml=ecf, signed_rfce_xml=rfce,
                             xml_hash=hashlib.sha256(ecf.encode()).hexdigest(), company=SimpleNamespace(rnc="101000001"), save=MagicMock())
    receipt = SimpleNamespace(encf=record.encf, code=1, status=dgii_status, sequence_used=True, messages=[])
    config = SimpleNamespace(certificate_path="unused", certificate_password="unused", request_timeout_seconds=1)
    with (patch("ecf.workflow._validate_signed_company_identity"), patch("ecf.workflow._settings_for_record", return_value=config),
          patch("ecf.workflow.load_pkcs12"), patch("ecf.workflow.verify_xml_signature"), patch("ecf.workflow.validate_xsd"),
          patch("ecf.workflow._validate_rfce_xml"), patch("ecf.workflow.DGIIAuthenticator"),
          patch("ecf.workflow._rfce_registry_for_environment"), patch("ecf.workflow.DGIIRFCEClient") as client):
        client.return_value.send_rfce.return_value = receipt
        send_rfce_record(record)
    assert record.status == expected
    assert record.dgii_status == dgii_status


def test_production_does_not_consume_certification_numbers():
    with patch.object(ElectronicInvoice.objects, "filter") as records, patch("ecf.views.used_encfs_for_company") as certification:
        records.return_value.values_list.return_value = ["E310000000005"]
        assert _used_encfs_for_sequence(sequence()) == {"E310000000005"}
    certification.assert_not_called()


def test_overlapping_authorizations_are_rejected():
    serializer = ElectronicInvoiceSequenceSerializer(context={"request": SimpleNamespace(user=SimpleNamespace(company_id=1))})
    with patch.object(ElectronicInvoiceSequence.objects, "filter") as ranges:
        ranges.return_value.exists.return_value = True
        from rest_framework.exceptions import ValidationError
        with pytest.raises(ValidationError, match="solapa"):
            serializer.validate(dict(environment="prod", document_type="31", authorized_start=1, authorized_end=10,
                                     due_date=date(2099, 12, 31), active=True, authorization_reference="UNIT-TEST"))


@pytest.mark.parametrize("env,status,should_link", [("prod", "accepted", True), ("prod", "accepted_conditional", True), ("prod", "rejected", False), ("cert", "accepted", False)])
def test_source_sale_is_linked_only_after_actual_production_acceptance(env, status, should_link):
    record = SimpleNamespace(environment=env, status=status, invoice_id=1, company_id=1, encf="E310000000001")
    with patch("sales.models.InvoicesHeader.objects.filter") as sales:
        sales.return_value.filter.return_value.update.return_value = 1
        link_accepted_sale(record)
    assert sales.called is should_link
    if should_link:
        sales.return_value.filter.return_value.update.assert_called_once_with(ncf=record.encf)


def test_acceptance_never_overwrites_a_different_existing_ncf():
    record = SimpleNamespace(environment="prod", status="accepted", invoice_id=1, company_id=1, encf="E310000000001")
    with patch("sales.models.InvoicesHeader.objects.filter") as sales:
        sales.return_value.filter.return_value.update.return_value = 0
        with pytest.raises(ValueError, match="otro NCF"):
            link_accepted_sale(record)


@pytest.mark.parametrize("protected", [False, True])
def test_traditional_sales_remain_editable_while_electronic_sources_are_protected(protected):
    from ecf.sale_protection import require_editable_sale
    from rest_framework.exceptions import ValidationError
    with patch("ecf.sale_protection.is_electronic_sale", return_value=protected):
        if protected:
            with pytest.raises(ValidationError):
                require_editable_sale(1)
        else:
            require_editable_sale(1)


def test_cashier_can_read_own_company_ecf_but_not_manage_ranges_or_send():
    from ecf.permissions import ECFCompanyAccessPermission
    permission = ECFCompanyAccessPermission()
    request = SimpleNamespace(method="GET", user=SimpleNamespace(is_authenticated=True, role="Caja"))
    assert permission.has_permission(request, None)
    request.method = "POST"
    assert not permission.has_permission(request, None)
